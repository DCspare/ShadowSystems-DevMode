// apps/stream-engine/core/telegram.go
package core

import (
	"context"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/celestix/gotgproto"
	"github.com/celestix/gotgproto/sessionMaker"
	"github.com/glebarez/sqlite"
	"github.com/gotd/contrib/middleware/floodwait"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

var (
	Client *TelegramClient
	once   sync.Once
)

type TelegramClient struct {
	Client     *gotgproto.Client
	API        *tg.Client
	TargetHash int64 // 🔑 We store the specific AccessHash for the Log Channel here
	Context    context.Context
	Log        *zap.Logger
}

func InitTelegram(ctx context.Context, logger *zap.Logger) (*TelegramClient, error) {
	var err error
	once.Do(func() {
		apiID, _ := strconv.Atoi(os.Getenv("TG_API_ID"))
		apiHash := os.Getenv("TG_API_HASH")
		sessionString := os.Getenv("TG_SESSION_STRING")

		// Ensure session dir exists
		os.MkdirAll("/app/sessions", 0700)
		sessionFile := filepath.Join("/app/sessions", "engine.db")

		// 1. Identity Logic
		// Use Pyrogram String (User Mode) if available, otherwise Bot Token
		var storage sessionMaker.SessionConstructor
		if sessionString != "" {
			logger.Info("📡 Identity: Cloning Pyrogram Session")
			storage = sessionMaker.PyrogramSession(sessionString)
		} else {
			logger.Info("📂 Identity: Using SQLite Session (Bot)")
			// FIX: Wrap the path in sqlite.Open to satisfy gorm.Dialector interface
			storage = sessionMaker.SqlSession(sqlite.Open(sessionFile)) 
		}

		waiter := floodwait.NewSimpleWaiter().WithMaxRetries(5)

		// 2. Client Build
		rawClient, err := gotgproto.NewClient(
			apiID,
			apiHash,
			gotgproto.ClientTypePhone(""), // ignored for string session
			&gotgproto.ClientOpts{
				Session:          storage,
				Middlewares:      []telegram.Middleware{waiter},
				DisableCopyright: true,
			},
		)

		if err != nil {
			return
		}
		
		Client = &TelegramClient{
			Client:  rawClient,
			API:     rawClient.API(),
			Context: ctx,
			Log:     logger,
		}
	})
	return Client, err
}

func (tc *TelegramClient) Run(ctx context.Context, onStart func(context.Context) error) error {
	return tc.Client.Run(ctx, func(ctx context.Context) error {
		// 1. Authenticate (Refresh if needed)
		if _, err := tc.Client.Auth().Status(ctx); err != nil {
			return err
		}

		tc.Log.Info("✅ Engine Connected. Searching for Log Channel...")

		// 2. RESOLVE ACCESS HASH MANUALLY
		// We sweep the dialogs to find the specific Log Channel from ENV
		// This sets 'tc.TargetHash' which is critical for the Downloader
		targetIDStr := os.Getenv("TG_LOG_CHANNEL_ID")
		// Clean ID: -10012345 -> 12345
		cleanIDStr := strings.TrimPrefix(targetIDStr, "-100")
		targetID, _ := strconv.ParseInt(cleanIDStr, 10, 64)

		dlgRes, err := tc.API.MessagesGetDialogs(ctx, &tg.MessagesGetDialogsRequest{
			Limit:      100,
			OffsetPeer: &tg.InputPeerEmpty{},
		})

		found := false
		if err == nil {
			// Iterate chats to find the hash
			var chats []tg.ChatClass
			switch d := dlgRes.(type) {
			case *tg.MessagesDialogs:
				chats = d.Chats
			case *tg.MessagesDialogsSlice:
				chats = d.Chats
			}

			for _, chat := range chats {
				if channel, ok := chat.(*tg.Channel); ok {
					if channel.ID == targetID {
						tc.TargetHash = channel.AccessHash
						tc.Log.Info("🎯 TARGET ACQUIRED", 
							zap.String("title", channel.Title),
							zap.Int64("hash", channel.AccessHash))
						found = true
						break
					}
				}
			}
		}

		if !found {
			// Emergency: Try Resolve via raw API if not in recent dialogs
			// (Only works if user is joined)
			tc.Log.Warn("⚠️ Log Channel not in top 100 dialogs. Attempting direct resolve...")
			// Logic could be expanded here if needed
		}

		return onStart(ctx)
	})
}
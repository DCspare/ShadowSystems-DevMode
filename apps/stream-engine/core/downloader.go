// apps/stream-engine/core/downloader.go
package core

import (
	"encoding/hex"
	"net/http"
	"strconv"
	"strings"

	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

func ServeStream(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	// Gather inputs
	msgIDStr := r.Header.Get("X-Location-Msg-ID")
	chatIDStr := r.Header.Get("X-Location-Chat-ID")
	
	// Fallback Raw inputs
	rawMediaID := r.Header.Get("X-Telegram-Media-ID")
	rawHash := r.Header.Get("X-Telegram-Access-Hash")
	rawRefHex := r.Header.Get("X-Telegram-File-Ref")

	msgID, _ := strconv.Atoi(msgIDStr)
	
	// Prepare Location Container
	var location *tg.InputDocumentFileLocation

	if Client == nil || Client.API == nil {
		http.Error(w, "Engine Offline", 503)
		return
	}

	// 🛑 STRATEGY A: Message ID Resolution (Preferred for seeking & fresh files)
	if msgID > 0 {
		cid, _ := strconv.ParseInt(strings.TrimPrefix(chatIDStr, "-100"), 10, 64)
		if cid != 0 && Client.TargetHash != 0 {
			targetChannel := &tg.InputChannel{ChannelID: cid, AccessHash: Client.TargetHash}
			
			res, err := Client.API.ChannelsGetMessages(ctx, &tg.ChannelsGetMessagesRequest{
				Channel: targetChannel,
				ID:      []tg.InputMessageClass{&tg.InputMessageID{ID: msgID}},
			})

			if err == nil {
				// Try extract from message
				extract := func(msgs []tg.MessageClass) {
					for _, m := range msgs {
						msg, ok := m.(*tg.Message)
						if !ok || msg.Media == nil { continue }
						if media, ok := msg.Media.(*tg.MessageMediaDocument); ok {
							if doc, ok := media.Document.AsNotEmpty(); ok {
								location = &tg.InputDocumentFileLocation{
									ID:            doc.ID,
									AccessHash:    doc.AccessHash,
									FileReference: doc.FileReference,
									ThumbSize:     "",
								}
								Client.Log.Info("✅ Found via Message", zap.Int("msg", msgID))
								return
							}
						}
					}
				}
				
				switch m := res.(type) {
				case *tg.MessagesChannelMessages: extract(m.Messages)
				case *tg.MessagesMessages: extract(m.Messages)
				case *tg.MessagesMessagesSlice: extract(m.Messages)
				}
			} else {
				Client.Log.Warn("⚠️ Message Lookup Failed", zap.Error(err))
			}
		}
	}

	// 🛑 STRATEGY B: Raw Direct Access (Fallback for Legacy/Failed lookups)
	if location == nil && rawMediaID != "" && rawMediaID != "0" {
		Client.Log.Info("⚡ Attempting Direct Raw Access (Legacy Mode)")
		
		mID, _ := strconv.ParseInt(rawMediaID, 10, 64)
		aHash, _ := strconv.ParseInt(rawHash, 10, 64)
		fRef, _ := hex.DecodeString(rawRefHex)

		location = &tg.InputDocumentFileLocation{
			ID:            mID,
			AccessHash:    aHash,
			FileReference: fRef,
			ThumbSize:     "",
		}
	}

	// Final check
	if location == nil {
		http.Error(w, "Media Empty or Unresolved", 404)
		return
	}

	// 4. STREAM PIPE
	// Basic Headers - We blindly set them since we might not have size if Strategy B used
	// Note: If Strategy B used, 'fileSize' is unknown. Seeking might be limited in fallback mode
	// unless we use content-range: bytes start-end/*. 
	
	w.Header().Set("Content-Type", "video/mp4")
	w.Header().Set("Accept-Ranges", "bytes")
	
	offset, _ := parseRange(r.Header.Get("Range"))
	if offset > 0 { w.WriteHeader(http.StatusPartialContent) } else { w.WriteHeader(http.StatusOK) }

	chunkSize := int64(1024 * 1024) 
	currentOffset := offset - (offset % chunkSize)
	firstPartSkip := offset - currentOffset

	for {
		select {
		case <-ctx.Done(): return
		default:
		}

		chunk, err := Client.API.UploadGetFile(ctx, &tg.UploadGetFileRequest{
			Location: location,
			Offset:   currentOffset,
			Limit:    int(chunkSize),
		})
		
		if err != nil { return }

		if c, ok := chunk.(*tg.UploadFile); ok {
			data := c.Bytes
			if len(data) == 0 { return }

			if firstPartSkip > 0 {
				if int64(len(data)) > firstPartSkip {
					data = data[firstPartSkip:]
				} else { data = nil }
				firstPartSkip = 0 
			}

			if len(data) > 0 {
				if _, err := w.Write(data); err != nil { return }
				if f, ok := w.(http.Flusher); ok { f.Flush() }
			}
			currentOffset += int64(len(c.Bytes))
		} else {
			return
		}
	}
}

func parseRange(h string) (int64, int64) {
	if !strings.HasPrefix(h, "bytes=") { return 0, 0 }
	parts := strings.Split(strings.TrimPrefix(h, "bytes="), "-")
	val, _ := strconv.ParseInt(parts[0], 10, 64)
	return val, 0
}
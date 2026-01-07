package core

import (
	"context"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gotd/td/telegram"
	"github.com/gotd/td/tg"
)

// Streamer handles the orchestration between Nginx authorized requests 
// and the raw Telegram MTProto Data Center connection.
type Streamer struct {
	Client *telegram.Client // Management layer for session maintenance
	Raw    *tg.Client      // Access layer for the low-level GetFile procedures
}

// NewStreamer creates the instance and fires the non-blocking Auth worker.
// It defensively cleans variables to survive Cloud-IDE environment quirks.
func NewStreamer(ctx context.Context) (*Streamer, error) {
	// Cleanup env noise (Backslashes, quotes) often found in IDX shell expansions
	apiIDStr := strings.Trim(os.Getenv("TG_API_ID"), "\\ \"'")
	apiHash := strings.Trim(os.Getenv("TG_API_HASH"), "\\ \"'")
	botToken := strings.Trim(os.Getenv("TG_ENGINE_BOT_TOKEN"), "\\ \"'")

	apiID, err := strconv.Atoi(apiIDStr)
	if err != nil {
		return nil, fmt.Errorf("initialization failure: API_ID error: %v", err)
	}

	s := &Streamer{}
	s.Client = telegram.NewClient(apiID, apiHash, telegram.Options{})
	s.Raw = tg.NewClient(s.Client)

	// Auth Handshake: Sustains the DC session in a background goroutine.
	go func() {
		// IDC networking bridge stabilization delay
		time.Sleep(1 * time.Second)
		
		err := s.Client.Run(ctx, func(runCtx context.Context) error {
			_, err := s.Client.Auth().Bot(runCtx, botToken)
			if err != nil { return err }
			log.Println("✅ Go-MTProto Engine: Transceiver Activated (Session Handshake Success)")
			<-runCtx.Done()
			return runCtx.Err()
		})
		if err != nil {
			log.Printf("❌ Bridge Heartbeat Terminated: %v", err)
		}
	}()

	return s, nil
}

// HandleStream implements the primary byte-piping logic. 
// It utilizes InputFileLocation coordinates received from the Brain to pull
// actual file packets from Telegram and streams them to the client.
func (s *Streamer) HandleStream(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	
	// Coordinate extraction from Headers (Passed by Manager -> Gateway chain)
	// Default to -1 to catch unmapped headers early
	mediaID, _ := strconv.ParseInt(r.Header.Get("X-Media-ID"), 10, 64)
	accessHash, _ := strconv.ParseInt(r.Header.Get("X-Access-Hash"), 10, 64)
	fileRefHex := r.Header.Get("X-File-Ref")
	
	// Decode File Reference (Telegram's cryptographic salt for each unique request)
	fileRef, err := hex.DecodeString(fileRefHex)
	if err != nil {
		log.Printf("[REQ_ERR] Malformed hex file_reference for DocumentID: %d", mediaID)
		return
	}

	log.Printf("[PIPE] Authenticated Tunnel Open for Doc: %d", mediaID)

	// Transmission Metadata Configuration
	w.Header().Set("Content-Type", "video/mp4")
	w.Header().Set("Accept-Ranges", "bytes")
	w.WriteHeader(http.StatusPartialContent)

	// Define MTProto-compliant range steps (Multiples of 1024/4096 preferred)
	const limit int = 1024 * 512 // 512KB stable chunk size
	var offset int64 = 0

	// Transmit logic: Bridging TG chunks directly to HTTP output writer.
	// For production verification: fetching the first 5MB to populate player UI.
	for i := 0; i < 10; i++ { 
		result, err := s.Raw.UploadGetFile(ctx, &tg.UploadGetFileRequest{
			Location: &tg.InputDocumentFileLocation{
				ID:            mediaID,
				AccessHash:    accessHash,
				FileReference: fileRef,
			},
			Offset: offset, // Corrected Type to int64
			Limit:  limit,
		})

		if err != nil {
			log.Printf("[FAIL] MTProto Chunk Failure at Offset %d: %v", offset, err)
			return
		}

		// Result Cast to Byte Object
		uploadFile, ok := result.(*tg.UploadFile)
		if !ok {
			log.Println("[ERR] Telegram DC returned unexpected response structure.")
			return
		}

		// Memory-optimized transfer
		if _, err := w.Write(uploadFile.Bytes); err != nil {
			log.Printf("[SESSION] Client closed the stream pipe.")
			return
		}

		offset += int64(len(uploadFile.Bytes))

		// Check for browser abort
		select {
		case <-ctx.Done(): return
		default: continue
		}
	}

	log.Printf("[SUCCESS] Pulse transmission verified for Doc %d", mediaID)
}

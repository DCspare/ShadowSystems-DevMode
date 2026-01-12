// apps/stream-engine/core/downloader.go
package core

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/gotd/td/tg"
	"go.uber.org/zap"
)

func ServeStream(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	msgIDStr := r.Header.Get("X-Location-Msg-ID")
	chatIDStr := r.Header.Get("X-Location-Chat-ID")

	if msgIDStr == "" || chatIDStr == "" {
		http.Error(w, "Headers missing", 400)
		return
	}

	msgID, _ := strconv.Atoi(msgIDStr)
	cid, _ := strconv.ParseInt(strings.TrimPrefix(chatIDStr, "-100"), 10, 64)

	if Client == nil || Client.API == nil {
		http.Error(w, "Engine Offline", 503)
		return
	}

	if Client.TargetHash == 0 {
		Client.Log.Error("❌ Log Channel Hash Unknown")
		http.Error(w, "Internal Error", 500)
		return
	}

	// 1. Fetch Message
	// We rely on PeerManager's persistent cache hash for access
	targetChannel := &tg.InputChannel{ChannelID: cid, AccessHash: Client.TargetHash}
	res, err := Client.API.ChannelsGetMessages(ctx, &tg.ChannelsGetMessagesRequest{
		Channel: targetChannel,
		ID:      []tg.InputMessageClass{&tg.InputMessageID{ID: msgID}},
	})

	if err != nil {
		Client.Log.Error("❌ Fetch Fail", zap.Error(err))
		http.Error(w, "Telegram Refused", 502)
		return
	}

	// 2. Extract Location & SIZE (Critical for Seeking)
	var location *tg.InputDocumentFileLocation
	var fileSize int64 = 0

	extract := func(msgs []tg.MessageClass) {
		for _, m := range msgs {
			msg, ok := m.(*tg.Message)
			if !ok || msg.Media == nil {
				continue
			}
			if media, ok := msg.Media.(*tg.MessageMediaDocument); ok {
				if doc, ok := media.Document.AsNotEmpty(); ok {
					fileSize = doc.Size // <--- CAPTURE SIZE HERE
					location = &tg.InputDocumentFileLocation{
						ID:            doc.ID,
						AccessHash:    doc.AccessHash,
						FileReference: doc.FileReference,
						ThumbSize:     "",
					}
					return
				}
			}
		}
	}

	switch m := res.(type) {
	case *tg.MessagesChannelMessages:
		extract(m.Messages)
	case *tg.MessagesMessages:
		extract(m.Messages)
	case *tg.MessagesMessagesSlice:
		extract(m.Messages)
	}

	if location == nil {
		http.Error(w, "Media Empty", 404)
		return
	}

	// 3. HTTP HEADERS (The Fix for Scrubbing)
	w.Header().Set("Content-Type", "video/mp4")
	w.Header().Set("Accept-Ranges", "bytes")
	
	requestedOffset, _ := parseRange(r.Header.Get("Range"))
	
	// A. CONTENT LENGTH: Required for the browser to know file end
	// Logic: Size = Total - StartOffset
	contentLength := fileSize - requestedOffset
	w.Header().Set("Content-Length", strconv.FormatInt(contentLength, 10))

	// B. CONTENT RANGE: Required for Status 206
	// Format: bytes START-END/TOTAL
	w.Header().Set("Content-Range", fmt.Sprintf("bytes %d-%d/%d", requestedOffset, fileSize-1, fileSize))

	if requestedOffset > 0 {
		w.WriteHeader(http.StatusPartialContent)
	} else {
		// Even for full file, returning 206 is often safer for video players,
		// but 200 with Accept-Ranges usually works too.
		// However, with Content-Range present, we MUST send 206 according to spec?
		// Actually: If no Range header in request, return 200 OK.
		// If Range header present (even "bytes=0-"), return 206 Partial.
		if r.Header.Get("Range") != "" {
			w.WriteHeader(http.StatusPartialContent)
		} else {
			w.WriteHeader(http.StatusOK)
		}
	}

	// 4. STREAM LOOP (Aligned Seeking Fix)
	chunkSize := int64(1024 * 1024) // 1MB Chunk (Telegram Standard)

	// Math: Find the nearest 1MB boundary BELOW the requested offset
	// e.g., Request 1048577 (1MB + 1byte) -> aligned = 1048576
	alignedOffset := requestedOffset - (requestedOffset % chunkSize)

	// Math: How many bytes to "throw away" from the first chunk
	firstPartSkip := requestedOffset - alignedOffset

	currentOffset := alignedOffset

	Client.Log.Info("▶️ Playback",
		zap.Int64("req_offset", requestedOffset),
		zap.Int64("tg_offset", alignedOffset),
		zap.Int64("size", fileSize),
	)

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		chunk, err := Client.API.UploadGetFile(ctx, &tg.UploadGetFileRequest{
			Location: location,
			Offset:   currentOffset,
			Limit:    int(chunkSize),
		})

		if err != nil {
			return
		} // Stream Ended

		if c, ok := chunk.(*tg.UploadFile); ok {
			data := c.Bytes
			if len(data) == 0 {
				return
			} // EOF

			// TRIM Logic: If we grabbed a chunk just to align it, remove the start
			if firstPartSkip > 0 {
				if int64(len(data)) > firstPartSkip {
					data = data[firstPartSkip:]
				} else {
					data = nil
				}
				firstPartSkip = 0 // Done skipping for this stream
			}
			
			// STOP at end of file strictly
			// (Telegram sometimes sends padding or we need to respect header limit)
			// Send valid data to user
			if len(data) > 0 {
				if _, err := w.Write(data); err != nil {
					return
				}
				if f, ok := w.(http.Flusher); ok {
					f.Flush()
				}
			}

			// Advance Telegram Offset by the REAL chunk size received (Un-trimmed)
			currentOffset += int64(len(c.Bytes))
		} else {
			return
		}
	}
}

func parseRange(h string) (int64, int64) {
	if !strings.HasPrefix(h, "bytes=") {
		return 0, 0
	}
	parts := strings.Split(strings.TrimPrefix(h, "bytes="), "-")
	val, _ := strconv.ParseInt(parts[0], 10, 64)
	return val, 0
}

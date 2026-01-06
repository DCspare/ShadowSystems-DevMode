package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// 1. Setup the Streaming Multiplexer
	mux := http.NewServeMux()

	// 2. The Direct-Pass Stream Handler
	mux.HandleFunc("/stream/", streamHandler)
    
    // Health probe for Gateway/Prometheus
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, "{\"engine\": \"Go-MTProto\", \"status\": \"online\"}")
	})

	log.Printf("🚀 Shadow Stream Engine ignited on port %s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("Fatal: Engine failure: %v", err)
	}
}

func streamHandler(w http.ResponseWriter, r *http.Request) {
	// Identity Extraction: /stream/{file_id}
	fileID := strings.TrimPrefix(r.URL.Path, "/stream/")
	if fileID == "" {
		http.Error(w, "Resource Identity Missing", http.StatusBadRequest)
		return
	}

	// Proxy Logic per Context_01
	clientIP := r.Header.Get("X-Real-IP")
	log.Printf("[STREAM] ID: %s | User: %s", fileID, clientIP)

	// --- STEP 4 MOCK HANDSHAKE ---
	// For this baseline, we respond with "Ready to Pipe" 
	// To test that the Gateway's secure link passed us the control.
	
	w.Header().Set("Content-Type", "video/mp4")
	w.Header().Set("Accept-Ranges", "bytes") // Crucial for skipping/seeking
	w.Header().Set("X-Shadow-Engine", "Handshake-V1")
    
    w.WriteHeader(http.StatusOK)
    fmt.Fprintf(w, "BYTE_STREAM_INITIATED_FOR_ID_%s", fileID)
}

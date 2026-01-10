// apps/stream-engine/main.go
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	
	"go.uber.org/zap"
	"github.com/joho/godotenv"
	"shadow-stream-engine/core"
)

func main() {
	godotenv.Load("../../.env") 
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	ctx, cancel := context.WithCancel(context.Background())
	client, err := core.InitTelegram(ctx, logger)
	if err != nil {
		logger.Fatal("Init", zap.Error(err))
	}

	go func() {
		logger.Info("🔥 Engine Connecting...")
		
		// The new Run signature calls the warmer logic internally
		err := client.Run(ctx, func(ctx context.Context) error {
			// This blocks until shutdown
			<-ctx.Done()
			return nil
		})
		
		if err != nil {
			logger.Fatal("Engine Died", zap.Error(err))
		}
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/stream/", func(w http.ResponseWriter, r *http.Request) {
		fid := strings.TrimPrefix(r.URL.Path, "/stream/")
		log.Printf("[REQ] %s", fid)
		core.ServeStream(w, r)
	})

	port := os.Getenv("PORT")
	if port == "" { port = "8000" }

	srv := &http.Server{Addr: ":" + port, Handler: mux}
	
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt)
	
	go func() {
		logger.Info("🚀 HTTP Ready", zap.String("port", port))
		srv.ListenAndServe()
	}()

	<-stop
	cancel()
}
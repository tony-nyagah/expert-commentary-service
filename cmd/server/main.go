package main

import (
	"log"
	"net/http"
	"os"

	"github.com/tony-nyagah/expert-commentary-service/internal/api"
	"github.com/tony-nyagah/expert-commentary-service/internal/config"
)

func main() {
	logger := log.New(os.Stdout, "[expert-commentary] ", log.LstdFlags|log.Lmsgprefix)

	cfg, err := config.Load()
	if err != nil {
		logger.Fatalf("failed to load config: %v", err)
	}

	handler := api.NewHandler(logger)
	router := handler.Router()

	logger.Printf("starting server on :%s", cfg.Port)
	if err := http.ListenAndServe(":"+cfg.Port, router); err != nil {
		logger.Fatalf("server failed: %v", err)
	}
}

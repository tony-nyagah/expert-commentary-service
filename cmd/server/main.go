package main

import (
	"log"
	"net/http"
	"os"

	"github.com/tony-nyagah/expert-commentary-service/internal/api"
)

func main() {
	logger := log.New(os.Stdout, "[expert-commentary] ", log.LstdFlags|log.Lmsgprefix)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	handler := api.NewHandler(logger)
	router := handler.Router()

	logger.Printf("starting server on :%s", port)
	if err := http.ListenAndServe(":"+port, router); err != nil {
		logger.Fatalf("server failed: %v", err)
	}
}

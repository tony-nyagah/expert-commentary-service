package config

import (
	"fmt"
	"os"
)

// Config holds all configuration for the service.
type Config struct {
	Port string
}

// Load reads configuration from environment variables.
func Load() (*Config, error) {
	cfg := &Config{
		Port: envOrDefault("PORT", "8080"),
	}

	if cfg.Port == "" {
		return nil, fmt.Errorf("PORT must not be empty")
	}

	return cfg, nil
}

func envOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

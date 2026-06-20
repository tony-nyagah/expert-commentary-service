package api

import (
	"encoding/json"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/tony-nyagah/expert-commentary-service/internal/commentary"
	"github.com/tony-nyagah/expert-commentary-service/internal/models"
)

// Handler holds dependencies for the HTTP server.
type Handler struct {
	logger *log.Logger
}

// NewHandler creates a new Handler.
func NewHandler(logger *log.Logger) *Handler {
	return &Handler{logger: logger}
}

// Router returns a configured chi router.
func (h *Handler) Router() chi.Router {
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)

	r.Route("/api/v1", func(r chi.Router) {
		r.Post("/generate-commentary", h.GenerateCommentary)
		r.Get("/health", h.Health)
	})

	return r
}

// GenerateCommentary handles POST /api/v1/generate-commentary
func (h *Handler) GenerateCommentary(w http.ResponseWriter, r *http.Request) {
	var req models.CommentaryRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.logger.Printf("ERROR: failed to decode request: %v", err)
		writeJSON(w, http.StatusBadRequest, map[string]string{
			"error": "invalid request body: " + err.Error(),
		})
		return
	}

	// Basic validation
	if req.EventID == 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{
			"error": "event_id is required",
		})
		return
	}
	if req.ProgramName == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{
			"error": "program_name is required",
		})
		return
	}

	h.logger.Printf("INFO: generating commentary for event=%d program=%s analytes=%d",
		req.EventID, req.ProgramName, len(req.Analytes))

	resp := commentary.Generate(req)

	writeJSON(w, http.StatusOK, resp)
}

// Health handles GET /api/v1/health
func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
		"service": "expert-commentary-service",
	})
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("ERROR: failed to write response: %v", err)
	}
}

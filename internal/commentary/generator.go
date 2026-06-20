package commentary

import (
	"github.com/tony-nyagah/expert-commentary-service/internal/models"
)

// Generate produces a complete humanized expert commentary from EQA data.
func Generate(req models.CommentaryRequest) models.CommentaryResponse {
	// Step 1: Classify — extract structured findings from raw stats
	c := Classify(req)

	// Step 2: Assemble — build commentary from classifications
	raw := Assemble(c, req)

	// Step 3: Humanize — strip AI-isms, add expert voice
	final := Humanize(raw)

	// Determine confidence based on data quality
	confidence := "high"
	if req.Summary.TotalParticipants < 10 {
		confidence = "medium"
	}
	if req.Summary.TotalParticipants < 5 {
		confidence = "low"
	}
	if c.OverallGrade == "insufficient_data" {
		confidence = "low"
	}

	return models.CommentaryResponse{
		Commentary:  final,
		GeneratedBy: "expert-commentary-service/v1",
		Confidence:  confidence,
		ProgramName: req.ProgramName,
		EventID:     req.EventID,
	}
}

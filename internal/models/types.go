package models

// CommentaryRequest is the payload received from the HuQAS Informatics API.
type CommentaryRequest struct {
	EventID     int         `json:"event_id"`
	ProgramName string      `json:"program_name"`
	ProgramType string      `json:"program_type"` // "quantitative", "qualitative", "multi_response", "drug_sensitivity"
	Summary     Summary     `json:"summary"`
	Analytes    []Analyte   `json:"analytes"`
}

// Summary aggregates the overall event-program performance.
type Summary struct {
	TotalParticipants int `json:"total_participants"`
	Satisfactory      int `json:"satisfactory"`
	Questionable      int `json:"questionable"`
	Unsatisfactory    int `json:"unsatisfactory"`
}

// Analyte holds the statistical results for a single analyte.
type Analyte struct {
	Name          string             `json:"name"`
	ConsensusMean float64            `json:"consensus_mean,omitempty"`
	ConsensusSD   float64            `json:"consensus_sd,omitempty"`
	Unit          string             `json:"unit,omitempty"`
	SDPA          float64            `json:"sdpa,omitempty"` // standard deviation for proficiency assessment
	OutlierCount  int                `json:"outlier_count"`
	ZScoreRange   [2]float64         `json:"z_score_range"` // [min, max]
	GradeCounts   map[string]int     `json:"grade_counts"`  // e.g. {"satisfactory": 140, "questionable": 7, "unsatisfactory": 3}
	// For qualitative programs
	ConcordanceRate float64          `json:"concordance_rate,omitempty"` // 0.0-1.0
	ResponseCounts  map[string]int   `json:"response_counts,omitempty"`  // "Positive": 120, "Negative": 30
}

// CommentaryResponse is the generated expert commentary.
type CommentaryResponse struct {
	Commentary  string `json:"commentary"`
	GeneratedBy string `json:"generated_by"`
	Confidence  string `json:"confidence"` // "high", "medium", "low"
	ProgramName string `json:"program_name"`
	EventID     int    `json:"event_id"`
}

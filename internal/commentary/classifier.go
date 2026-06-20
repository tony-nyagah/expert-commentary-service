package commentary

import (
	"fmt"
	"math"

	"github.com/tony-nyagah/expert-commentary-service/internal/models"
)

// Classification represents the structured findings extracted from EQA data.
type Classification struct {
	OverallGrade    string   // "excellent", "good", "needs_attention", "poor"
	OverallComment  string   // one-line summary
	NotableAnalytes []AnalyteFinding
	HasSystematic   bool
	SystematicNote   string
	HasOutliers     bool
	OutlierAnalytes []string
	Recommendations []string
}

// AnalyteFinding flags a specific analyte with noteworthy results.
type AnalyteFinding struct {
	Name       string
	Grade      string // "satisfactory", "borderline", "unsatisfactory"
	Severity   string // "info", "warning", "critical"
	Detail     string // e.g. "3 extreme outliers (z > 3), negative bias"
	ZRange     string // human-readable z-score range
}

// Classify analyzes EQA statistics and produces structured findings.
func Classify(req models.CommentaryRequest) Classification {
	c := Classification{}

	if len(req.Analytes) == 0 {
		c.OverallGrade = "insufficient_data"
		c.OverallComment = "Insufficient data was available to generate a meaningful commentary for this program."
		return c
	}

	// Determine overall grade from participant-level stats
	c.OverallGrade = classifyOverall(req.Summary)

	// Analyze each analyte
	for _, a := range req.Analytes {
		finding := classifyAnalyte(a)
		if finding.Grade != "satisfactory" {
			c.NotableAnalytes = append(c.NotableAnalytes, finding)
		}
	}

	// Detect systematic bias (same-direction z-score shifts across multiple analytes)
	c.HasSystematic, c.SystematicNote = detectSystematicBias(req.Analytes)

	// Flag outlier presence
	for _, a := range req.Analytes {
		if a.OutlierCount > 0 {
			c.HasOutliers = true
			c.OutlierAnalytes = append(c.OutlierAnalytes, a.Name)
		}
	}

	// Generate recommendations
	c.Recommendations = generateRecommendations(c, req)

	return c
}

func classifyOverall(s models.Summary) string {
	if s.TotalParticipants == 0 {
		return "insufficient_data"
	}
	unsatPct := float64(s.Unsatisfactory) / float64(s.TotalParticipants) * 100
	questPct := float64(s.Questionable) / float64(s.TotalParticipants) * 100

	switch {
	case unsatPct <= 2 && questPct <= 5:
		return "excellent"
	case unsatPct <= 5 && questPct <= 10:
		return "good"
	case unsatPct <= 10:
		return "needs_attention"
	default:
		return "poor"
	}
}

func classifyAnalyte(a models.Analyte) AnalyteFinding {
	f := AnalyteFinding{Name: a.Name}

	// Count grades
	sat := a.GradeCounts["satisfactory"] + a.GradeCounts["S"]
	quest := a.GradeCounts["questionable"] + a.GradeCounts["Q"]
	unsat := a.GradeCounts["unsatisfactory"] + a.GradeCounts["U"]
	total := sat + quest + unsat

	if total == 0 {
		f.Grade = "satisfactory"
		f.Detail = "No grade data available."
		return f
	}

	unsatPct := float64(unsat) / float64(total) * 100
	questPct := float64(quest) / float64(total) * 100

	switch {
	case unsatPct >= 15:
		f.Grade = "unsatisfactory"
		f.Severity = "critical"
	case unsatPct >= 5 || questPct >= 15:
		f.Grade = "borderline"
		f.Severity = "warning"
	case questPct >= 8:
		f.Grade = "borderline"
		f.Severity = "info"
	default:
		f.Grade = "satisfactory"
	}

	// Build detail string
	parts := []string{}
	if unsat > 0 {
		parts = append(parts, fmt.Sprintf("%d unsatisfactory (%d%%)", unsat, int(math.Round(unsatPct))))
	}
	if quest > 0 {
		parts = append(parts, fmt.Sprintf("%d questionable (%d%%)", quest, int(math.Round(questPct))))
	}
	if a.OutlierCount > 0 {
		parts = append(parts, fmt.Sprintf("%d outlier(s)", a.OutlierCount))
	}
	// Z-score range
	f.ZRange = fmt.Sprintf("z: %.1f to %.1f", a.ZScoreRange[0], a.ZScoreRange[1])

	// Detect bias direction
	if math.Abs(a.ZScoreRange[0]) > 2 || math.Abs(a.ZScoreRange[1]) > 2 {
		if a.ZScoreRange[0] < -2 && a.ZScoreRange[1] < 0 {
			parts = append(parts, "negative bias observed")
		} else if a.ZScoreRange[0] > 0 && a.ZScoreRange[1] > 2 {
			parts = append(parts, "positive bias observed")
		} else {
			parts = append(parts, "scatter in both directions")
		}
	}

	if len(parts) > 0 {
		f.Detail = joinParts(parts)
	} else {
		f.Detail = "All results within expected range."
	}

	return f
}

func joinParts(parts []string) string {
	if len(parts) == 0 {
		return ""
	}
	if len(parts) == 1 {
		return parts[0]
	}
	result := parts[0]
	for i := 1; i < len(parts)-1; i++ {
		result += ", " + parts[i]
	}
	result += ", and " + parts[len(parts)-1]
	return result
}

func detectSystematicBias(analytes []models.Analyte) (bool, string) {
	if len(analytes) < 2 {
		return false, ""
	}

	negativeCount := 0
	positiveCount := 0
	for _, a := range analytes {
		// Mean z-score for this analyte (approximate from range)
		meanZ := (a.ZScoreRange[0] + a.ZScoreRange[1]) / 2.0
		if meanZ < -0.5 {
			negativeCount++
		} else if meanZ > 0.5 {
			positiveCount++
		}
	}

	threshold := len(analytes) / 2
	if negativeCount >= threshold {
		return true, "A systematic negative bias was observed across multiple analytes, suggesting possible calibration or methodological issues."
	}
	if positiveCount >= threshold {
		return true, "A systematic positive bias was observed across multiple analytes, suggesting possible calibration or methodological issues."
	}
	return false, ""
}

func generateRecommendations(c Classification, req models.CommentaryRequest) []string {
	var recs []string

	if c.OverallGrade == "poor" || c.OverallGrade == "needs_attention" {
		recs = append(recs, "Laboratories with unsatisfactory performance should review their analytical procedures, including calibration, quality control materials, and reagent handling.")
	}

	if c.HasOutliers {
		recs = append(recs, "Laboratories with outlying results are advised to investigate potential sources of error, including sample handling, instrument maintenance, and operator technique.")
	}

	if c.HasSystematic {
		recs = append(recs, "Participating laboratories showing systematic bias should verify their method calibration and consider participation in additional proficiency testing schemes.")
	}

	for _, a := range c.NotableAnalytes {
		if a.Severity == "critical" {
			recs = append(recs, fmt.Sprintf("The %s assay requires particular attention — review calibration protocols and quality control acceptance criteria.", a.Name))
		}
	}

	// Deduplicate
	seen := make(map[string]bool)
	var unique []string
	for _, r := range recs {
		if !seen[r] {
			seen[r] = true
			unique = append(unique, r)
		}
	}

	return unique
}

package commentary

import (
	"fmt"
	"strings"

	"github.com/tony-nyagah/expert-commentary-service/internal/models"
)

// Assemble builds the full commentary text from a classification.
// Returns raw text before humanization.
func Assemble(c Classification, req models.CommentaryRequest) string {
	var sections []string

	// 1. Opening statement
	sections = append(sections, buildOpening(c, req))

	// 2. Overall performance
	sections = append(sections, buildOverall(c, req))

	// 3. Notable analytes
	if len(c.NotableAnalytes) > 0 {
		sections = append(sections, buildAnalyteSection(c))
	}

	// 4. Systematic bias
	if c.HasSystematic {
		sections = append(sections, c.SystematicNote)
	}

	// 5. Closing / recommendations
	if len(c.Recommendations) > 0 {
		sections = append(sections, buildRecommendations(c))
	}

	// 6. Closing statement
	sections = append(sections, buildClosing(c, req))

	return strings.Join(sections, "\n\n")
}

func buildOpening(c Classification, req models.CommentaryRequest) string {
	participation := fmt.Sprintf("%d laboratories participated in the %s programme.", 
		req.Summary.TotalParticipants, req.ProgramName)
	
	if c.OverallGrade == "insufficient_data" {
		return participation + " " + c.OverallComment
	}

	return participation
}

func buildOverall(c Classification, req models.CommentaryRequest) string {
	sat := req.Summary.Satisfactory
	quest := req.Summary.Questionable
	unsat := req.Summary.Unsatisfactory
	total := req.Summary.TotalParticipants

	// Performance percentages
	satPct := float64(sat) / float64(total) * 100

	switch c.OverallGrade {
	case "excellent":
		return fmt.Sprintf(
			"Overall performance was excellent, with %.0f%% of participants (%d out of %d) achieving satisfactory results across all analytes. Only %d laboratories returned questionable results and %d were unsatisfactory.",
			satPct, sat, total, quest, unsat,
		)
	case "good":
		return fmt.Sprintf(
			"Overall performance was good, with %.0f%% of participants (%d out of %d) achieving satisfactory results. %d laboratories had questionable performance and %d returned unsatisfactory results.",
			satPct, sat, total, quest, unsat,
		)
	case "needs_attention":
		return fmt.Sprintf(
			"Overall performance indicates room for improvement: %.0f%% satisfactory (%d/%d), with %d questionable and %d unsatisfactory results. Several areas warrant closer examination.",
			satPct, sat, total, quest, unsat,
		)
	case "poor":
		return fmt.Sprintf(
			"Overall performance was below expectations, with only %.0f%% of laboratories (%d/%d) achieving satisfactory results. %d questionable and %d unsatisfactory results highlight significant quality concerns.",
			satPct, sat, total, quest, unsat,
		)
	default:
		return ""
	}
}

func buildAnalyteSection(c Classification) string {
	var lines []string

	if len(c.NotableAnalytes) == 1 {
		lines = append(lines, fmt.Sprintf("The %s analyte warrants specific attention.", c.NotableAnalytes[0].Name))
	} else {
		names := make([]string, len(c.NotableAnalytes))
		for i, a := range c.NotableAnalytes {
			names[i] = a.Name
		}
		lines = append(lines, fmt.Sprintf("The following analytes warrant attention: %s.", strings.Join(names, ", ")))
	}

	for _, a := range c.NotableAnalytes {
		line := fmt.Sprintf("  • %s: %s (%s)", a.Name, a.Detail, a.ZRange)
		lines = append(lines, line)
	}

	return strings.Join(lines, "\n")
}

func buildRecommendations(c Classification) string {
	lines := []string{"Recommendations:"}
	for _, rec := range c.Recommendations {
		lines = append(lines, fmt.Sprintf("  • %s", rec))
	}
	return strings.Join(lines, "\n")
}

func buildClosing(c Classification, req models.CommentaryRequest) string {
	switch c.OverallGrade {
	case "excellent":
		return "Participating laboratories are commended for their strong performance and continued commitment to quality."
	case "good":
		return "Participating laboratories are encouraged to maintain their quality systems and address any borderline results before the next proficiency testing round."
	case "needs_attention":
		return "Laboratories are strongly advised to review their analytical performance and implement corrective actions where necessary. Repeat testing may be warranted for consistently underperforming analytes."
	case "poor":
		return "Significant quality issues were identified. Affected laboratories should conduct root cause analysis, implement corrective actions, and consider re-enrollment in a follow-up proficiency testing round."
	default:
		return ""
	}
}

package commentary

import (
	"regexp"
	"strings"
)

// Humanize applies post-processing to strip AI-isms from generated commentary.
// Based on patterns from blader/humanizer (Wikipedia WikiProject AI Cleanup).
func Humanize(text string) string {
	t := text

	// Phase 1: Remove filler phrases (pattern 23)
	fillerPhrases := []struct {
		pattern     string
		replacement string
	}{
		{`[Ii]n order to `, "To "},
		{`[Dd]ue to the fact that `, "Because "},
		{`[Aa]t this point in time`, "Now"},
		{`[Ii]n the event that `, "If "},
		{`has the ability to `, "can "},
		{`[Ii]t is important to note that `, ""},
		{`[Ii]t should be noted that `, ""},
		{`[Ii]t is worth noting that `, ""},
		{`[Ii]t must be noted that `, ""},
	}
	for _, f := range fillerPhrases {
		re := regexp.MustCompile(f.pattern)
		t = re.ReplaceAllString(t, f.replacement)
	}

	// Phase 2: Eliminate AI vocabulary (pattern 7)
	aiWords := []struct {
		word        string
		replacement string
	}{
		{`\badditionally\b`, ""},
		{`\bmoreover\b`, ""},
		{`\bfurthermore\b`, ""},
		{`\bconsequently\b`, "so"},
		{`\bunderscores?\b`, "shows"},
		{`\bhighlights?\b`, "shows"},
		{`\bdelve\b`, "explore"},
		{`\bpivotal\b`, "key"},
		{`\bcrucial\b`, "important"},
		{`\benduring\b`, "lasting"},
	}
	for _, w := range aiWords {
		re := regexp.MustCompile(`(?i)` + w.word)
		t = re.ReplaceAllString(t, w.replacement)
	}

	// Phase 3: Remove hedging (pattern 24)
	hedging := []string{
		`(?i)it could be argued that `,
		`(?i)it might be suggested that `,
		`(?i)it is possible that `,
		`(?i)potentially `,
		`(?i)arguably `,
	}
	for _, h := range hedging {
		re := regexp.MustCompile(h)
		t = re.ReplaceAllString(t, "")
	}

	// Phase 4: Replace copula avoidance (pattern 8)
	// "serves as a" → "is a", "stands as a" → "is a"
	copulaAvoidance := []struct {
		pattern     string
		replacement string
	}{
		{`\bserves as a\b`, "is a"},
		{`\bstands as a\b`, "is a"},
		{`\bfunctions as a\b`, "is a"},
		{`\brepresents a\b`, "is a"},
	}
	for _, c := range copulaAvoidance {
		re := regexp.MustCompile(`(?i)` + c.pattern)
		t = re.ReplaceAllString(t, c.replacement)
	}

	// Phase 5: Remove persuasive authority tropes (pattern 27)
	tropes := []string{
		`(?i)the real question is\s*`,
		`(?i)at its core,?\s*`,
		`(?i)in reality,?\s*`,
		`(?i)what really matters is\s*`,
		`(?i)fundamentally,?\s*`,
	}
	for _, tr := range tropes {
		re := regexp.MustCompile(tr)
		t = re.ReplaceAllString(t, "")
	}

	// Phase 6: Clean up whitespace and punctuation artifacts
	t = cleanWhitespace(t)

	// Phase 7: Vary sentence starts (basic)
	t = varySentenceStarts(t)

	return t
}

func cleanWhitespace(t string) string {
	// Remove extra spaces from removed phrases
	t = regexp.MustCompile(`  +`).ReplaceAllString(t, " ")
	// Remove leading spaces after periods
	t = regexp.MustCompile(`\.  `).ReplaceAllString(t, ". ")
	// Fix double periods
	t = regexp.MustCompile(`\.\.`).ReplaceAllString(t, ".")
	// Remove leading comma
	t = regexp.MustCompile(`^,\s*`).ReplaceAllString(t, "")
	// Clean up ", ." 
	t = regexp.MustCompile(`, \.`).ReplaceAllString(t, ".")
	// Fix sentences starting with lowercase after removal
	re := regexp.MustCompile(`\. ([a-z])`)
	t = re.ReplaceAllStringFunc(t, func(s string) string {
		return ". " + strings.ToUpper(s[2:3]) + s[3:]
	})
	// Trim
	t = strings.TrimSpace(t)
	return t
}

// varySentenceStarts does basic variety injection to avoid monotonous structure.
func varySentenceStarts(t string) string {
	// If every paragraph starts with "Overall" or "The", inject variety
	sentences := regexp.MustCompile(`\. `).Split(t, -1)
	if len(sentences) <= 2 {
		return t
	}

	var result []string
	overallCount := 0
	for _, s := range sentences {
		trimmed := strings.TrimSpace(s)
		if strings.HasPrefix(strings.ToLower(trimmed), "overall") {
			overallCount++
			if overallCount > 1 {
				// Replace second+ "Overall" with varied opener
				openers := []string{
					"Across the board,",
					"Taken together,",
					"Looking at the full picture,",
					"In summary,",
					"Broadly speaking,",
				}
				idx := (overallCount - 2) % len(openers)
				trimmed = openers[idx] + " " + strings.TrimPrefix(trimmed, "Overall")
				trimmed = strings.TrimSpace(trimmed)
				// Fix double capitalization from the prefix removal
				trimmed = regexp.MustCompile(`^([A-Z][a-z]+,) ([A-Z])`).ReplaceAllStringFunc(trimmed, func(m string) string {
					parts := regexp.MustCompile(`, `).Split(m, 2)
					if len(parts) == 2 {
						return parts[0] + ", " + strings.ToLower(parts[1][:1]) + parts[1][1:]
					}
					return m
				})
			}
		}
		result = append(result, trimmed)
	}

	return strings.Join(result, ". ")
}

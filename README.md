# expert-commentary-service

Generates expert commentary for HuQAS Informatics EQA reports. Receives statistical analysis results and returns humanized, domain-specific commentary suitable for inclusion in laboratory proficiency testing reports.

## How it works

1. **Classify** — deterministic rules analyze z-scores, grade distributions, outlier counts, and systematic bias patterns
2. **Assemble** — findings are structured into natural paragraphs using domain-specific templates
3. **Humanize** — post-processing strips AI-isms (filler phrases, hedging, corporate jargon) per the [Wikipedia AI Cleanup patterns](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)

Built for HuQAS but generic enough for any ISO 13528-compliant EQA system.

## Quickstart

```bash
# Build
make build

# Run
make run

# Smoke test (requires jq)
make smoke
```

## API

### `POST /api/v1/generate-commentary`

**Request:**

```json
{
  "event_id": 42,
  "program_name": "Clinical Chemistry",
  "program_type": "quantitative",
  "summary": {
    "total_participants": 150,
    "satisfactory": 130,
    "questionable": 12,
    "unsatisfactory": 8
  },
  "analytes": [
    {
      "name": "Glucose",
      "consensus_mean": 5.2,
      "consensus_sd": 0.15,
      "unit": "mmol/L",
      "sdpa": 0.5,
      "outlier_count": 3,
      "z_score_range": [-4.1, 3.8],
      "grade_counts": {
        "satisfactory": 140,
        "questionable": 7,
        "unsatisfactory": 3
      }
    }
  ]
}
```

**Response:**

```json
{
  "commentary": "138 laboratories participated...",
  "generated_by": "expert-commentary-service/v1",
  "confidence": "high",
  "program_name": "Clinical Chemistry",
  "event_id": 42
}
```

Confidence levels: `high` (≥10 participants), `medium` (5-9), `low` (<5 or insufficient data).

### `GET /api/v1/health`

```json
{"status": "ok", "service": "expert-commentary-service"}
```

## Docker

```bash
docker build -t expert-commentary-service .
docker run -p 8080:8080 expert-commentary-service
```

Or with compose:

```bash
docker compose up -d
```

## Integrating with HuQAS

From the HuQAS Django API, call this service during report generation (`iso13528/reporting_v2/reporting_router.py`):

```python
import requests

resp = requests.post(
    "http://expert-commentary:8080/api/v1/generate-commentary",
    json={
        "event_id": analysis.test_event_id,
        "program_name": program.name,
        "program_type": "quantitative",
        "summary": build_summary(ags),
        "analytes": build_analytes(ags),
    },
    timeout=30,
)
data = resp.json()
EventProgramCommentary.objects.update_or_create(
    test_event=event,
    program=program,
    defaults={"commentary": data["commentary"]},
)
```

## Architecture

```
expert-commentary-service/
├── cmd/server/main.go            # Entry point
├── internal/
│   ├── api/handler.go            # HTTP handlers (chi router)
│   ├── commentary/
│   │   ├── classifier.go         # Deterministic stats → findings
│   │   ├── templates.go          # Findings → structured text
│   │   ├── humanizer.go          # AI-pattern removal
│   │   └── generator.go          # Orchestrator
│   └── models/types.go           # Request/response types
├── Dockerfile                    # Multi-stage (golang → alpine)
├── docker-compose.yml
├── Makefile
└── go.mod
```

## License

MIT

# Expert commentary service

A small FastAPI service that drafts expert commentaries for laboratory proficiency testing (PT) and external quality assessment (EQA) schemes. You send it the results of a test event; it asks an LLM to write the commentary and returns the draft as HTML for a person to review and publish.

It works with any provider that has an OpenAI-compatible chat API, such as DeepSeek, Qwen or Gemini.

## How it fits in

1. Your EQA platform compiles the event's statistics and posts them to `POST /api/v1/commentary/generate`.
2. The service turns them into a prompt and sends it to the LLM.
3. It returns the HTML draft and the token count.
4. Your platform shows the draft to an expert, who edits and publishes it.

The service keeps no data between requests and has no database.

## What gets sent to the LLM

Each request becomes one chat completion call with two messages.

The system message is the fixed set of writing rules in `app/prompts.py`. It contains no event data.

The user message is built from your request, and everything in it comes from what you sent:

- the program name and the event name (the program code is only used to find the description file and in logs; the model is told to use full names, never codes or short forms)
- a program description: `program_description` from the request if you sent one, otherwise the contents of `config/programs/<program code>.md` if that file exists, otherwise a line saying there are no guidelines
- the overall pass rate and the program totals
- for each analyte: its name, whether it's quantitative, its totals and the reviewer's note
- for each sample: its name, assigned value, the counts of acceptable, warning, not acceptable and ungraded results, and the pass rate
- each cohort's name (method, reagent or instrument), result count, acceptable percentage and, if given, mean and CV
- earlier events' names, pass rates and changes
- the common failure modes you listed
- the example commentaries, in full

The call also carries the model name, a temperature of 0.2 and your API key.

The service adds nothing beyond this. It sees only what you put in the request, so keep lab names, lab codes and anything else that identifies a participant out of it. Watch the free-text fields in particular: reviewer notes, failure modes, the program description and example commentaries are passed to the model word for word. Once the prompt reaches the provider, their data retention and training terms apply.

The service's own logs record the program code, event name, provider host, model and any error messages. They don't record the request body or the prompt.

## Running it locally

You need [uv](https://github.com/astral-sh/uv). Install the dependencies:

```bash
uv sync
```

Create a `.env` file:

```env
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_API_KEY=your_provider_api_key_here
# Optional, seconds to wait for the provider
# LLM_TIMEOUT=110
PORT=8005
# Optional: when set, requests must send a matching X-Service-Token header
SERVICE_TOKEN=shared_secret_with_the_calling_backend
```

Without `LLM_API_KEY` the service returns a placeholder commentary, which is enough for development.

Start the server:

```bash
uv run fastapi dev app/main.py --port 8005
```

The API docs are at [http://localhost:8005/docs](http://localhost:8005/docs).

CI runs these on every push and pull request:

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

## LLM providers

Set `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` to switch providers:

| Provider | `LLM_BASE_URL` | Example `LLM_MODEL` |
|---|---|---|
| DeepSeek | `https://api.deepseek.com` | `deepseek-flash`, `deepseek-v4-pro` |
| Qwen (DashScope) | `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1` | `qwen3.8-max` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.8-flash` |

Model names change often, so check the provider's docs. `GET /health` shows the base URL and model in use, and reports `misconfigured` if a key is set without a base URL or model.

## Docker image

Every push to `main` publishes `ghcr.io/tony-nyagah/expert-commentary-service` tagged `latest`, `main` and `sha-<short sha>`. Version tags like `v1.2.3` also publish `1.2.3` and `1.2`. Pin a version or `sha-` tag in deployments.

```bash
docker run -p 8005:8005 \
  -e LLM_BASE_URL=https://api.deepseek.com -e LLM_MODEL=deepseek-flash -e LLM_API_KEY=sk-... \
  -e SERVICE_TOKEN=shared_secret \
  ghcr.io/tony-nyagah/expert-commentary-service:latest
```

## Program descriptions

The model writes a better introduction when it knows what the program tests. You can describe a program in two ways:

1. Send `program_description` in the request.
2. Add a Markdown file to `config/programs/`. The file name is the program code in lower case, so `MALARIA-RDT` loads `config/programs/malaria-rdt.md`.

The request wins if you do both.

## API

### `POST /api/v1/commentary/generate`

Send an `X-Service-Token` header if `SERVICE_TOKEN` is set.

`totals` (for the program and each analyte) and each history entry's `change` are figures you've already worked out. The model is told to quote them and not to do its own arithmetic, so the numbers in the draft can be checked against your data. `example_commentaries` are earlier commentaries for the same program written by people. The model follows their structure and tone but is told not to reuse their figures.

`program_code`, `program_name`, `event_name`, `overall_pass_rate` and `analytes` are required. `totals`, `warning`, `ungraded`, `review_comment`, `assigned_value`, cohort `mean` and `cv`, and the other lists are optional.

```json
{
  "program_code": "MALARIA-RDT",
  "program_name": "Malaria Rapid Diagnostic Tests EQA",
  "event_name": "TE-2026-02",
  "overall_pass_rate": 92.0,
  "totals": {"results": 40, "graded": 40, "acceptable": 36, "pass_rate": 90.0},
  "analytes": [
    {
      "name": "Malaria Antigen",
      "is_quantitative": false,
      "review_comment": "Several false negatives on Sample C",
      "samples": [
        {
          "name": "Sample A",
          "assigned_value": "Positive",
          "participants": 40,
          "acceptable": 36,
          "warning": 0,
          "not_acceptable": 4,
          "ungraded": 0,
          "pass_rate": 90.0
        }
      ],
      "totals": {"results": 40, "graded": 40, "acceptable": 36, "pass_rate": 90.0}
    }
  ],
  "cohorts": [
    {
      "name": "SD BIOLINE",
      "kind": "reagent",
      "participant_count": 30,
      "acceptable_percent": 93.33
    }
  ],
  "common_failure_modes": [
    "Incubation time overrun",
    "Incorrect buffer volume"
  ],
  "history": [
    {
      "event_name": "TE-2026-01",
      "pass_rate": 87.5,
      "change": 4.5
    }
  ],
  "example_commentaries": [
    "<p>This EQA program tests the ability to detect malaria parasites...</p>"
  ]
}
```

Response:

```json
{
  "commentary_html": "<p>This EQA cycle evaluated...</p>",
  "usage_tokens": 1280
}
```

Errors: `401` for a missing or wrong service token, `422` for an invalid request, `500` if the LLM settings are incomplete or something unexpected fails, and `502` if the provider fails or returns an empty reply.

## Project layout

```text
app/
  main.py        FastAPI app, routes and the service token check
  schemas.py     request and response models
  services.py    LLM settings, prompt building and the provider call
  prompts.py     the system instructions and prompt template
config/programs/ optional Markdown descriptions, one per program
tests/           pytest suite
Dockerfile       multi-stage image build
```

## License

MIT. See [LICENSE](LICENSE).

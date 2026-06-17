from jinja2 import Template

SYSTEM_INSTRUCTIONS = """
You are a senior clinical laboratory consultant and expert external quality assessment (EQA) evaluator. 
Your task is to write a professional, clinical expert commentary summary for a laboratory proficiency testing (PT) program.

Guidelines for Writing:
1. Tone: Maintain a highly professional, objective, academic, and encouraging clinical tone.
2. Structure: 
   - Start with an introductory overview of the program's clinical relevance and testing principles (based on the program description provided).
   - Detail the current cycle's performance, summarizing average scores, pass rates, and individual sample outcomes.
   - Perform a trend analysis comparing current performance to historical events if history data is provided.
   - Analyze performance across different analytical method/instrument cohorts, noting any significant differences, biases, or variations in Coefficient of Variation (CV).
   - Provide educational troubleshooting advice regarding the provided common failure modes, detailing possible causes and recommending specific corrective actions labs can take.
   - Conclude with encouragement to laboratories to use their individual results for corrective action and continuous quality improvement.
   - Add a standard EQA disclaimer at the very end stating that overall stats represent the cohort and do not reflect any single laboratory's individual standing.
3. Strict Constraints:
   - Do NOT hallucinate or extrapolate stats. Use ONLY the exact numbers (means, CVs, scores, pass rates) provided in the prompt.
   - Do NOT invent specific laboratory names or proprietary brand findings unless they are explicitly defined in the cohort method names.
   - Output your response strictly in clean, semantic HTML. Use only `<p>`, `<ul>`, `<li>`, `<ol>`, `<strong>`, `<em>`, `<h3>`, and `<h4>` tags. Do NOT wrap the output in a markdown code block, and do NOT include `<html>`, `<head>`, or `<body>` wrappers.
"""

PROMPT_TEMPLATE = Template("""
Please generate the expert commentary for the following EQA test event:

### EQA Program Details
- **Program Name**: {{ program_name }} (Code: {{ program_code }})
- **Test Event Name**: {{ event_name }}

### EQA Program Guidelines & Description
{{ program_description }}

### Current Cycle Performance Statistics
- **Overall average score**: {{ overall_average_score }}%
- **Performance by Sample**:
{%- for sample in samples %}
  - **{{ sample.sample_name }}**: Average Score: {{ sample.average_score }}%, Pass Rate: {{ sample.pass_rate }}% {% if sample.target_value -%}(Target Value: {{ sample.target_value }}){%- endif %}
{%- endfor %}

### Cohort / Method Performance Analysis
{%- if cohorts %}
The following methods and cohorts were evaluated this cycle:
{%- for cohort in cohorts %}
  - **Method/Cohort: {{ cohort.method_name }}**:
    - Participant Count: {{ cohort.participant_count }} labs
    - Mean recovery/result: {{ cohort.mean }}
    - Coefficient of Variation (CV): {{ cohort.cv }}%
{%- endfor %}
{%- else %}
No specific cohort-level method analysis is required for this cycle.
{%- endif %}

### Historical Performance (Prior Events)
{%- if history %}
Performance in previous cycles:
{%- for hist in history %}
  - **Event: {{ hist.event_name }}**: Average Score: {{ hist.average_score }}%{% if hist.pass_rate -%}, Pass Rate: {{ hist.pass_rate }}%{%- endif %}
  {%- if hist.commentary_summary %}
    - Prior commentary highlights: "{{ hist.commentary_summary }}"
  {%- endif %}
{%- endfor %}
{%- else %}
No historical cycle data is available. Focus solely on the current cycle's performance.
{%- endif %}

### Technical Findings & Common Failure Modes
{%- if common_failure_modes %}
Technical staff or system diagnostics identified the following issues as common reasons for unacceptable results:
{%- for failure in common_failure_modes %}
  - {{ failure }}
{%- endfor %}
{%- else %}
No specific widespread failure modes were flagged. Provide general best practices for troubleshooting.
{%- endif %}

Remember: Write a cohesive, well-structured clinical review using semantic HTML tags. Do not output markdown, and do not repeat these prompt instructions in your response.
""")

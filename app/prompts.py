from jinja2 import Template

SYSTEM_INSTRUCTIONS = """
You are a senior clinical laboratory consultant and expert external quality assessment (EQA) evaluator.
Your task is to write a professional, clinical expert commentary summary for a laboratory proficiency testing (PT) program.

Guidelines for Writing:
1. Tone: Maintain a highly professional, objective, academic, and encouraging clinical tone.
2. Example commentaries: If earlier commentaries for this program are provided, they were written by the program's experts. Follow their structure, section order, length, tone and description of the program as closely as possible, so the new commentary reads as the next one in the series.
3. Structure (use this when no example commentaries are provided, and to fill gaps the examples leave):
   - Start with an introductory overview of the program's clinical relevance and testing principles (based on the program description provided).
   - Detail the current cycle's performance, summarizing the overall pass rate and each sample's outcome.
   - Perform a trend analysis comparing current performance to historical events if history data is provided.
   - Compare performance across methods, reagents or instruments if cohort data is provided, noting any cohort that performed notably worse.
   - Provide educational troubleshooting advice regarding the provided common failure modes and reviewer notes, detailing possible causes and recommending specific corrective actions labs can take.
   - Conclude with encouragement to laboratories to use their individual results for corrective action and continuous quality improvement.
   - Add a standard EQA disclaimer at the very end stating that overall stats represent the cohort and do not reflect any single laboratory's individual standing.
4. Strict Constraints:
   - Do NOT hallucinate or extrapolate stats. Use ONLY the exact numbers (counts, pass rates, assigned values, means, CVs) given under the current cycle, cohort and historical sections of the prompt.
   - Do NOT do your own arithmetic. Totals per analyte, program totals and changes from earlier events are provided; quote those instead of adding up, subtracting or averaging figures yourself.
   - NEVER copy numbers, sample outcomes, reagent names or event names from the example commentaries. They describe earlier events; only their wording and structure may be reused.
   - Refer to the program only by its full name exactly as given (e.g. "Blood Parasites"), never by a program code, short form or variant name (e.g. not "BLPA" or "H32BLPA"), even if the example commentaries use one. Use the analytes' full names too. Write any other abbreviation in full the first time you use it.
   - Do NOT invent specific laboratory names or proprietary brand findings unless they are explicitly given as cohort names.
   - Output your response strictly in clean, semantic HTML. Use only `<p>`, `<ul>`, `<li>`, `<ol>`, `<strong>`, `<em>`, `<h3>`, `<h4>`, `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>` and `<td>` tags. A table is a good way to present per-sample results. Do NOT wrap the output in a markdown code block, and do NOT include `<html>`, `<head>`, or `<body>` wrappers.
"""

PROMPT_TEMPLATE = Template("""
Please generate the expert commentary for the following EQA test event:

### EQA Program Details
- **Program Name**: {{ program_name }}
- **Test Event Name**: {{ event_name }}

### EQA Program Guidelines & Description
{{ program_description }}

### Current Cycle Performance Statistics
- **Overall pass rate**: {{ overall_pass_rate }}% (mean of the per-sample pass rates)
{%- if totals %}
- **All results**: {{ totals.results }} results, {{ totals.graded }} graded, {{ totals.acceptable }} acceptable ({{ totals.pass_rate }}% of graded results)
{%- endif %}
{%- for analyte in analytes %}
- **Analyte: {{ analyte.name }}** ({{ "quantitative" if analyte.is_quantitative else "qualitative" }})
  {%- if analyte.totals %}
  - Analyte total: {{ analyte.totals.results }} results, {{ analyte.totals.graded }} graded, {{ analyte.totals.acceptable }} acceptable ({{ analyte.totals.pass_rate }}% of graded results)
  {%- endif %}
  {%- if analyte.review_comment %}
  - Reviewer note: "{{ analyte.review_comment }}"
  {%- endif %}
  {%- for sample in analyte.samples %}
  - **{{ sample.name }}**: {{ sample.participants }} results, {{ sample.acceptable }} acceptable, {% if sample.warning %}{{ sample.warning }} warning, {% endif %}{{ sample.not_acceptable }} not acceptable{% if sample.ungraded %}, {{ sample.ungraded }} ungraded{% endif %}. Pass Rate: {{ sample.pass_rate }}%{% if sample.assigned_value %} (Assigned value: {{ sample.assigned_value }}){% endif %}
  {%- endfor %}
{%- endfor %}

### Method / Reagent / Instrument Performance
{%- if cohorts %}
{%- for cohort in cohorts %}
  - **{{ cohort.kind|capitalize }}: {{ cohort.name }}**: {{ cohort.participant_count }} graded results, {{ cohort.acceptable_percent }}% acceptable{% if cohort.mean is not none %}, mean {{ cohort.mean }}{% endif %}{% if cohort.cv is not none %}, CV {{ cohort.cv }}%{% endif %}
{%- endfor %}
{%- else %}
Only one method/reagent was used, so there is no cohort comparison for this cycle.
{%- endif %}

### Historical Performance (Prior Events)
{%- if history %}
Overall pass rate in previous cycles:
{%- for hist in history %}
  - **{{ hist.event_name }}**: {{ hist.pass_rate }}%{% if hist.change is not none %} (this event is {{ "%+.1f"|format(hist.change) }} percentage points compared with it){% endif %}
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
{% if example_commentaries %}
### Example Commentaries From Earlier Events (style reference only)
The following commentaries were written by the program's experts for earlier events. Match their structure and tone. Do NOT reuse any of their numbers or findings.
{% for example in example_commentaries %}
<example_commentary index="{{ loop.index }}">
{{ example }}
</example_commentary>
{% endfor %}
{%- endif %}
Remember: Write a cohesive, well-structured clinical review using semantic HTML tags. Do not output markdown, and do not repeat these prompt instructions in your response.
""")

from typing import Literal

from pydantic import BaseModel, Field


class SampleStats(BaseModel):
    name: str = Field(..., description="Name of the sample (e.g. Sample A)")
    assigned_value: str | None = Field(
        None,
        description="Expected result for the sample: a reference response, or a consensus mean ± SD with its acceptable range",
    )
    participants: int = Field(..., description="Number of laboratory results evaluated for this sample")
    acceptable: int = Field(..., description="Number of results graded acceptable")
    warning: int = Field(0, description="Number of results graded warning")
    not_acceptable: int = Field(..., description="Number of results graded not acceptable")
    ungraded: int = Field(0, description="Number of results that were not graded or not evaluated")
    pass_rate: float = Field(..., description="Percentage of graded results that were acceptable")


class ResultTotals(BaseModel):
    results: int = Field(..., description="Number of results, including ungraded ones")
    graded: int = Field(..., description="Number of graded results (acceptable, warning or not acceptable)")
    acceptable: int = Field(..., description="Number of results graded acceptable")
    pass_rate: float = Field(..., description="Acceptable results as a percentage of graded results")


class AnalyteStats(BaseModel):
    name: str = Field(..., description="Name of the analyte or test")
    is_quantitative: bool = Field(..., description="Whether the analyte reports numeric results")
    review_comment: str | None = Field(
        None, description="Note left by the scientist who reviewed this analyte's analysis"
    )
    samples: list[SampleStats] = Field(..., description="Performance statistics per sample")
    totals: ResultTotals | None = Field(None, description="The analyte's results across all its samples")


class Cohort(BaseModel):
    name: str = Field(..., description="Name of the method, reagent or instrument")
    kind: Literal["method", "reagent", "instrument"] = Field(..., description="What the cohort groups results by")
    participant_count: int = Field(..., description="Number of graded results from this cohort")
    acceptable_percent: float = Field(..., description="Percentage of the cohort's graded results that were acceptable")
    mean: float | None = Field(None, description="Mean result of the cohort, for quantitative analytes")
    cv: float | None = Field(None, description="Coefficient of Variation (%) of the cohort, for quantitative analytes")


class HistoricalEventStats(BaseModel):
    event_name: str = Field(..., description="Name/code of the earlier test event")
    pass_rate: float = Field(..., description="Overall pass rate in that event")
    change: float | None = Field(None, description="Current overall pass rate minus this event's, in percentage points")


class CommentaryRequest(BaseModel):
    program_code: str = Field(..., description="Unique code identifying the EQA program (e.g. MALARIA-RDT)")
    program_name: str = Field(..., description="Full human-readable name of the program")
    event_name: str = Field(..., description="Name of the current EQA test event")
    overall_pass_rate: float = Field(..., description="Mean of the per-sample pass rates across the program")
    analytes: list[AnalyteStats] = Field(..., description="Performance statistics per analyte and sample")
    totals: ResultTotals | None = Field(None, description="Results across every analyte and sample in the program")
    cohorts: list[Cohort] = Field(default=[], description="Performance grouped by method, reagent or instrument")
    common_failure_modes: list[str] = Field(
        default=[], description="Common causes of failure identified by technical staff"
    )
    program_description: str | None = Field(
        None,
        description="Clinical overview of what this program evaluates. If not provided, the service falls back to local config files.",
    )
    history: list[HistoricalEventStats] = Field(
        default=[], description="Pass rates from earlier events of this program, oldest first"
    )
    example_commentaries: list[str] = Field(
        default=[],
        description="Earlier expert commentaries for this program, written by people, used as examples of structure and tone",
    )


class CommentaryResponse(BaseModel):
    commentary_html: str = Field(..., description="Generated expert commentary formatted in clean semantic HTML")
    usage_tokens: int | None = Field(None, description="Number of LLM tokens consumed during commentary generation")

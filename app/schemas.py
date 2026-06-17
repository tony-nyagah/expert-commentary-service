from pydantic import BaseModel, Field
from typing import List, Optional

class SampleStats(BaseModel):
    sample_name: str = Field(..., description="Name of the sample (e.g. Sample A)")
    target_value: Optional[float] = Field(None, description="The expected target or consensus value, if applicable")
    pass_rate: float = Field(..., description="Percentage of laboratories that achieved an acceptable result")
    average_score: float = Field(..., description="The average score (percentage or scale) achieved by participants for this sample")

class MethodCohort(BaseModel):
    method_name: str = Field(..., description="Name of the analysis method or instrument cohort")
    participant_count: int = Field(..., description="Number of participants in this cohort")
    mean: float = Field(..., description="Mean value of results submitted by this cohort")
    cv: float = Field(..., description="Coefficient of Variation (%) representing the dispersion of results")

class HistoricalEventStats(BaseModel):
    event_name: str = Field(..., description="Name/code of the historical test event")
    average_score: float = Field(..., description="Overall average score achieved in the historical event")
    pass_rate: Optional[float] = Field(None, description="Overall pass rate in the historical event")
    commentary_summary: Optional[str] = Field(
        None, 
        description="A brief summary or text of the prior event's commentary to maintain context continuity"
    )

class CommentaryRequest(BaseModel):
    program_code: str = Field(..., description="Unique code identifying the EQA program (e.g. MALARIA-RDT)")
    program_name: str = Field(..., description="Full human-readable name of the program")
    event_name: str = Field(..., description="Name of the current EQA test event")
    overall_average_score: float = Field(..., description="Overall average score achieved across all samples and cohorts in this event")
    samples: List[SampleStats] = Field(..., description="Performance statistics grouped by sample")
    cohorts: List[MethodCohort] = Field(..., description="Performance statistics grouped by analysis method cohorts")
    common_failure_modes: List[str] = Field(default=[], description="Common causes of failure identified by technical staff or algorithms")
    program_description: Optional[str] = Field(
        None, 
        description="Clinical overview of what this program evaluates. If not provided, the service falls back to local config files."
    )
    history: List[HistoricalEventStats] = Field(
        default=[], 
        description="Performance history of this program over previous cycles to allow trend analysis"
    )

class CommentaryResponse(BaseModel):
    commentary_html: str = Field(..., description="Generated expert commentary formatted in clean semantic HTML")
    usage_tokens: Optional[int] = Field(None, description="Number of LLM tokens consumed during commentary generation")

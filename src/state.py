from typing import TypedDict, Dict, List, Optional, Any, Literal, Annotated
import operator
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class Evidence(BaseModel):
    """Forensic evidence collected by detectives."""
    
    found: bool
    content: Optional[str] = None
    location: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v


class GitCommit(BaseModel):
    """Structured git commit information."""
    
    hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: List[str]
    
    @property
    def is_atomic(self) -> bool:
        """Determine if commit is atomic based on message quality."""
        atomic_patterns = [
            'feat:', 'fix:', 'docs:', 'style:', 'refactor:',
            'perf:', 'test:', 'chore:', 'Add', 'Implement',
            'Update', 'Remove', 'Fix'
        ]
        return any(msg in self.message for msg in atomic_patterns)


class GitForensicEvidence(BaseModel):
    """Git history forensic analysis."""
    
    commits: List[GitCommit]
    commit_count: int
    has_atomic_history: bool
    progression_pattern: Literal['analysis_scaffolding_logic', 
                                 'bulk_dump', 
                                 'monolithic', 
                                 'unknown']
    timestamps: List[datetime]


class CodeStructureEvidence(BaseModel):
    """Code structure forensic analysis."""
    
    architecture_notes_exists: bool
    architecture_notes_paths: List[str] = Field(default_factory=list)
    tool_registered: bool
    tool_location: Optional[str] = None
    system_prompt_contains_instruction: bool
    system_prompt_location: Optional[str] = None
    middleware_exists: bool
    middleware_location: Optional[str] = None
    hashing_implemented: bool
    hashing_location: Optional[str] = None
    trace_writing_implemented: bool
    trace_location: Optional[str] = None
    state_models_detected: bool = False
    state_model_locations: List[str] = Field(default_factory=list)
    graph_fan_out_detected: bool = False
    graph_fan_in_detected: bool = False
    conditional_edges_detected: bool = False
    checkpointer_detected: bool = False
    graph_edge_count: int = 0
    graph_node_count: int = 0


class PdfForensicEvidence(BaseModel):
    """PDF report forensic analysis."""
    
    cognitive_depth: Dict[str, str] = Field(default_factory=dict)
    trust_debt_mentioned: bool
    context_injection_paradox_mentioned: bool
    two_stage_state_machine_mentioned: bool
    claimed_file_paths: List[str] = Field(default_factory=list)
    verified_paths: List[str] = Field(default_factory=list)
    hallucinated_paths: List[str] = Field(default_factory=list)
    retrieval_snippets: Dict[str, List[str]] = Field(default_factory=dict)


class ImageForensicEvidence(BaseModel):
    """Diagram forensic analysis."""
    
    image_count: int
    diagram_types: List[str] = Field(default_factory=list)
    handshake_visualized: bool
    flow_description: Optional[str] = None
    contains_reasoning_loop: bool
    data_payloads_labeled: bool


class ForensicEvidenceCollection(BaseModel):
    """Complete evidence collection from all detectives."""
    
    git: Optional[GitForensicEvidence] = None
    code: Optional[CodeStructureEvidence] = None
    pdf: Optional[PdfForensicEvidence] = None
    images: Optional[ImageForensicEvidence] = None
    raw_evidence: Dict[str, Evidence] = Field(default_factory=dict)


def merge_evidences(
    left: Optional[ForensicEvidenceCollection],
    right: Optional[ForensicEvidenceCollection],
) -> ForensicEvidenceCollection:
    """Merge evidence collections for parallel graph updates."""
    if left is None:
        return right or ForensicEvidenceCollection()
    if right is None:
        return left

    return ForensicEvidenceCollection(
        git=right.git or left.git,
        code=right.code or left.code,
        pdf=right.pdf or left.pdf,
        images=right.images or left.images,
        raw_evidence={**left.raw_evidence, **right.raw_evidence},
    )


def merge_criterion_judgments(
    left: Optional[Dict[str, "CriterionJudgment"]],
    right: Optional[Dict[str, "CriterionJudgment"]],
) -> Dict[str, "CriterionJudgment"]:
    """Merge criterion judgments for parallel judge updates."""
    if not left:
        return right or {}
    if not right:
        return left

    merged: Dict[str, "CriterionJudgment"] = dict(left)
    for key, judgment in right.items():
        if key in merged:
            merged[key].opinions.extend(judgment.opinions)
        else:
            merged[key] = judgment
    return merged


class JudicialOpinion(BaseModel):
    """Opinion from a specific judge persona."""
    
    judge: Literal['Prosecutor', 'Defense', 'TechLead']
    criterion_id: str
    score: int = Field(ge=0, le=5)
    argument: str
    cited_evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    
    @validator('score')
    def validate_score(cls, v):
        if v not in [0, 1, 2, 3, 4, 5]:
            raise ValueError('Score must be 0-5')
        return v


class CriterionJudgment(BaseModel):
    """Collection of opinions for a single criterion."""
    
    criterion_id: str
    criterion_name: str
    opinions: List[JudicialOpinion]
    
    @property
    def score_variance(self) -> float:
        scores = [o.score for o in self.opinions]
        if len(scores) < 2:
            return 0.0
        return max(scores) - min(scores)
    
    @property
    def consensus_score(self) -> Optional[float]:
        if not self.opinions:
            return None
        return sum(o.score for o in self.opinions) / len(self.opinions)


class FinalVerdict(BaseModel):
    """Supreme court synthesis output."""
    
    criterion_id: str
    final_score: int = Field(ge=0, le=5)
    dissent_summary: str
    remediation_plan: List[str] = Field(default_factory=list)
    security_override_applied: bool = False
    fact_supremacy_applied: bool = False


class AuditReport(BaseModel):
    """Complete audit report output."""
    
    repo_url: str
    timestamp: datetime = Field(default_factory=datetime.now)
    executive_summary: str
    criterion_breakdown: List[FinalVerdict]
    remediation_plan: Dict[str, List[str]]
    raw_evidence_summary: Dict[str, Any]
    criterion_narratives: Dict[str, str] = Field(default_factory=dict)


class AgentState(TypedDict):
    """LangGraph state definition."""
    
    # Input
    repo_url: str
    pdf_path: Optional[str]
    
    # Processing state
    repo_cloned: bool
    temp_dir: Optional[str]
    
    # Evidence collection
    evidences: Annotated[ForensicEvidenceCollection, merge_evidences]
    evidence_errors: Annotated[List[str], operator.add]
    
    # Judicial opinions
    opinions: Annotated[List[JudicialOpinion], operator.add]
    criterion_judgments: Annotated[Dict[str, CriterionJudgment], merge_criterion_judgments]
    
    # Final output
    final_verdicts: List[FinalVerdict]
    audit_report: Optional[AuditReport]
    report_path: Optional[str]
    
    # Metadata
    trace_id: str
    errors: List[str]
    warnings: List[str]

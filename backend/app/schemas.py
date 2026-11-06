import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class UserOut(BaseModel):
    id: UUID
    email: str
    locale: str
    display_name: str | None
    country_code: str | None
    birth_year: int | None
    is_minor: bool
    created_at: datetime
    updated_at: datetime
    guardian_consent_at: datetime | None = None
    has_openrouter_key: bool = False


class GuardianConsentIn(BaseModel):
    confirmed: bool = True


class OpenRouterKeyIn(BaseModel):
    api_key: str = Field(min_length=8, max_length=256)


class OpenRouterKeyOut(BaseModel):
    has_openrouter_key: bool


class UserPatch(BaseModel):
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    locale: str | None = Field(default=None, pattern="^(en|es)$")
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    country_code: str | None = Field(default=None, pattern="^[A-Z]{2}$")


class KnowledgeNodeOut(BaseModel):
    id: UUID
    slug: str
    title: str
    description: str
    node_type: str
    domain: str


class KnowledgeEdgeOut(BaseModel):
    parent_id: UUID
    child_id: UUID
    edge_type: str
    weight: float


class GraphOut(BaseModel):
    nodes: list[KnowledgeNodeOut]
    edges: list[KnowledgeEdgeOut]


MAX_ANSWER_BYTES = 4096


def _bounded_answer(v: dict) -> dict:
    if len(json.dumps(v)) > MAX_ANSWER_BYTES:
        raise ValueError("answer too large")
    return v


class AnswerIn(BaseModel):
    """``{part_index, answer}`` (the legacy ``step_index``/``submitted_latex`` body is gone)."""

    item_id: UUID
    part_index: int = Field(ge=0, le=50)
    answer: dict

    _bounded = field_validator("answer")(_bounded_answer)


class EvaluateStepIn(AnswerIn):
    session_id: UUID | None = None
    hint_level: int = Field(default=0, ge=0, le=3)
    scaffold_level: int = Field(default=2, ge=1, le=3)
    latency_ms: int = Field(default=0, ge=0)


class EvaluateStepOut(BaseModel):
    verdict: str
    is_success: bool
    decided_by: str
    structure_ok: bool
    session_id: UUID
    attempt_id: int
    fsrs_grade: int | None = None
    fsrs_due_at: datetime | None = None
    is_final_step: bool
    scaffold_level: int = Field(default=2, ge=1, le=3)
    genui: dict | None = None
    score: float | None = None
    feedback: str | None = None
    grader: str | None = None


class DueNodeOut(BaseModel):
    node_id: UUID
    slug: str
    title: str
    due_date: datetime
    fsrs_state: str
    reps: int


class DueQueueOut(BaseModel):
    nodes: list[DueNodeOut]


class SessionStepOut(BaseModel):
    latex: str
    operation: str | None = None
    justification: str | None = None
    gap_latex: str | None = None


class SessionPartOut(BaseModel):
    """A part as the client sees it: never ``answer_spec``."""

    component: str | None = None
    grader: str | None = None
    props: dict = Field(default_factory=dict)


class SessionItemOut(BaseModel):
    id: UUID
    statement_latex: str
    prompt: str | None = None
    # ponytail: math steps stay client-visible (Reveal step + gap prefill), low-stakes practice;
    # upgrade path = a server reveal endpoint. Empty for non-sympy items (would leak the key).
    steps: list[SessionStepOut]
    step_count: int
    prompt_md: str | None = None
    stimulus: list[dict] | None = None
    parts: list[SessionPartOut] = Field(default_factory=list)


def _strip_beats(beats: list[dict]) -> list[dict]:
    from app.services.component_catalog import strip_beats

    return strip_beats(beats)


def _public_sources(v: list | None) -> list[dict]:
    """``research_brief.sources`` → ``[{title, url}]`` (http(s) only; quotes stay server-side)."""
    out = []
    for s in v or []:
        url = str(s.get("url") or "") if isinstance(s, dict) else ""
        if url.startswith(("https://", "http://")):
            out.append({"title": str(s.get("title") or url)[:200], "url": url[:500]})
    return out[:8]


class CitedLessonOut(BaseModel):
    """Lesson text the learner sees: only research-cited URLs survive (Doc 10 R4)."""

    primer_md: str | None = None
    lesson_beats: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)

    _public = field_validator("sources", mode="before")(_public_sources)
    # Stored beats embed problem plans with answer keys; every response strips them.
    _no_keys = field_validator("lesson_beats")(_strip_beats)

    @model_validator(mode="after")
    def _cited_only(self) -> "CitedLessonOut":
        from app.services.component_catalog import norm_url, scrub_urls

        urls = {norm_url(s["url"]) for s in self.sources}
        self.primer_md = scrub_urls(self.primer_md, urls)
        self.lesson_beats = scrub_urls(self.lesson_beats, urls)
        return self


class SessionNodeOut(CitedLessonOut):
    id: UUID
    slug: str
    title: str
    source_attribution: str | None = None
    # Subject profile notation (none|math|chem|code): KaTeX `$…$` only for math/chem.
    notation: str | None = None


class SessionStartIn(BaseModel):
    session_id: UUID | None = None
    path_id: UUID | None = None
    node_id: UUID | None = None
    item_id: UUID | None = None


class SessionStartOut(BaseModel):
    session_id: UUID
    item: SessionItemOut | None
    node: SessionNodeOut | None
    step_index: int = 0
    done: bool = False
    ai_enabled: bool = False
    path_id: UUID | None = None
    scaffold_level: int = Field(default=2, ge=1, le=3)
    genui: dict | None = None
    needs_materialize: bool = False
    materialize_node_id: UUID | None = None
    # Lesson teach beats are readable while problems are still being generated.
    teach_ready: bool = False
    build_status: str | None = None
    build_error: str | None = None


class SessionCompleteIn(BaseModel):
    active_seconds: int = Field(default=0, ge=0)
    micro_breaks_triggered: int = Field(default=0, ge=0)
    micro_breaks_skipped: int = Field(default=0, ge=0)
    post_session_rest_completed: bool = False


class SessionCompleteOut(BaseModel):
    session_id: UUID
    completed_at: datetime
    active_seconds: int
    correct_count: int
    incorrect_count: int


class SessionHintIn(BaseModel):
    session_id: UUID
    item_id: UUID
    step_index: int = Field(ge=0)
    hint_level: int = Field(ge=1, le=3)
    locale: str = Field(default="en", pattern="^(en|es)$")
    submitted_latex: str | None = Field(default=None, max_length=500)
    verdict: str | None = None


class SessionHintOut(BaseModel):
    socratic_prompt: str
    source: str  # SYSTEM2 | TEMPLATE
    ai_enabled: bool
    hint_level: int


class TutorChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=600)


class SessionTutorChatIn(BaseModel):
    session_id: UUID
    item_id: UUID
    message: str = Field(min_length=2, max_length=500)
    locale: str = Field(default="en", pattern="^(en|es)$")
    history: list[TutorChatMessage] = Field(default_factory=list, max_length=12)


class SessionTutorChatOut(BaseModel):
    reply: str
    refused: bool
    source: str
    ai_enabled: bool
    turn_index: int
    capped: bool
    max_turns: int = 8


class SubjectProfile(BaseModel):
    """Clamped by ``services.subject_profile.clamp_profile`` before it is ever built."""

    subject: str
    family_hint: str = ""
    categories: list[str]
    notation: str
    code_language: str | None = None
    target_language: str | None = None
    instruction_language: str = "en"
    answer_modes: list[str] = Field(default_factory=list)
    level: str = "beginner"
    allowed: bool = True
    reason: str = ""


class PathProfileIn(BaseModel):
    goal_text: str = Field(min_length=3, max_length=500)
    exam_markdown: str | None = Field(default=None, max_length=80_000)
    source_markdowns: list[str] = Field(default_factory=list, max_length=5)


class PathIngestIn(BaseModel):
    goal_text: str = Field(min_length=3, max_length=500)
    # Learner-confirmed profile from POST /paths/profile; clamped again (inferred when absent).
    subject_profile: dict | None = None
    deadline_date: str | None = None  # YYYY-MM-DD
    daily_budget_mins: int | None = Field(default=None, ge=5, le=480)
    exam_markdown: str | None = Field(default=None, max_length=80_000)
    source_markdowns: list[str] = Field(default_factory=list, max_length=5)
    use_corpus: bool = True
    # Deprecated alias — treated as exam_markdown when exam_markdown is empty
    optional_syllabus_markdown: str | None = Field(default=None, max_length=80_000)


class UploadParseOut(BaseModel):
    text: str
    char_count: int


class PlacementGenerateIn(BaseModel):
    goal_text: str = Field(min_length=3, max_length=500)
    subject_profile: dict | None = None


class PlacementQuestionOut(BaseModel):
    id: str = Field(max_length=64)
    prompt_md: str = Field(default="", max_length=1000)
    statement_latex: str = Field(default="", max_length=500)
    skill_hint: str = Field(default="", max_length=64)
    difficulty: int = 1
    parts: list[SessionPartOut] = Field(default_factory=list, max_length=1)
    # HMAC-signed answer_spec: the client holds the exam until submit but cannot rewrite the key.
    key: str = Field(max_length=4096)


class PlacementGenerateOut(BaseModel):
    questions: list[PlacementQuestionOut]


class PlacementAnswerIn(BaseModel):
    id: str = Field(max_length=64)
    answer: dict = Field(default_factory=dict)

    _bounded = field_validator("answer")(_bounded_answer)


class PlacementGradeIn(BaseModel):
    questions: list[PlacementQuestionOut] = Field(max_length=10)
    answers: list[PlacementAnswerIn] = Field(max_length=10)


class PlacementGradeOut(BaseModel):
    summary_markdown: str
    correct_count: int
    total: int
    weak_skills: list[str]
    strong_skills: list[str]


class MaterializeOut(BaseModel):
    path_id: UUID
    node_id: UUID
    status: str  # STARTED | READY
    stream_url: str
    item_count: int = 0
    build_status: str | None = None  # PLANNED | BUILDING | TEACH_READY | READY | FAILED
    teach_ready: bool = False


class PathDraftNodeOut(BaseModel):
    slug: str
    title: str
    node_id: UUID | None = None


class PathIngestOut(BaseModel):
    path_id: UUID
    status: str
    initial_draft_nodes: list[PathDraftNodeOut]
    stream_url: str


class PathImproveIn(BaseModel):
    improvement_prompt: str = Field(min_length=3, max_length=500)


class PathRebuildIn(BaseModel):
    """Optional; empty means rebuild from the current target_goal."""
    goal_text: str | None = Field(default=None, min_length=3, max_length=500)


class PathSummaryOut(BaseModel):
    path_id: UUID
    title: str
    target_goal: str
    status: str
    deadline_date: str | None = None
    daily_budget_mins: int | None = None
    node_count: int = 0
    created_at: datetime


class PathNodeOut(CitedLessonOut):
    node_id: UUID
    slug: str
    title: str
    sequence_index: int
    is_draft: bool
    content_ready: bool = False
    build_status: str | None = None
    build_error: str | None = None
    p_mastery: float
    label: str  # mastered | frontier | locked | unknown
    source_attribution: str | None = None
    source_license: str | None = None
    source_url: str | None = None


class PathOut(BaseModel):
    path_id: UUID
    title: str
    target_goal: str
    status: str
    deadline_date: str | None = None
    daily_budget_mins: int | None = None
    nodes: list[PathNodeOut]
    frontier_node_ids: list[UUID]
    refining: bool = False


class DiagnosticProbeOut(BaseModel):
    done: bool = False
    probe_index: int = 0
    node_id: UUID | None = None
    node_title: str | None = None
    item_id: UUID | None = None
    statement_latex: str | None = None
    prompt_md: str | None = None
    parts: list[SessionPartOut] = Field(default_factory=list)
    notation: str | None = None  # subject profile notation: KaTeX only for math/chem
    frontier_node_ids: list[UUID] = []


class DiagnosticAnswerIn(BaseModel):
    """``answer`` per the probe's first part grader."""

    node_id: UUID
    item_id: UUID
    answer: dict
    latency_ms: int = Field(default=0, ge=0)
    probe_index: int = Field(ge=1, le=5)

    _bounded = field_validator("answer")(_bounded_answer)


class OfflineAttemptIn(AnswerIn):
    client_attempt_id: UUID
    latency_ms: int = Field(default=0, ge=0)
    hint_level: int = Field(default=0, ge=0, le=3)
    scaffold_level: int = Field(default=2, ge=1, le=3)


class SessionSyncIn(BaseModel):
    attempts: list[OfflineAttemptIn]


class SessionSyncAttemptOut(BaseModel):
    client_attempt_id: UUID
    status: str = "accepted"  # accepted | skipped | failed
    attempt_id: int | None = None
    verdict: str | None = None
    is_success: bool | None = None
    reason: str | None = None


class SessionSyncOut(BaseModel):
    results: list[SessionSyncAttemptOut]

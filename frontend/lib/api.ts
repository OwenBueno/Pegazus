const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UserProfile = {
  id: string;
  email: string;
  locale: string;
  display_name: string | null;
  country_code: string | null;
  birth_year: number | null;
  is_minor: boolean;
  guardian_consent_at?: string | null;
  has_openrouter_key?: boolean;
};

export type GraphPayload = {
  nodes: { id: string; slug: string; title: string; description: string }[];
  edges: { parent_id: string; child_id: string; edge_type: string }[];
};

export type UserPatchBody = {
  birth_year?: number;
  locale?: string;
  display_name?: string;
  country_code?: string;
};

export type SessionStep = {
  latex: string;
  operation: string | null;
  justification?: string | null;
  gap_latex?: string | null;
};

export type SessionItem = {
  id: string;
  statement_latex: string;
  prompt?: string | null;
  steps: SessionStep[];
  step_count: number;
  prompt_md?: string | null;
  stimulus?: Record<string, unknown> | null;
  /** Answer-key free; answer_spec never leaves the server. */
  parts?: SessionPart[];
};
export type SessionPart = { component: string; grader: string; props: Record<string, unknown> };
/** Grader-specific answer: {latex} | {ids} | {pairs} | {value, unit?} | {text} | ... */
export type PartAnswer = Record<string, unknown>;
export type LessonBeat = {
  type: string;
  title?: string;
  body_md?: string;
  item_id?: string;
  genui_plan?: { widgets?: Array<string | { type: string; props?: Record<string, unknown> }> };
  demo_steps?: { latex: string }[];
  layout?: "stack" | "split" | "focus";
  visual?: { type: string; props: Record<string, unknown> };
};

/** A research citation: the only URLs lesson content may link. */
export type LessonSource = { title: string; url: string };

export type SessionNode = {
  id: string;
  slug: string;
  title: string;
  primer_md?: string | null;
  source_attribution?: string | null;
  lesson_beats?: LessonBeat[];
  sources?: LessonSource[];
  /** Subject profile notation; `$…$` is KaTeX only for math/chem (null = legacy math node). */
  notation?: "none" | "math" | "chem" | "code" | null;
};
export type SessionStart = {
  session_id: string;
  item: SessionItem | null;
  node: SessionNode | null;
  step_index: number;
  done: boolean;
  ai_enabled?: boolean;
  path_id?: string | null;
  scaffold_level?: number;
  genui?: unknown;
  needs_materialize?: boolean;
  materialize_node_id?: string | null;
  /** Teach beats are designed; problems are still being generated. */
  teach_ready?: boolean;
  build_status?: BuildStatus | null;
  /** Learner-safe reason when build_status is FAILED. */
  build_error?: string | null;
};

export type BuildStatus = "PLANNED" | "BUILDING" | "TEACH_READY" | "READY" | "FAILED";

export type EvaluateStepResult = {
  verdict: string;
  is_success: boolean;
  decided_by: string;
  structure_ok: boolean;
  session_id: string;
  attempt_id: number;
  fsrs_grade: number | null;
  fsrs_due_at: string | null;
  is_final_step: boolean;
  scaffold_level?: number;
  genui?: unknown;
  score?: number;
  feedback?: string | null;
  grader?: string;
};

export type SessionHintResult = {
  socratic_prompt: string;
  source: string;
  ai_enabled: boolean;
  hint_level: number;
};

export type SessionCompleteResult = {
  session_id: string;
  completed_at: string;
  active_seconds: number;
  correct_count: number;
  incorrect_count: number;
};

export type DueQueue = {
  nodes: {
    node_id: string;
    slug: string;
    title: string;
    due_date: string;
    fsrs_state: string;
    reps: number;
  }[];
};

async function apiFetch<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 204) {
    return undefined as T;
  }
  if (!res.ok) {
    const text = await res.text();
    let msg = text;
    try {
      const detail = JSON.parse(text)?.detail;
      if (typeof detail === "string") msg = detail;
    } catch {
      /* keep raw text */
    }
    throw new Error(msg || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function getMe(token: string) {
  return apiFetch<UserProfile>("/api/v1/me", token);
}

export function patchMe(token: string, body: UserPatchBody) {
  return apiFetch<UserProfile>("/api/v1/me", token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteMe(token: string) {
  return apiFetch<void>("/api/v1/me", token, { method: "DELETE" });
}

export function getGraph(token: string) {
  return apiFetch<GraphPayload>("/api/v1/graph", token);
}

export function startSession(
  token: string,
  sessionId?: string | null,
  pathId?: string | null,
  opts?: { nodeId?: string | null; itemId?: string | null },
) {
  return apiFetch<SessionStart>("/api/v1/session/start", token, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId ?? null,
      path_id: pathId ?? null,
      node_id: opts?.nodeId ?? null,
      item_id: opts?.itemId ?? null,
    }),
  });
}

export function evaluateStep(
  token: string,
  body: {
    item_id: string;
    part_index: number;
    answer: PartAnswer;
    session_id: string;
    hint_level?: number;
    scaffold_level?: number;
    latency_ms?: number;
  },
) {
  return apiFetch<EvaluateStepResult>("/api/v1/session/evaluate-step", token, {
    method: "POST",
    body: JSON.stringify({
      scaffold_level: 2,
      hint_level: 0,
      latency_ms: 0,
      ...body,
    }),
  });
}

export function completeSession(
  token: string,
  sessionId: string,
  body: {
    active_seconds: number;
    micro_breaks_triggered?: number;
    micro_breaks_skipped?: number;
    post_session_rest_completed?: boolean;
  },
) {
  return apiFetch<SessionCompleteResult>(
    `/api/v1/session/${sessionId}/complete`,
    token,
    {
      method: "POST",
      body: JSON.stringify({
        micro_breaks_triggered: 0,
        micro_breaks_skipped: 0,
        post_session_rest_completed: false,
        ...body,
      }),
    },
  );
}

export function getDue(token: string) {
  return apiFetch<DueQueue>("/api/v1/session/due", token);
}

export function requestHint(
  token: string,
  body: {
    session_id: string;
    item_id: string;
    step_index: number;
    hint_level: number;
    locale?: string;
    submitted_latex?: string;
    verdict?: string;
  },
) {
  return apiFetch<SessionHintResult>("/api/v1/session/hint", token, {
    method: "POST",
    body: JSON.stringify({ locale: "en", ...body }),
  });
}

export type TutorChatMessage = { role: "user" | "assistant"; content: string };

export type TutorChatResult = {
  reply: string;
  refused: boolean;
  source: string;
  ai_enabled: boolean;
  turn_index: number;
  capped: boolean;
  max_turns: number;
};

export function tutorChat(
  token: string,
  body: {
    session_id: string;
    item_id: string;
    message: string;
    locale?: string;
    history?: TutorChatMessage[];
  },
) {
  return apiFetch<TutorChatResult>("/api/v1/session/tutor-chat", token, {
    method: "POST",
    body: JSON.stringify({
      locale: "en",
      history: [],
      ...body,
    }),
  });
}

export type SocraticAskResult = {
  intent: string;
  refused: boolean;
  socratic_prompt: string;
  steps: { latex: string; locked: boolean }[];
  exchange_index: number;
  session_id: string;
  genui: unknown;
};

export function socraticAsk(
  token: string,
  body: {
    query: string;
    locale?: string;
    exchange_index: number;
    prior_prompts?: string[];
    session_id?: string | null;
  },
) {
  return apiFetch<SocraticAskResult>("/api/v1/socratic/ask", token, {
    method: "POST",
    body: JSON.stringify({
      locale: "en",
      prior_prompts: [],
      session_id: body.session_id ?? null,
      ...body,
    }),
  });
}

export type PathSummary = {
  path_id: string;
  title: string;
  target_goal: string;
  status: string;
  deadline_date: string | null;
  daily_budget_mins: number | null;
  node_count: number;
  created_at: string;
};

export type PathIngestResult = {
  path_id: string;
  status: string;
  initial_draft_nodes: { slug: string; title: string; node_id: string | null }[];
  stream_url: string;
};

export type PathDetail = {
  path_id: string;
  title: string;
  target_goal: string;
  status: string;
  deadline_date: string | null;
  daily_budget_mins: number | null;
  nodes: {
    node_id: string;
    slug: string;
    title: string;
    sequence_index: number;
    is_draft: boolean;
    content_ready?: boolean;
    build_status?: BuildStatus | null;
    build_error?: string | null;
    p_mastery: number;
    label: string;
    primer_md?: string | null;
    lesson_beats?: LessonBeat[];
    sources?: LessonSource[];
    source_attribution?: string | null;
    source_license?: string | null;
    source_url?: string | null;
  }[];
  frontier_node_ids: string[];
  refining?: boolean;
};

export type DiagnosticProbe = {
  done: boolean;
  probe_index: number;
  node_id: string | null;
  node_title: string | null;
  item_id: string | null;
  statement_latex: string | null;
  prompt_md?: string | null;
  parts?: { component: string | null; grader: string; props: Record<string, unknown> }[];
  notation?: SessionNode["notation"];
  frontier_node_ids: string[];
};

/** Raw input → grader answer (contract: choice ids, numeric value, sympy latex, else text). */
export function answerFor(grader: string | undefined, raw: string): PartAnswer {
  const s = raw.trim();
  if (grader === "choice") return { ids: s ? [s] : [] };
  if (grader === "sympy") return { latex: s };
  if (grader === "numeric") {
    const n = Number(s);
    // Non-finite input still goes up as text so it grades wrong instead of erroring.
    return s && Number.isFinite(n) ? { value: n } : { text: s };
  }
  return { text: s };
}

export type SubjectCategory =
  | "core"
  | "math"
  | "science"
  | "language"
  | "humanities"
  | "code"
  | "media";
export type SubjectNotation = "none" | "math" | "chem" | "code";

export type SubjectProfile = {
  subject: string;
  family_hint: string;
  categories: SubjectCategory[];
  notation: SubjectNotation;
  code_language: "python" | "javascript" | null;
  target_language: string | null;
  instruction_language: string;
  answer_modes: string[];
  level: "beginner" | "intermediate" | "advanced";
  allowed: boolean;
  reason: string;
};

export function inferSubjectProfile(
  token: string,
  body: { goal_text: string; exam_markdown?: string | null; source_markdowns?: string[] },
) {
  return apiFetch<SubjectProfile>("/api/v1/paths/profile", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function ingestPath(
  token: string,
  body: {
    goal_text: string;
    deadline_date?: string | null;
    daily_budget_mins?: number | null;
    exam_markdown?: string | null;
    source_markdowns?: string[];
    use_corpus?: boolean;
    subject_profile?: SubjectProfile | null;
  },
) {
  return apiFetch<PathIngestResult>("/api/v1/paths/ingest", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function parsePathUpload(token: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_URL}/api/v1/paths/uploads/parse`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
  });
  if (!res.ok) {
    throw new Error((await res.text()) || res.statusText);
  }
  return (await res.json()) as { text: string; char_count: number };
}

export type PlacementQuestion = {
  id: string;
  prompt_md: string;
  statement_latex: string;
  skill_hint: string;
  difficulty: number;
  parts: { component: string | null; grader: string; props: Record<string, unknown> }[];
  /** Opaque signed answer key; send back unchanged. */
  key: string;
};

export function generatePlacement(
  token: string,
  goal_text: string,
  subject_profile?: SubjectProfile | null,
) {
  return apiFetch<{ questions: PlacementQuestion[] }>(
    "/api/v1/paths/placement/generate",
    token,
    {
      method: "POST",
      body: JSON.stringify(subject_profile ? { goal_text, subject_profile } : { goal_text }),
    },
  );
}

export function gradePlacement(
  token: string,
  body: {
    questions: PlacementQuestion[];
    answers: { id: string; answer: PartAnswer }[];
  },
) {
  return apiFetch<{
    summary_markdown: string;
    correct_count: number;
    total: number;
    weak_skills: string[];
    strong_skills: string[];
  }>("/api/v1/paths/placement/grade", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function materializeNode(token: string, pathId: string, nodeId: string) {
  return apiFetch<{
    path_id: string;
    node_id: string;
    status: string;
    stream_url: string;
    item_count: number;
    build_status?: BuildStatus | null;
    teach_ready?: boolean;
  }>(`/api/v1/paths/${pathId}/nodes/${nodeId}/materialize`, token, {
    method: "POST",
  });
}

/** SSE until node_ready or materialize_failed. */
export type MaterializeOutcome =
  | { status: "ready" }
  | { status: "failed"; error: string };

export async function streamMaterializeUntilReady(
  token: string,
  pathId: string,
  nodeId: string,
  onEvent?: (name: string, data: unknown) => void,
): Promise<MaterializeOutcome> {
  const res = await fetch(
    `${API_URL}/api/v1/paths/${pathId}/nodes/${nodeId}/materialize/stream`,
    {
      headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
    },
  );
  if (!res.ok || !res.body) {
    throw new Error((await res.text()) || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let outcome: MaterializeOutcome = {
    status: "failed",
    error: "Materialize stream ended without node_ready",
  };
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const chunks = buf.split("\n\n");
    buf = chunks.pop() ?? "";
    for (const chunk of chunks) {
      let eventName = "message";
      let dataLine = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!dataLine) continue;
      let data: unknown = dataLine;
      try {
        data = JSON.parse(dataLine);
      } catch {
        /* keep string */
      }
      onEvent?.(eventName, data);
      if (eventName === "node_ready") {
        outcome = { status: "ready" };
      }
      if (eventName === "materialize_failed") {
        const d = data as { error?: string; reason?: string };
        outcome = {
          status: "failed",
          error: String(d?.error || d?.reason || "Materialize failed"),
        };
      }
    }
  }
  return outcome;
}

/** Share one prepare across Strict Mode remounts / double effects. */
const _materializeInflight = new Map<string, Promise<MaterializeOutcome>>();

export function ensureNodeMaterialized(
  token: string,
  pathId: string,
  nodeId: string,
  onEvent?: (name: string, data: unknown) => void,
): Promise<MaterializeOutcome> {
  const key = `${pathId}:${nodeId}`;
  const existing = _materializeInflight.get(key);
  if (existing) return existing;

  const run = (async () => {
    const started = await materializeNode(token, pathId, nodeId);
    if (started.status === "READY") return { status: "ready" as const };
    return streamMaterializeUntilReady(token, pathId, nodeId, onEvent);
  })().finally(() => {
    _materializeInflight.delete(key);
  });

  _materializeInflight.set(key, run);
  return run;
}

/** Materialize (SSE until node_ready), then start the session on that node. */
const _prepareAndStartInflight = new Map<string, Promise<SessionStart>>();

export async function prepareLessonAndStart(
  token: string,
  pathId: string,
  nodeId: string,
  sessionId: string | null | undefined,
  onEvent?: (name: string, data: unknown) => void,
): Promise<SessionStart> {
  const key = `${pathId}:${nodeId}`;
  const existing = _prepareAndStartInflight.get(key);
  if (existing) return existing;

  const run = (async () => {
    const mat = await ensureNodeMaterialized(token, pathId, nodeId, onEvent);
    if (mat.status === "failed") {
      throw new Error(mat.error || "Could not prepare this lesson");
    }
    // node_ready is emitted after the persist commit, so one start normally suffices;
    // a single retry covers a read racing that commit.
    let last = await startSession(token, sessionId, pathId, { nodeId });
    if (last.needs_materialize || !last.item || !last.node) {
      await new Promise((r) => setTimeout(r, 500));
      last = await startSession(token, last.session_id, pathId, { nodeId });
    }
    if (last.needs_materialize || !last.item || !last.node) {
      throw new Error(last.build_error || "Lesson still not ready after materialize");
    }
    return last;
  })().finally(() => {
    _prepareAndStartInflight.delete(key);
  });

  _prepareAndStartInflight.set(key, run);
  return run;
}

export function listPaths(token: string) {
  return apiFetch<PathSummary[]>("/api/v1/paths", token);
}

export function deletePath(token: string, pathId: string) {
  return apiFetch<void>(`/api/v1/paths/${pathId}`, token, { method: "DELETE" });
}

export function improvePath(
  token: string,
  pathId: string,
  improvement_prompt: string,
) {
  return apiFetch<PathIngestResult>(`/api/v1/paths/${pathId}/improve`, token, {
    method: "POST",
    body: JSON.stringify({ improvement_prompt }),
  });
}

export function rebuildPath(
  token: string,
  pathId: string,
  goal_text?: string | null,
) {
  return apiFetch<PathIngestResult>(`/api/v1/paths/${pathId}/rebuild`, token, {
    method: "POST",
    body: JSON.stringify(goal_text ? { goal_text } : {}),
  });
}

export function getPath(token: string, pathId: string) {
  return apiFetch<PathDetail>(`/api/v1/paths/${pathId}`, token);
}

/** Consume SSE until graph_complete or graph_failed. Throws on failure/timeout. */
export async function streamPathUntilComplete(
  token: string,
  pathId: string,
  onEvent?: (name: string, data: unknown) => void,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/paths/${pathId}/stream`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
  });
  if (!res.ok || !res.body) {
    throw new Error(await res.text() || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      throw new Error("Path stream ended without completing");
    }
    buf += decoder.decode(value, { stream: true });
    const chunks = buf.split("\n\n");
    buf = chunks.pop() ?? "";
    for (const chunk of chunks) {
      let eventName = "message";
      let dataLine = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!dataLine) continue;
      let data: unknown = dataLine;
      try {
        data = JSON.parse(dataLine);
      } catch {
        /* keep string */
      }
      onEvent?.(eventName, data);
      if (eventName === "graph_complete") {
        const d = data as { total_nodes?: number; error?: string; timeout?: boolean };
        if (d?.timeout || d?.error || (d?.total_nodes != null && d.total_nodes < 1)) {
          throw new Error(
            String(d.error || "Path draft finished with no lessons"),
          );
        }
        return;
      }
      if (eventName === "graph_failed") {
        const d = data as { error?: string; timeout?: boolean };
        throw new Error(
          String(
            d?.error ||
              (d?.timeout
                ? "Path draft timed out"
                : "Path draft failed"),
          ),
        );
      }
    }
  }
}

export function startDiagnostic(token: string, pathId: string) {
  return apiFetch<DiagnosticProbe>(
    `/api/v1/paths/${pathId}/diagnostic/start`,
    token,
    { method: "POST", body: "{}" },
  );
}

export function answerDiagnostic(
  token: string,
  pathId: string,
  body: {
    node_id: string;
    item_id: string;
    answer: PartAnswer;
    latency_ms?: number;
    probe_index: number;
  },
) {
  return apiFetch<DiagnosticProbe>(
    `/api/v1/paths/${pathId}/diagnostic/answer`,
    token,
    { method: "POST", body: JSON.stringify(body) },
  );
}

/** Onboarding complete when name, country, and birth year are set. */
export function isProfileComplete(me: UserProfile): boolean {
  return (
    Boolean(me.display_name?.trim()) &&
    Boolean(me.country_code) &&
    me.birth_year != null
  );
}

export function needsGuardianConsent(me: UserProfile): boolean {
  return Boolean(me.is_minor && !me.guardian_consent_at);
}

export function postGuardianConsent(token: string) {
  return apiFetch<UserProfile>("/api/v1/me/guardian-consent", token, {
    method: "POST",
    body: JSON.stringify({ confirmed: true }),
  });
}

export function putOpenRouterKey(token: string, apiKey: string) {
  return apiFetch<{ has_openrouter_key: boolean }>(
    "/api/v1/me/openrouter-key",
    token,
    { method: "PUT", body: JSON.stringify({ api_key: apiKey }) },
  );
}

export function deleteOpenRouterKey(token: string) {
  return apiFetch<{ has_openrouter_key: boolean }>(
    "/api/v1/me/openrouter-key",
    token,
    { method: "DELETE" },
  );
}

export function syncOfflineAttempts(
  token: string,
  sessionId: string,
  attempts: {
    client_attempt_id: string;
    item_id: string;
    part_index: number;
    answer: PartAnswer;
    latency_ms?: number;
    hint_level?: number;
  }[],
) {
  return apiFetch<{
    results: {
      client_attempt_id: string;
      status: "accepted" | "skipped" | "failed" | string;
      attempt_id?: number | null;
      verdict?: string | null;
      is_success?: boolean | null;
      reason?: string | null;
    }[];
  }>(`/api/v1/session/${sessionId}/sync`, token, {
    method: "POST",
    body: JSON.stringify({ attempts }),
  });
}

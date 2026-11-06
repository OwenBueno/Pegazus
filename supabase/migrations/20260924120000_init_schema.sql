-- Pegazus P0-lite schema (Doc 04 §2.1) + auth bridge + RLS

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS & COGNITIVE PROFILES
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    locale VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    birth_year SMALLINT NULL,
    is_minor BOOLEAN NOT NULL DEFAULT FALSE,
    guardian_consent_at TIMESTAMPTZ NULL,

    target_retention_rate NUMERIC(3, 2) NOT NULL DEFAULT 0.90,
    fsrs_weights REAL[] NULL,
    preferred_session_duration_mins INT NOT NULL DEFAULT 45,

    custom_openrouter_api_key_encrypted BYTEA NULL,

    CONSTRAINT chk_fsrs_weights_len CHECK (fsrs_weights IS NULL OR array_length(fsrs_weights, 1) = 21)
);

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email)
  VALUES (NEW.id, COALESCE(NEW.email, NEW.id::text))
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 2. KNOWLEDGE GRAPH: ATOMIC NODES
CREATE TYPE node_type_enum AS ENUM ('CONCEPT', 'SKILL');
CREATE TYPE domain_enum AS ENUM ('MATHEMATICS', 'DEVOPS', 'LANGUAGE');

CREATE TABLE public.knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain domain_enum NOT NULL DEFAULT 'MATHEMATICS',
    slug VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    node_type node_type_enum NOT NULL DEFAULT 'CONCEPT',
    element_interactivity_weight NUMERIC(3, 2) NOT NULL DEFAULT 0.50,
    canonical_equation_latex TEXT NULL,
    expected_ast_signature JSONB NULL,
    source_url TEXT NULL,
    source_license VARCHAR(64) NULL,
    source_attribution TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. KNOWLEDGE GRAPH: DEPENDENCY EDGES (DAG)
CREATE TYPE edge_type_enum AS ENUM ('PREREQUISITE_OF', 'TRANSFERS_TO');

CREATE TABLE public.knowledge_edges (
    parent_id UUID NOT NULL REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    edge_type edge_type_enum NOT NULL DEFAULT 'PREREQUISITE_OF',
    weight NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    PRIMARY KEY (parent_id, child_id, edge_type),
    CONSTRAINT chk_no_self_loops CHECK (parent_id <> child_id)
);

CREATE INDEX idx_edges_child ON public.knowledge_edges(child_id);

-- 4. ITEM BANK
CREATE TYPE item_status_enum AS ENUM ('DRAFT', 'VERIFIED', 'RETIRED');
CREATE TYPE item_source_enum AS ENUM ('SEEDED', 'GENERATED');

CREATE TABLE public.items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    statement_latex TEXT NOT NULL,
    steps JSONB NOT NULL,
    difficulty_estimate NUMERIC(3, 2) NOT NULL DEFAULT 0.50,
    status item_status_enum NOT NULL DEFAULT 'DRAFT',
    source item_source_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_items_node_verified ON public.items(node_id) WHERE status = 'VERIFIED';

-- 5. FSRS-6 USER MEMORY STATE
CREATE TYPE fsrs_state_enum AS ENUM ('LEARNING', 'REVIEW', 'RELEARNING');

CREATE TABLE public.user_node_states (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    fsrs_state fsrs_state_enum NOT NULL DEFAULT 'LEARNING',
    difficulty NUMERIC(4, 2) NULL,
    stability NUMERIC(10, 4) NULL,
    last_review_at TIMESTAMPTZ NULL,
    due_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    p_mastery NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
    reps INT NOT NULL DEFAULT 0,
    lapses INT NOT NULL DEFAULT 0,
    current_scaffold_level SMALLINT NOT NULL DEFAULT 2,
    PRIMARY KEY (user_id, node_id),
    CONSTRAINT chk_scaffold CHECK (current_scaffold_level BETWEEN 1 AND 3)
);

CREATE INDEX idx_user_node_states_due ON public.user_node_states(user_id, due_date ASC);

-- 6. LEARNING PLANS
CREATE TYPE plan_status_enum AS ENUM ('DRAFTING', 'ACTIVE', 'COMPLETED', 'ARCHIVED');

CREATE TABLE public.learning_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    target_goal TEXT NOT NULL,
    deadline_date DATE NULL,
    daily_budget_mins INT NULL,
    status plan_status_enum NOT NULL DEFAULT 'DRAFTING',
    estimated_total_minutes INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_path_constraint CHECK (deadline_date IS NOT NULL OR daily_budget_mins IS NOT NULL)
);

CREATE TABLE public.path_nodes (
    path_id UUID NOT NULL REFERENCES public.learning_paths(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    sequence_index INT NOT NULL,
    is_draft BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (path_id, node_id),
    UNIQUE (path_id, sequence_index)
);

-- 7. SESSIONS
CREATE TABLE public.session_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    path_id UUID NULL REFERENCES public.learning_paths(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    active_seconds INT NOT NULL DEFAULT 0,
    micro_breaks_triggered INT NOT NULL DEFAULT 0,
    micro_breaks_skipped INT NOT NULL DEFAULT 0,
    post_session_rest_completed BOOLEAN NOT NULL DEFAULT FALSE,
    llm_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0
);

CREATE INDEX idx_session_logs_user_recent ON public.session_logs(user_id, started_at DESC);

-- 8. ATTEMPTS
CREATE TABLE public.attempts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES public.session_logs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES public.items(id) ON DELETE CASCADE,
    step_index SMALLINT NOT NULL,
    submitted_latex TEXT NOT NULL,
    verdict VARCHAR(40) NOT NULL,
    is_success BOOLEAN NOT NULL,
    hint_level SMALLINT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL,
    scaffold_level SMALLINT NOT NULL,
    fsrs_grade SMALLINT NULL,
    decided_by VARCHAR(10) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attempts_user_recent ON public.attempts(user_id, created_at DESC);

-- RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_node_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_paths ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.path_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_own ON public.users
  FOR SELECT TO authenticated USING (id = auth.uid());
CREATE POLICY users_update_own ON public.users
  FOR UPDATE TO authenticated USING (id = auth.uid()) WITH CHECK (id = auth.uid());

CREATE POLICY kn_select_auth ON public.knowledge_nodes
  FOR SELECT TO authenticated USING (true);
CREATE POLICY ke_select_auth ON public.knowledge_edges
  FOR SELECT TO authenticated USING (true);
CREATE POLICY items_select_auth ON public.items
  FOR SELECT TO authenticated USING (status = 'VERIFIED');

CREATE POLICY uns_own ON public.user_node_states
  FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY lp_own ON public.learning_paths
  FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY pn_own ON public.path_nodes
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.learning_paths lp WHERE lp.id = path_id AND lp.user_id = auth.uid()))
  WITH CHECK (EXISTS (SELECT 1 FROM public.learning_paths lp WHERE lp.id = path_id AND lp.user_id = auth.uid()));
CREATE POLICY sl_own ON public.session_logs
  FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY attempts_own ON public.attempts
  FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- Service role bypasses RLS by default; seed runs as postgres/superuser.

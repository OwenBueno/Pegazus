-- Durable lesson build state, per-node research brief, critic review.

ALTER TABLE public.path_nodes
  ADD COLUMN IF NOT EXISTS build_status TEXT NOT NULL DEFAULT 'PLANNED'
    CHECK (build_status IN ('PLANNED', 'BUILDING', 'TEACH_READY', 'READY', 'FAILED')),
  ADD COLUMN IF NOT EXISTS build_error TEXT NULL,
  ADD COLUMN IF NOT EXISTS build_started_at TIMESTAMPTZ NULL;

UPDATE public.path_nodes SET build_status = 'READY' WHERE is_draft = FALSE;

ALTER TABLE public.knowledge_nodes
  ADD COLUMN IF NOT EXISTS research_brief JSONB NULL,
  ADD COLUMN IF NOT EXISTS research_brief_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS lesson_review JSONB NULL;

-- Previously only created by scripts/ensure_lesson_beats.py; materialize writes it.
ALTER TABLE public.items
  ADD COLUMN IF NOT EXISTS prompt TEXT NULL;

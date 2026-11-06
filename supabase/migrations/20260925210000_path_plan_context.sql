-- Lazy path: store goal/exam/source digests for on-demand materialize (not full PDFs).
ALTER TABLE public.learning_paths
  ADD COLUMN IF NOT EXISTS plan_context JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Lesson beat sequences generated once at materialize (intro → problems).
ALTER TABLE public.knowledge_nodes
  ADD COLUMN IF NOT EXISTS lesson_beats JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Optional cached GenUI widget plan per item (AI-chosen once).
ALTER TABLE public.items
  ADD COLUMN IF NOT EXISTS genui_plan JSONB NULL;

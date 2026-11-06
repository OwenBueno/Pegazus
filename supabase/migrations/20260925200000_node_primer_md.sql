-- Add instructional primer markdown on knowledge nodes (read-only; not FSRS-graded).
ALTER TABLE public.knowledge_nodes
  ADD COLUMN IF NOT EXISTS primer_md TEXT;

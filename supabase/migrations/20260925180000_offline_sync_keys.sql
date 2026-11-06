-- Offline sync idempotency keys (P5-lite)
CREATE TABLE IF NOT EXISTS public.offline_sync_keys (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    client_attempt_id UUID NOT NULL,
    attempt_id BIGINT NULL REFERENCES public.attempts(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, client_attempt_id)
);

ALTER TABLE public.offline_sync_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY osk_own ON public.offline_sync_keys
  FOR ALL TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

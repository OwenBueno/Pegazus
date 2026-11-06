-- Profile fields for onboarding / settings
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(80) NULL,
  ADD COLUMN IF NOT EXISTS country_code CHAR(2) NULL;

COMMENT ON COLUMN public.users.display_name IS 'Preferred first name or nickname shown in the app';
COMMENT ON COLUMN public.users.country_code IS 'ISO 3166-1 alpha-2; MX primary market for now';

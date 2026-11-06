import psycopg
from app.config import settings

c = psycopg.connect(settings.database_url)
c.execute(
    "ALTER TABLE public.learning_paths "
    "ADD COLUMN IF NOT EXISTS plan_context JSONB NOT NULL DEFAULT '{}'::jsonb"
)
c.commit()
print("plan_context ok")
c.close()

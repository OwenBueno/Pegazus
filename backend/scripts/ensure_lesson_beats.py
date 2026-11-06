import psycopg
from app.config import settings

c = psycopg.connect(settings.database_url)
c.execute(
    "ALTER TABLE public.knowledge_nodes "
    "ADD COLUMN IF NOT EXISTS lesson_beats JSONB NOT NULL DEFAULT '[]'::jsonb"
)
c.execute(
    "ALTER TABLE public.items ADD COLUMN IF NOT EXISTS genui_plan JSONB NULL"
)
c.execute(
    "ALTER TABLE public.items ADD COLUMN IF NOT EXISTS prompt TEXT NULL"
)
c.commit()
print("lesson_beats + genui_plan + prompt ok")
c.close()

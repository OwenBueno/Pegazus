from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = "super-secret-jwt-token-with-at-least-32-characters-long"
    api_cors_origins: str = "http://localhost:3000"
    minor_age_threshold: int = 18

    openrouter_api_key: str = ""
    # Empty string means auto: enabled only when key is set.
    ai_enabled: str = ""
    byo_encryption_key: str = ""
    jev_model: str = "typesafe/jev-1.13"
    system2_model: str = "deepseek/deepseek-v4.1-flash"
    system2_fallback_model: str = "z-ai/glm-5.3-flash"
    jev_timeout_ms: int = 400
    # Item/primer/beats LLM calls — 8s is too tight for OpenRouter cold starts
    system2_timeout_s: float = 45.0
    # Per-item calls are small; fail fast and let llm.chat retry instead of one long wait.
    item_timeout_s: float = 25.0
    llm_max_concurrency: int = 8
    # OpenRouter reasoning effort; provider-default reasoning made one design call take 5+ min.
    # Empty = provider default.
    llm_reasoning_effort: str = "low"
    lesson_workers: int = 3
    # Empty = auto (on when AI is on). Uses OpenRouter's web plugin for per-lesson research.
    research_web: str = ""
    research_brief_ttl_days: int = 30
    jev_choice_confidence: float = 0.70
    jev_score_confidence: float = 0.60
    # rubric_llm (FreeResponse) stops calling the LLM once a session spent this; key-term fallback after.
    rubric_session_cap_usd: float = 0.05

    @property
    def research_web_on(self) -> bool:
        if self.research_web.lower() in ("0", "false", "no", "off"):
            return False
        return self.ai_on or self.research_web.lower() in ("1", "true", "yes", "on")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def ai_on(self) -> bool:
        if self.ai_enabled.lower() in ("0", "false", "no", "off"):
            return False
        if self.ai_enabled.lower() in ("1", "true", "yes", "on"):
            return bool(self.openrouter_api_key)
        return bool(self.openrouter_api_key)


settings = Settings()

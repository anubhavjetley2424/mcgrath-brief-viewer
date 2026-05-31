"""Environment configuration loaded from .env at startup."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
N8N_STAGE_CHANGE_WEBHOOK: str = os.getenv("N8N_STAGE_CHANGE_WEBHOOK", "")
N8N_DRAFT_APPROVED_WEBHOOK: str = os.getenv("N8N_DRAFT_APPROVED_WEBHOOK", "")
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

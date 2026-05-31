"""Supabase client factory. Uses service_role key (bypasses RLS — dev only)."""
from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

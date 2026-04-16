import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Create and return a Supabase client using environment variables."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

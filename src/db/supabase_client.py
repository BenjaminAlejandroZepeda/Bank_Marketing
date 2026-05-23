
import os
from dotenv import load_dotenv
from supabase import Client, create_client

if os.getenv("ENV") != "production":
    load_dotenv()

_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase

    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise Exception("Faltan variables de entorno SUPABASE_URL / SUPABASE_KEY")

        _supabase = create_client(url, key)

    return _supabase
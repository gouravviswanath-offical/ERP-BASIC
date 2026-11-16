"""Shared settings + Groq client. Change the model in one place."""
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_STEPS = 5  # safety limit: max tool-call rounds per agent run

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY missing. Copy .env.example to .env and add your key.")
        _client = Groq(api_key=key)
    return _client

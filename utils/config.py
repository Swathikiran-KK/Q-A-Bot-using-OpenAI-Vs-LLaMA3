import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Optional vector DB
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# ==== Models (defaults are safe) ====
OPENROUTER_TEXT_MODEL   = os.getenv("OPENROUTER_TEXT_MODEL",   "openai/gpt-4o-mini")
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini")  # same route supports images


# Use one of Groq’s current models (older llama3-8b-8192 is decommissioned)
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")

# Rough costs (for display)
COST_MAP = {
    "openai/gpt-4o-mini:input": 0.150,
    "openai/gpt-4o-mini:output": 0.600,
    "openai/gpt-4o-audio-preview:input": 0.150,   # use same estimate
    "openai/gpt-4o-audio-preview:output": 0.600,
    "llama-3.1-8b-instant:input": 0.0,
    "llama-3.1-8b-instant:output": 0.0,
}

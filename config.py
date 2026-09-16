import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- OpenAI Configuration (Loaded exclusively from .env) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY)

OUTPUT_FILE = "saved_surveys.json"
RESPONSES_FILE = "responses.json"
FINALIZED_DIR = "finalized_templates"

ALLOWED_SCALE_TYPES = [
    "nps", "csat", "ces", "rating",
    "text", "radio", "mcq", "matrix", "file"
]

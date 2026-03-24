import os
from dotenv import load_dotenv

load_dotenv()

# --- ENVIRONMENT & PATHS ---
ENV = os.getenv("APP_ENV", "local")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if ENV == "production":
    OUTPUT_DIR = "/tmp/assets"
else:
    OUTPUT_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- API KEYS ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_API_KEY_1 = os.getenv("GEMINI_API_KEY_1")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# --- GOOGLE SHEET ---
G_SPREADSHEET_NAME = os.getenv("G_SPREADSHEET_NAME", "Youtube_English")
SHEET_NAME = os.getenv("SHEET_NAME", "Main")

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")


# --- MODEL CONFIGS ---
IDEA_GENERATION_MODEL = os.getenv("IDEA_GENERATION_MODEL")
SCRIPT_IMAGE_PROMPT_MODEL = os.getenv("SCRIPT_IMAGE_PROMPT_MODEL")
AUDIO_GEN_MODEL = os.getenv("AUDIO_GEN_MODEL")
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL")
VIDEO_METADATA_GENERATION_MODEL = os.getenv("VIDEO_METADATA_GENERATION_MODEL")

# --- AWS CONFIG ---
AWS_PROFILE = os.getenv("AWS_PROFILE") #if ENV == "local" else None
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("S3_BUCKET_NAME", "zeteon-media")
DYNAMO_TABLE_NAME = os.getenv("DYNAMO_TABLE_NAME", "Zeteon_State_Store")
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# --- SOCIAL ACCESS ---
INSTA_ACCESS_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
INSTA_ACCOUNT_ID = os.getenv("INSTA_ACCOUNT_ID")


# --- VOICE CONFIG ---
VOICE_IDS = [v.strip() for v in os.getenv("ELEVENLABS_VOICE_IDS", "").split(",") if v.strip()]

# --- API ENDPOINTS ---
IDEA_GENERATION_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{IDEA_GENERATION_MODEL}:generateContent?key={GEMINI_API_KEY_1}"
)

CLAUDE_SCRIPT_IMAGE_PROMPT_URL = (
    f"https://api.anthropic.com/v1/messages"
)

ELEVENLABS_VOICE_GENERATION_API_URL = (
    f"https://api.elevenlabs.io/v1/text-to-speech"
)

IMAGEN_IMAGE_GENERATION_API_URL_1 = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{IMAGEN_MODEL}:predict?key={GEMINI_API_KEY_1}"
)

IMAGEN_IMAGE_GENERATION_API_URL_2 = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{IMAGEN_MODEL}:predict?key={GEMINI_API_KEY_2}"
)



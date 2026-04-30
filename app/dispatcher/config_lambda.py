import os
from pathlib import Path

# 1. DETECT ENVIRONMENT
# Lambda sets 'LAMBDA_TASK_ROOT'. ECS/Worker usually won't.
IS_LAMBDA = "LAMBDA_TASK_ROOT" in os.environ
TASK_ROOT = os.environ.get("LAMBDA_TASK_ROOT", os.path.dirname(os.path.abspath(__file__)))

# 2. FILE SYSTEM HANDLING
# Lambda ONLY allows writing to /tmp. Worker can write to local 'assets'.
if IS_LAMBDA:
    OUTPUT_DIR = "/tmp/assets"
else:
    # Use a relative path from the script location for the worker
    OUTPUT_DIR = os.path.join(TASK_ROOT, "assets")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. DYNAMIC AUTH PATHS
# This works for both because you'll bake these files into both Docker images
CREDENTIALS_JSON = os.path.join(TASK_ROOT, "credentials.json")
TOKEN_PICKLE = os.path.join(TASK_ROOT, "token.pickle")
CLIENT_SECRET_JSON = os.path.join(TASK_ROOT, "client_secret.json")

# 4. Some more dependencies
G_SPREADSHEET_NAME = os.getenv("G_SPREADSHEET_NAME", "Youtube_English")
SHEET_NAME = os.getenv("SHEET_NAME", "Main")
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")
STEP_FUNCTION_ARN = os.getenv("STEP_FUNCTION_ARN")

# --- AWS CONFIG ---
AWS_S3_BUCKET = os.getenv("S3_BUCKET_NAME", "zeteon-media")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
ECS_CLUSTER = os.getenv("ECS_CLUSTER_NAME", "ZeteonCluster")
ECS_TASK_DEFINITION = os.getenv("ECS_TASK_DEFINITION", "zeteon-worker-task")
ECS_SUBNET_ID = os.getenv("ECS_SUBNET_ID")
ECS_SECURITY_GROUP = os.getenv("ECS_SECURITY_GROUP") 

IDEA_GENERATION_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- API ENDPOINTS ---
IDEA_GENERATION_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{IDEA_GENERATION_MODEL}:generateContent?key={GEMINI_API_KEY}"
)
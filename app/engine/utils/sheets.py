import os
import gspread
import logging
from config import G_SPREADSHEET_NAME, OUTPUT_DIR

logger = logging.getLogger(__name__)

def get_worksheet(name):
    """
    Lazy-loads the Google Sheet client.
    Supports local dev and AWS paths.
    """
    # 1. Setup paths
    aws_path = os.path.join(OUTPUT_DIR, "credentials.json")
    # Using absolute path for local dev to be safe
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(os.path.dirname(current_dir), "credentials.json")

    # 2. Find which one actually exists
    if os.path.exists(aws_path):
        creds_path = aws_path
    elif os.path.exists(local_path):
        creds_path = local_path
    else:
        # If neither exists, we fail early with a clear message
        error_msg = f"Missing credentials.json! Looked in: {aws_path} AND {local_path}"
        logger.error(f"❌ {error_msg}")
        raise FileNotFoundError(error_msg)

    try:
        logger.info(f"🔐 Authenticating Google Sheets with: {creds_path}")
        gc = gspread.service_account(filename=creds_path)
        sh = gc.open(G_SPREADSHEET_NAME)
        return sh.worksheet(name)
    except Exception as e:
        logger.error(f"❌ Google Sheets Auth Failed: {e}")
        raise e
import aioboto3
import logging
import sys
import os
from config_lambda import AWS_S3_BUCKET, AWS_REGION

# --- LOGGING CONFIGURATION (AWS READY) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonPipeline")

# Create the session once at the top level
session = aioboto3.Session(region_name=AWS_REGION)

async def download_file_from_s3(s3_key: str, local_path: str):
    """Async Download: Retrieves S3 object to local disk (/tmp/)."""
    # Use 'sts' client to log identity right before the S3 call
    async with session.client("s3") as s3, session.client("sts") as sts:
        try:
            # IDENTITY LOGGING
            identity = await sts.get_caller_identity()
            logger.info(f"🔍 DEBUG: Lambda Identity -> {identity['Arn']}")
            logger.info(f"🔍 DEBUG: Attempting S3 Key -> '{s3_key}'")

            await s3.download_file(AWS_S3_BUCKET, s3_key, local_path)
            logger.info(f"📥 Asset downloaded from s3: {s3_key}")
        except Exception as e:
            logger.error(f"❌ Asset download failed: {e}")
            raise

async def load_prompt_from_s3(s3_key: str, local_path: str) -> str:
    # Ensure local_path is in /tmp/ if running in Lambda
    if not local_path.startswith("/tmp/"):
        local_path = os.path.join("/tmp", os.path.basename(local_path))
        
    await download_file_from_s3(s3_key, local_path)
    with open(local_path, "r", encoding="utf-8") as f:
        return f.read()
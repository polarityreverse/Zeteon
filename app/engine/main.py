import sys
import os
import logging
import asyncio
import traceback
import boto3
import requests  # Ensure 'requests' is in your requirements.txt
from dotenv import load_dotenv

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonWorker")

# Silence noisy third-party logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("langgraph_checkpoint_aws").setLevel(logging.WARNING)

# --- HELPER FUNCTIONS ---

def notify_telegram(message):
    """Sends a status update to Telegram via Bot API."""
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        logger.warning("⚠️ Telegram credentials missing. Skipping notification.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Use HTML for bolding/formatting
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"❌ Telegram notify failed: {e}")

def update_sheet_status(row_idx, status):
    """Updates the status column in Google Sheets."""
    try:
        from utils.sheets import get_worksheet
        from config import SHEET_NAME
        sheet = get_worksheet(SHEET_NAME)
        # Assuming Column 3 is your Status column
        sheet.update_cell(int(row_idx), 3, status)
        logger.info(f"📑 Sheet updated: Row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"❌ Failed to update Google Sheet: {e}")

def bootstrap_engine():
    """Environment Injection after Shell Script sync."""
    base_output = "/tmp/assets" if os.getenv("APP_ENV") == "production" else "assets"
    env_path = os.path.join(base_output, "prod.env")

    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        logger.info(f"✅ Environment injected from {env_path}")
    elif os.getenv("APP_ENV") == "production":
        # Hard fail if secrets aren't there in Prod
        msg = "❌ CRITICAL: prod.env not found in /tmp/assets!"
        notify_telegram(msg)
        logger.error(msg)
        sys.exit(1)
    else:
        load_dotenv()
        logger.info("🏠 Running in LOCAL mode with standard .env")

# --- EXECUTE BOOTSTRAP ---
bootstrap_engine()

# --- IMPORTS (After Bootstrap) ---
from langgraph.graph import StateGraph, END
from langgraph_checkpoint_aws import DynamoDBSaver 
from langgraph.checkpoint.base import BaseCheckpointSaver
from utils.schema import flowstate
from utils.sheets import get_worksheet
from nodes.script_gen import script_generation
from nodes.audio_gen import audio_generation
from nodes.image_gen import image_generation
from nodes.video_assembly import video_stitching_slideshow
from nodes.final_upload import video_upload_node
from config import (AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
                    DYNAMO_TABLE_NAME, SHEET_NAME)

# --- SELECTIVE CHECKPOINTER ---
class SelectiveCheckpointer(BaseCheckpointSaver):
    def __init__(self, real_checkpointer: DynamoDBSaver):
        super().__init__()
        self.real_checkpointer = real_checkpointer

    async def aput(self, config, checkpoint, metadata, new_versions):
        step = metadata.get("step", -1)
        # Checkpoint only after major nodes
        if step in {0, 1, 2, 3, 4}:
            logger.info(f"💾 Checkpointing step {step}...")
            return await self.real_checkpointer.aput(config, checkpoint, metadata, new_versions)
        return config

    async def aput_writes(self, config, writes, task_id): return None
    async def aget_tuple(self, config): return await self.real_checkpointer.aget_tuple(config)
    async def alist(self, config, **kwargs):
        async for item in self.real_checkpointer.alist(config, **kwargs): yield item

# --- WORKFLOW SETUP ---
def build_workflow(checkpointer):
    workflow = StateGraph(flowstate)
    workflow.add_node("script_gen", script_generation)
    workflow.add_node("audio_gen", audio_generation)
    workflow.add_node("image_gen", image_generation)
    workflow.add_node("video_assembly", video_stitching_slideshow)
    workflow.add_node("final_upload", video_upload_node)

    workflow.set_entry_point("script_gen")
    workflow.add_edge("script_gen", "audio_gen")
    workflow.add_edge("audio_gen", "image_gen")
    workflow.add_edge("image_gen", "video_assembly")
    workflow.add_edge("video_assembly", "final_upload")
    workflow.add_edge("final_upload", END)
    return workflow.compile(checkpointer=checkpointer)

# --- MAIN WORKER ---
async def run_worker():
    topic = os.getenv("VIDEO_TOPIC")
    row_idx = os.getenv("ROW_INDEX")

    if not topic or not row_idx:
        logger.error("❌ Worker started without variables.")
        notify_telegram("⚠️ Worker started with missing ENV variables.")
        sys.exit(1)

    # 1. MARK AS RUNNING & NOTIFY START
    update_sheet_status(row_idx, "RUNNING")
    notify_telegram(f"🚀 <b>Zeteon Pipeline Initiated</b>\nRow: {row_idx}\nTopic: {topic}")

    try:
        # 2. DYNAMO DB SETUP
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
            region_name=AWS_REGION
        )
        base_saver = DynamoDBSaver(table_name=DYNAMO_TABLE_NAME, ttl_seconds=86400)
        base_saver.repo.dynamodb_client = session.client('dynamodb')
        checkpointer = SelectiveCheckpointer(base_saver)

        # 3. CONFIGURE RUN
        config = {"configurable": {"thread_id": f"thread_row_{row_idx}"}}

        initial_state: flowstate = {
        "row_index": int(row_idx),
        "video_topic": topic,
        "s3_folder_prefix": f"row_{row_idx}",
        
        "s3_script_en_url": "",
        "s3_voiceover_en_url": "",
        "s3_alignment_en_url": "",
        "s3_caption_en_url": "",
        "s3_image_urls": [],

        "s3_en_video_link": "",

        "yt_en_link": "",
        "ig_en_link": "",
        
        "isenscriptgenerated": False,
        "isenvoiceovergenerated": False,
        "isimagesgenerated": False,
        "isenvideogenerated": False,
        "isenvideouploaded": False,

        "error_message": None
    }

        app_workflow = build_workflow(checkpointer)
        
        # 4. EXECUTE & RESUME LOGIC
        existing_state = await app_workflow.aget_state(config)
        if existing_state.values:
            logger.info(f"🔄 Resuming from step: {existing_state.metadata.get('step')}")
            final_state = await app_workflow.ainvoke(None, config)
        else:
            final_state = await app_workflow.ainvoke(initial_state, config)
        
        # 5. FINAL SUCCESS CHECK
        if final_state.get("isenvideouploaded"):
            # Extract links from final state
            yt_link = final_state.get("yt_en_link", "N/A")
            ig_link = final_state.get("ig_en_link", "N/A")
            s3_link = final_state.get("s3_en_video_link", "N/A")

            update_sheet_status(row_idx, "SUCCESS")
            
            # Formulate the "Empire" update message
            success_msg = (
                f"🎬 <b>Zeteon Pipeline Success!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>Row:</b> {row_idx}\n"
                f"<b>Topic:</b> {topic}\n\n"
                f"📺 <a href='{yt_link}'>YouTube Link</a>\n"
                f"📸 <a href='{ig_link}'>Instagram Link</a>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ <i>Pipeline complete. All nodes finished.</i>"
            )
            notify_telegram(success_msg)
        else:
            update_sheet_status(row_idx, "FAILED")
            notify_telegram(f"⚠️ <b>Worker Finished</b>\nRow {row_idx} ended without upload.")

    except Exception as e:
        error_msg = f"💥 <b>Pipeline Crash</b>\nRow: {row_idx}\nError: {str(e)[:200]}"
        logger.error(traceback.format_exc())
        update_sheet_status(row_idx, "FAILED")
        notify_telegram(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except Exception as fatal_e:
        # Catch errors that happen even before run_worker starts properly
        logger.critical(f"Fatal Startup Error: {fatal_e}")
        notify_telegram(f"🚨 <b>Fatal Container Crash</b>\n{str(fatal_e)}")
        sys.exit(1)
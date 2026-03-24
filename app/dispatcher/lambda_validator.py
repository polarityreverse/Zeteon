import asyncio
import logging
import sys
from config_lambda import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.sheets_lambda import get_worksheet
from utils.ecs_handler import launch_fargate_task # You'll build this for the worker
from telegram import Bot

# --- LOGGING CONFIGURATION (AWS READY) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonPipeline")

async def validate_and_launch(event):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Data passed from the Step Function
    row_id = event.get("row_id")
    topic = event.get("topic")

    try:
        ws = get_worksheet()
        # Ensure row_id is an int and get the status from Column 3 (C)
        current_status = ws.cell(int(row_id), 3).value

        if not current_status:
            logger.info(f"🚫 Launch aborted for row {row_id} (User Cancelled).")
            # Reset to PENDING so it can be picked up another day if needed
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"✅ **Confirmation:** Row {row_id} has been reset to PENDING. No resources used."
            )
            return {"status": "ABORTED"}

        # If it's still TRIGGERED, we go for launch!
        logger.info(f"🚀 Status is {current_status}. Launching Fargate task...")
        ws.update_cell(int(row_id), 3, "PROCESSING")
        
        # Trigger the heavy-duty Zeteon Worker
        task_arn = launch_fargate_task(row_id, topic)

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🎬 **Worker Active!**\nTopic: {topic}\nFargate Task: `{task_arn.split('/')[-1]}`"
        )
        
        return {"status": "LAUNCHED", "task_arn": task_arn}

    except Exception as e:
        logger.error(f"Validator Error: {e}")
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ **Validator Failure:** {str(e)}")
        return {"status": "ERROR", "message": str(e)}

def handler(event, context):
    return asyncio.run(validate_and_launch(event))
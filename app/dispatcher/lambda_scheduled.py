import asyncio
import logging
import json
import sys
from config_lambda import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.idea_picker import get_video_idea
from utils.step_launcher import start_wait_sequence
from utils.sheets_lambda import get_worksheet
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- LOGGING CONFIGURATION (AWS READY) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonPipeline")
async def run_scheduler():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        # 1. Fetch the next PENDING idea
        # idea contains {'row_id': 5, 'topic': 'AI Revolution', 'status': 'PENDING'}
        idea = await get_video_idea()
        
        if not idea:
            logger.info("No PENDING ideas found. Sleeping.")
            return {"statusCode": 200, "body": "No tasks."}

        row_id = idea['row_num']
        topic = idea['topic']

        # 2. THE LOCK: Immediately update sheet to TRIGGERED
        # This prevents any other process from touching this row
        ws = get_worksheet()
        # Assuming Status is Column 3 (C)
        ws.update_cell(row_id, 3, "TRIGGERED")
        logger.info(f"Row {row_id} locked and set to TRIGGERED.")

        # 3. Create the Overide Button
        # callback_data is what lambda_webhook.py will parse
        keyboard = [
            [InlineKeyboardButton("🛑 STOP GENERATION", callback_data=f"stop_{row_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = (
            f"📅 **Scheduled Run Initiated**\n\n"
            f"**Topic:** {topic}\n"
            f"**Row:** {row_id}\n\n"
            f"⏳ You have 60 seconds to cancel before the Fargate worker starts."
        )

        # 4. Notify Telegram
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        # 5. Launch the Step Function (The 60s Timer)
        # We pass row_id and topic so the Validator knows what to check
        sf_response = start_wait_sequence(row_id, topic)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Sequence started",
                "row_id": row_id,
                "execution_arn": sf_response.get('executionArn')
            })
        }

    except Exception as e:
        logger.error(f"Scheduled Lambda Failed: {e}")
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🚨 **Dispatcher Error:** {str(e)}")
        return {"statusCode": 500, "body": str(e)}

def handler(event, context):
    return asyncio.run(run_scheduler())
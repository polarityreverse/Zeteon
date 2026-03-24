import asyncio
import json
import sys
import logging
from config_lambda import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
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

async def handle_manual_request(event):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # 1. Parse the Incoming Webhook Body
    try:
        body = json.loads(event.get("body", "{}"))
        # We only care about actual messages (not button clicks, those go to webhook.py)
        if "message" not in body or "text" not in body["message"]:
            return {"statusCode": 200}

        message_text = body["message"]["text"]
        chat_id = body["message"]["chat"]["id"]

        # 2. Security Check: Only you can trigger this
        if str(chat_id) != str(TELEGRAM_CHAT_ID):
            logger.warning(f"Unauthorized access attempt from {chat_id}")
            return {"statusCode": 403}

        # 3. Parse Command (e.g., "/run Space Exploration")
        if message_text.startswith("/run "):
            topic = message_text.replace("/run ", "").strip()
        else:
            return {"statusCode": 200}

        # 4. Record the Manual Request in Sheets
        ws = get_worksheet()
        # Append a new row: [Topic, ID (Timestamp), Status]
        # Using a timestamp as a temporary row_id if your sheet lacks auto-increment
        import time
        row_id = int(time.time()) 
        ws.append_row([topic, row_id, "TRIGGERED"])
        
        # Determine the exact row number for the STOP button
        # (append_row adds to the end, find the last row)
        actual_row_num = len(ws.col_values(1)) 

        # 5. Feedback & STOP Button
        keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_{actual_row_num}")]]
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🏗️ **Manual Request Received**\n**Topic:** {topic}\n**Row:** {actual_row_num}\n⏳ Launching in 60s...",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

        # 6. Kick off the Wait Sequence
        start_wait_sequence(actual_row_num, topic)

        return {"statusCode": 200, "body": "Manual trigger successful"}

    except Exception as e:
        logger.error(f"Manual Lambda Error: {e}")
        return {"statusCode": 500, "body": str(e)}

def handler(event, context):
    return asyncio.run(handle_manual_request(event))
import asyncio
import json
import sys
import logging
from datetime import datetime
from config_lambda import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.step_launcher import start_wait_sequence
from utils.sheets_lambda import get_worksheet
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonMasterController")

async def handle_webhook(event):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        body = json.loads(event.get("body", "{}"))
        
        # --- ROUTE 1: CALLBACK QUERIES (STOP BUTTON) ---
        if "callback_query" in body:
            callback_query = body["callback_query"]
            callback_data = callback_query.get("data", "")
            chat_id = callback_query["message"]["chat"]["id"]
            message_id = callback_query["message"]["message_id"]

            if str(chat_id) != str(TELEGRAM_CHAT_ID):
                return {"statusCode": 403}

            if callback_data.startswith("stop_"):
                row_idx = callback_data.split("_")[1]
                logger.info(f"🛑 STOP signal for row: {row_idx}")

                # Update Sheet to CANCELLED
                ws = get_worksheet()
                ws.update_cell(int(row_idx), 3, "")

                # Visual feedback in Telegram
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🛑 **SEQUENCE ABORTED**\nRow {row_idx} marked as **CANCELLED**.\nLaunch sequence has been aborted.",
                    parse_mode='Markdown'
                )
                await bot.answer_callback_query(callback_query["id"], text="Sequence Stopped.")
            return {"statusCode": 200}

        # --- ROUTE 2: TEXT MESSAGES (/run) ---
        message = body.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if not text or str(chat_id) != str(TELEGRAM_CHAT_ID):
            return {"statusCode": 200}

        if text.startswith("/run "):
            topic = text.replace("/run ", "").strip()
            logger.info(f"🚀 Manual trigger for topic: {topic}")

            # 1. Record in Sheets
            ws = get_worksheet()
            today = datetime.now().strftime("%Y-%m-%d")
            ws.append_row([today, topic, "TRIGGERED"])
            
            # 2. Get the row number (last row)
            actual_row_num = len(ws.col_values(1))

            # 3. Send Telegram message with STOP button
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_{actual_row_num}")]]
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"🏗️ **Manual Request Received**\n**Topic:** {topic}\n**Row:** {actual_row_num}\n⏳ Launching in 60s...",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

            # 4. Kick off the Wait Sequence (Step Function)
            # Note: Ensure this utility does NOT block the Lambda (no time.sleep)
            start_wait_sequence(actual_row_num, topic)
            
            return {"statusCode": 200}

        return {"statusCode": 200}

    except Exception as e:
        logger.error(f"Master Controller Error: {e}")
        return {"statusCode": 500}

def handler(event, context):
    return asyncio.run(handle_webhook(event))
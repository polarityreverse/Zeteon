import sys
import logging
import random
import json
import datetime
import time
import os
import httpx 
from typing import List

from utils.sheets import get_worksheet
from utils.youtube_view_count import get_performance_context
from utils.s3_helper import load_prompt_from_s3
from config import IDEA_GENERATION_API_URL, SHEET_NAME, OUTPUT_DIR

# --- LOGGING CONFIGURATION (AWS READY) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonPipeline")


async def generate_3_ideas(uploaded_ideas: List) -> List:
    """LLM call to generate next viral science topics."""
    performance_data = get_performance_context()
    
    idea_prompt_filename = f"idea_generation_prompt.txt"
    idea_prompt_key = f"prompts/{idea_prompt_filename}"
    idea_gen_sys_instruction_filename = f"idea_system_instructions.txt"
    idea_gen_sys_instruction_key = f"prompts/{idea_gen_sys_instruction_filename}"
    local_idea_prompt_path = f"{OUTPUT_DIR}/{idea_prompt_filename}"
    local_idea_sys_ins_path = f"{OUTPUT_DIR}/{idea_gen_sys_instruction_filename}"

    IDEA_PROMPT = await load_prompt_from_s3(idea_prompt_key, local_idea_prompt_path)
    IDEA_SYSTEM_INSTRUCTIONS = await load_prompt_from_s3(idea_gen_sys_instruction_key, local_idea_sys_ins_path)
    
    prompt = (
    f"{IDEA_PROMPT} \n"
    f"### PERFORMANCE CONTEXT: {performance_data} \n"
    f"### AVOID THESE TOPICS: {uploaded_ideas}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": IDEA_SYSTEM_INSTRUCTIONS}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {"ideas": {"type": "array", "items": {"type": "string"}}},
                "required": ["ideas"]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                resp = await client.post(IDEA_GENERATION_API_URL, json=payload, timeout=60)
                resp_json = resp.json()
                raw_text = resp_json['candidates'][0]['content']['parts'][0]['text']
                
                # CLEANING: Remove markdown code blocks if present
                clean_json = raw_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                ideas = data.get('ideas', [])
                if ideas and isinstance(ideas, list):
                    return ideas

                logger.warning(f"Attempt {attempt+1}: JSON parsed but 'ideas' key missing or empty.")
            except Exception as e:
                logger.warning(f"Topic generation attempt {attempt+1} failed: {e}")
                time.sleep(2)

            finally:
                # Clean up the local temp file
                files_to_clean = [local_idea_sys_ins_path, local_idea_prompt_path]
                for temp_file in files_to_clean:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)    
    return []

# --- TOPIC MANAGEMENT ---
async def get_video_idea():
    """Fetches a topic for the video, ensure atomic locking and maintains consistency in Google sheet in case of parallel runs..."""
    
    try:
        worksheet = get_worksheet(SHEET_NAME)
        all_records = worksheet.get_all_values()
        if not all_records: 
            logger.warning("Your Google Sheet is empty. Please check that you have correct sheet name setup.")
            return None

        headers = [h.strip().lower() for h in all_records[0]]
        idx_map = {header: i for i, header in enumerate(headers)}
        idx_trigger = idx_map.get('overall status')
        idx_topic = idx_map.get('video topic')

        if idx_trigger is None or idx_topic is None:
            logger.error("❌ Required columns 'Overall Status' or 'Video Topic' not found!")
            return None

        # Identifying all truly pending video topics from sheet
        failed_pool = []
        pending_pool = []
        uploaded_topics = []
        data = all_records[1:]
        for i, row in enumerate(data):
            sheet_row = i + 2 
            
            # Check if row needs processing
            status = row[idx_trigger].strip().upper() if len(row) > idx_trigger else ""
            idea_topic = row[idx_topic] if len(row) > idx_topic else ""
            
            if not idea_topic: continue

            if status == 'FAILED':
                failed_pool.append((sheet_row, idea_topic))
            elif not status or status not in ['SUCCESS']:  #['TRIGGERED', 'SUCCESS', 'FAILED']:
                pending_pool.append((sheet_row, idea_topic))
            else:
                uploaded_topics.append(idea_topic)

        random.shuffle(pending_pool)
        final_pool = failed_pool + pending_pool

        # If no topics exist, generate new ones
        if not final_pool:
            logger.info("Empty topic queue. Generating 3 new Video topics...")
            try:
                new_topics = await generate_3_ideas(uploaded_topics)
            except Exception as gen_err:
                logger.error(f"❌ Failed to generate topics via LLM: {gen_err}")
                return None # Stop here if generation fails
            
            today = datetime.date.today().strftime("%Y-%m-%d")
            # We append 3, but we 'lock' the first one immediately in the sheet
            rows_to_add = []
            for i, topic in enumerate(new_topics):
                lock_val = 'TRIGGERED' if i == 0 else ''
                # Format: [Video Date, Video Topic, Overall Status, IG EN Status,....more columns on right]
                rows_to_add.append([today, topic, lock_val])
            
            worksheet.append_rows(rows_to_add)
            new_row_num = len(all_records) + 1
            logger.info(f"✅ Generated 3 topics and locked: {new_topics[0]} (Row {new_row_num})")
            return {'row_num': new_row_num, 'topic': new_topics[0]}
        
        for row_num, topic in final_pool:
            # Re-verify cell status to ensure another container didn't grab it 0.5s ago
            # This is the 'Double-Check Lock' pattern
            current_status = worksheet.cell(row_num, idx_trigger + 1).value
            if not current_status or current_status.strip().upper() not in ['SUCCESS']:#['TRIGGERED', 'SUCCESS']:
                try:
                    worksheet.update_cell(row_num, idx_trigger + 1, 'TRIGGERED')
                    logger.info(f"🎯 Successfully claimed topic: {topic} (Row {row_num})")
                    return {'row_num': row_num, 'topic': topic}
                except Exception as e:
                    logger.warning(f"Could not claim topic from row {row_num}, likely grabbed by another instance: {e}")
                    continue        
        
        # If we exhausted the pool and everyone else grabbed the rows, recurse once
        logger.info("All pending rows were claimed by parallel runs. Generating fresh ideas.")
        return await get_video_idea()

    except Exception as e:
        logger.error(f"Critical Error in get_video_idea: {str(e)}")
        return None
    
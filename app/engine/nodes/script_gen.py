import logging
import json
import re
import requests
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict
from json_repair import repair_json

from utils.schema import flowstate
from utils.s3_helper import check_s3_exists, upload_file_to_s3, load_prompt_from_s3
from config import (
    CLAUDE_API_KEY, SCRIPT_IMAGE_PROMPT_MODEL,
    CLAUDE_SCRIPT_IMAGE_PROMPT_URL, AWS_S3_BUCKET, OUTPUT_DIR
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
#  Claude API Wrapper (with retries + extended timeout)
# -------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=12),
    reraise=True
)
def call_claude_api(payload: Dict, headers: Dict) -> Dict:
    """
    Claude API call with retry logic.
    Timeout increased to 120s to prevent 499 client disconnects.
    """
    response = requests.post(
        CLAUDE_SCRIPT_IMAGE_PROMPT_URL,
        headers=headers,
        json=payload,
        timeout=120
    )
    if response.status_code == 401:
        # Check if the key being used is actually what we think it is
        key_snippet = headers.get("x-api-key", "MISSING")[:8]
        logger.error(f"❌ CLAUDE AUTH FAILURE: Key starting with {key_snippet} was rejected.")
        response.raise_for_status()

    response.raise_for_status()
    return response.json()

# -------------------------------------------------------------------
#  Script Generation Node
# -------------------------------------------------------------------
async def script_generation(state: flowstate) -> flowstate:
    """Node 1: Script generation with robust validation and logging."""

    row_idx = state.get("row_index")
    picked_topic = state.get("video_topic")
    s3_folder_prefix = state.get("s3_folder_prefix")

    # ---------------------------------------------------------------
    # 1. CACHE CHECK
    # ---------------------------------------------------------------
    filename = f"script_en.json"
    s3_key = f"scripts/{s3_folder_prefix}/{filename}"
    s3_url = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_key}"

    if await check_s3_exists (s3_key):
        logger.info(f"📦 S3 Cache Hit: Skipping script generation, existing script located at {s3_key}")
        state["s3_script_en_url"] = s3_url
        state["isenscriptgenerated"] = True
        return state
        
    script_prompt_filename = f"script_generation_prompt.txt"
    sys_instruction_filename = f"script_system_instructions.txt"
    local_prompt_path = f"{OUTPUT_DIR}/{script_prompt_filename}"
    local_sys_ins_path = f"{OUTPUT_DIR}/{sys_instruction_filename}"
    prompt_key = f"prompts/{script_prompt_filename}"
    system_instruction_key = f"prompts/{sys_instruction_filename}"

    SCRIPT_GENERATION_PROMPT = await load_prompt_from_s3(prompt_key, local_prompt_path)
    SCRIPT_GENERATION_SYSTEM_INSTRUCTIONS = await load_prompt_from_s3(system_instruction_key, local_sys_ins_path)

    logger.info(f"🧠 Starting script generation for Row {row_idx} | Topic: {picked_topic}")
    # ---------------------------------------------------------------
    # 2. PREPARE CLAUDE PAYLOAD
    # ---------------------------------------------------------------
    payload = {
        "model": SCRIPT_IMAGE_PROMPT_MODEL,
        "max_tokens": 4000,
        "system": SCRIPT_GENERATION_SYSTEM_INSTRUCTIONS,
        "messages": [
            {
                "role": "user",
                "content": (
                            f"{SCRIPT_GENERATION_PROMPT}\n\n"
                            f"### TOPIC:\n{picked_topic}"
                )
            }
        ]
    }

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # ---------------------------------------------------------------
    # 3. CALL CLAUDE
    # ---------------------------------------------------------------
    response_json = call_claude_api(payload, headers)
    script_text = response_json["content"][0]["text"]

    # ---------------------------------------------------------------
    # 4. EXTRACT JSON BLOCK
    # ---------------------------------------------------------------
    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", script_text)
    if not json_match:
        raise ValueError("Claude returned no JSON block.")

    raw_json = json_match.group(1)
    fixed_json = repair_json(raw_json)
    generated_script = json.loads(fixed_json)

    # ---------------------------------------------------------------
    # 5. SCHEMA VALIDATION
    # ---------------------------------------------------------------
    required_keys = ["Metadata", "scenes"]
    missing = [k for k in required_keys if k not in generated_script]

    if missing:
        raise KeyError(f"Missing required keys: {missing}")

    # ---------------------------------------------------------------
    # 6. SAVE TO S3 AND UPDATE STATE
    # ---------------------------------------------------------------
    script_json_str = json.dumps(generated_script, indent = 4)

    local_temp_path = f"{OUTPUT_DIR}/{filename}"
    with open(local_temp_path, "w", encoding="utf-8") as f:
        f.write(script_json_str)

    try:
        await upload_file_to_s3(local_temp_path, s3_key)
        state["s3_script_en_url"] = s3_url
        state["isenscriptgenerated"] = True
        logger.info(f"📤 Script genetared and uploaded to S3 at {s3_key}")
    finally:
        # Clean up the local temp file
        files_to_clean = [local_temp_path, local_sys_ins_path, local_prompt_path]
        for temp_file in files_to_clean:
            if os.path.exists(temp_file):
                os.remove(temp_file)


    return state
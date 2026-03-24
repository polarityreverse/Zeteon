import os
import base64
import requests
import json
import random
import logging

from utils.s3_helper import upload_file_to_s3, check_s3_exists, download_file_from_s3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import (
    ELEVENLABS_API_KEY, AUDIO_GEN_MODEL, ELEVENLABS_VOICE_GENERATION_API_URL, 
    OUTPUT_DIR, VOICE_IDS, AWS_S3_BUCKET
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(requests.exceptions.HTTPError),
    reraise=True
)
def call_elevenlabs_api(url: str, payload: dict, headers: dict):
    response = requests.post(url, json=payload, headers=headers, timeout=90)
    if response.status_code == 429:
        logger.warning("🕒 ElevenLabs Rate Limit hit. Retrying...")
    response.raise_for_status()
    return response.json()

async def audio_generation(state: dict) -> dict:
    """Node 2: Voiceover generation with S3 Cache check ..."""

    row_id = state.get('row_index')
    s3_folder_prefix = state.get("s3_folder_prefix")

    # 1. Validation: Ensure Script exists (via S3 URL)-------
    if not state.get("isenscriptgenerated") and not state.get("s3_script_en_url"):
        logger.error(f"❌ Pipeline Error: No script URL found for Row {row_id}")
        raise ValueError("Missing s3_script_en_url. Previous node failed or state is corrupt.")
    
    vo_filename = f"voiceover_en.mp3"
    align_filename = f"alignment_en.json"

    s3_vo_key = f"voiceovers/{s3_folder_prefix}/{vo_filename}"
    s3_align_key = f"voiceover_alignment/{s3_folder_prefix}/{align_filename}"

    s3_vo_uri = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_vo_key}"
    s3_align_uri = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_align_key}"

    local_folder = OUTPUT_DIR #f"/tmp" Will use temp folder in ECS
    os.makedirs(local_folder, exist_ok=True)
    local_vo_path = os.path.join(local_folder, vo_filename)
    local_align_path = os.path.join(local_folder, align_filename)

    # 2. S3 CACHE CHECK -----------
    if await check_s3_exists(s3_vo_key) and await check_s3_exists(s3_align_key):
        logger.info(f"📦 Cache Hit: Validating and downloading audio assets from S3 for Row {row_id}")
        
        try:
            # Download to verify
            await download_file_from_s3(s3_vo_key, local_vo_path)
            await download_file_from_s3(s3_align_key, local_align_path)
            
            # Check for 0-byte files
            if os.path.getsize(local_vo_path) == 0 or os.path.getsize(local_align_path) == 0:
                raise ValueError("Downloaded audio asset files are empty (0 bytes)")

            # Verify JSON integrity (since we have it locally anyway)
            with open(local_align_path, 'r', encoding='utf-8') as f:
                json.load(f) 
            
            # If we reach here, cache is VALID
            state["s3_voiceover_en_url"] = s3_vo_uri
            state["s3_alignment_en_url"] = s3_align_uri
            state["isenvoiceovergenerated"] = True
            return state

        except Exception as e:
            logger.warning(f"⚠️ Cache Corrupted ({str(e)}). Forcing re-generation...")
            # Clean up the "poison" files so generator can start fresh
            if os.path.exists(local_vo_path): os.remove(local_vo_path)
            if os.path.exists(local_align_path): os.remove(local_align_path)


    # 3. GENERATION
    logger.info(f"🎙️ Generating audio assets now for Row {row_id}...")
    
    s3_script_url = state.get("s3_script_en_url")
    filename = s3_script_url.split("/")[-1]
    local_script_path = os.path.join(local_folder, filename)
    s3_script_key = s3_script_url.split(".amazonaws.com")[-1].lstrip("/")
    
    try:
        await download_file_from_s3(s3_script_key, local_script_path)

        with open(local_script_path, 'r') as f:
            script_data = json.load(f)

        scenes = script_data['scenes']
        full_vo_text = " ".join([scene['Voiceover_English'].strip() for scene in scenes])
        VOICE_ID = random.choice(VOICE_IDS)

        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "text": full_vo_text,
            "model_id": AUDIO_GEN_MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.0, "use_speaker_boost": True}
        }

        vo_url = f"{ELEVENLABS_VOICE_GENERATION_API_URL}/{VOICE_ID}/with-timestamps"
        data = call_elevenlabs_api(vo_url, payload, headers)
        
        # Save and Upload
        with open(local_vo_path, 'wb') as f:
            f.write(base64.b64decode(data['audio_base64']))
        with open(local_align_path, 'w') as f:
            json.dump(data['alignment'], f)

        await upload_file_to_s3(local_vo_path, s3_vo_key)
        await upload_file_to_s3(local_align_path, s3_align_key)

        state["s3_voiceover_en_url"] = s3_vo_uri
        state["s3_alignment_en_url"] = s3_align_uri
        state["isenvoiceovergenerated"] = True
        logger.info(f"✅ Voiceover synced to S3 for Row {row_id}")

    except Exception as e:
        logger.error(f"❌ Voiceover Generation Failed: {e}")
        # Re-raising ensures LangGraph stops here!
        raise 
    finally:
        if os.path.exists(local_script_path):
            os.remove(local_script_path)
    
    return state
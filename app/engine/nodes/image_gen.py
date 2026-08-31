import asyncio
import aiohttp
import random
import base64
import os
import logging
import json
from typing import Optional

from utils.s3_helper import copy_s3_object, download_file_from_s3, check_s3_exists, upload_bytes_to_s3
from config import AWS_S3_BUCKET, GEMINI_API_KEY_1, GEMINI_API_KEY_2, NANO_BANANA_MODEL, NANO_BANANA_IMAGE_GENERATION_API_URL, OUTPUT_DIR

# Set up production logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def generate_single_image_async(
    http_session: aiohttp.ClientSession, 
    prompt: str, 
    s3_image_key: str, 
    retries_per_url: int = 3
) -> Optional[str]:
    payload = {
        "model": NANO_BANANA_MODEL,
        "input": [{"type": "text", "text": prompt}],
        "generation_config": {
            "image_config": {
                "aspect_ratio": "9:16"
            }
        }
    }
    
    keys_to_try = [GEMINI_API_KEY_1, GEMINI_API_KEY_2]

    for key_idx, api_key in enumerate(keys_to_try):
        key_label = f"Key {key_idx + 1}"

        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        for attempt in range(retries_per_url):
            try:
                async with http_session.post(NANO_BANANA_IMAGE_GENERATION_API_URL, headers=headers, json=payload, timeout=90) as response:
                    if response.status == 200:
                        resp_data = await response.json()
                        image_b64 = None

                        # 1. Primary Extraction: /v1beta/interactions format (model_output -> content -> image)
                        steps = resp_data.get("steps", [])
                        for step in steps:
                            if step.get("type") == "model_output":
                                contents = step.get("content", [])
                                for item in contents:
                                    if item.get("type") == "image" and "data" in item:
                                        image_b64 = item["data"]
                                        break
                            if image_b64:
                                break

                        # 2. Secondary Fallback (inspects all content objects regardless of step structure)
                        if not image_b64:
                            for step in steps:
                                contents = step.get("content", [])
                                if isinstance(contents, list):
                                    for item in contents:
                                        if isinstance(item, dict) and item.get("mime_type", "").startswith("image/") and "data" in item:
                                            image_b64 = item["data"]
                                            break
                                if image_b64:
                                    break

                        if image_b64:
                            image_bytes = base64.b64decode(image_b64)
                            return await upload_bytes_to_s3(image_bytes, s3_image_key)
                        
                        logger.error(f"⚠️ {key_label} returned 200 but image data was missing from response payload.")
                    
                    elif response.status == 429:
                        wait_time = (2 ** attempt) * 8 + (random.uniform(0, 2))
                        logger.warning(f"🕒 {key_label} Rate Limited. Retrying in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                    
                    elif response.status == 400:
                        logger.error(f"⚠️ Safety/Prompt Filter Triggered on {key_label}. Skipping.")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"⚠️ {key_label} API Error {response.status}: {error_text}")
            except Exception as e:
                logger.error(f"❌ {key_label} Async Request Failed: {str(e)}")
                await asyncio.sleep(5)
        
        if key_idx == 0:
            logger.error(f"🚨 {key_label} exhausted. Switching to API KEY 2...")

    return None


async def image_generation(state: dict) -> dict:
    """Node 3: Async Image generation with S3 Cache check and robust fallbacks."""

    row_id = state.get('row_index')
    s3_folder_prefix = state.get("s3_folder_prefix")
    s3_script_url = state.get("s3_script_en_url")

    if not s3_script_url:    
        raise ValueError(f"❌ Image Gen Failed: No script URL for Row {row_id}")

    # Download script file from S3
    filename = s3_script_url.split("/")[-1]
    local_script_path = os.path.join(OUTPUT_DIR, filename)
    s3_script_key = s3_script_url.split(".amazonaws.com")[-1].lstrip("/")

    await download_file_from_s3(s3_script_key, local_script_path)

    with open(local_script_path, 'r') as f:
        script_data = json.load(f)
 
    scenes = script_data.get('scenes', [])
    metadata = script_data.get("Metadata", {})
    anchor = metadata.get("Global_Environmental_Anchor", "Cinematic background")
    subject = metadata.get("Visual_Continuity_Subject", "")
    style_suffix = f", featuring {subject}, set in {anchor}, photorealistic, 8k, extreme detail, cinematic lighting"
    
    # Count total images needed
    total_images_needed = sum(2 if ("Image_Action_Prompt_A" in s and s.get("Image_Action_Prompt_B")) else 1 for s in scenes)
    logger.info(f"🎨 Starting {total_images_needed} Asynchronous Image Generations for Row {row_id}...")

    state["s3_image_urls"] = []
    semaphore = asyncio.Semaphore(2)

    async def throttled_gen(http_session, prompt, s3_image_key, suffix):
        async with semaphore:
            full_prompt = f"{prompt}{suffix}"
            result = await generate_single_image_async(http_session, full_prompt, s3_image_key)
            await asyncio.sleep(1.5) 
            return result

    async with aiohttp.ClientSession() as http_session:
        tasks = []
        task_dest_keys = []
        
        for i, scene in enumerate(scenes):
            prompts_to_process = []
            if "Image_Action_Prompt_A" in scene and scene.get("Image_Action_Prompt_B"):
                prompts_to_process = [
                    (scene["Image_Action_Prompt_A"], f"Scene_{i+1}_A.png"),
                    (scene["Image_Action_Prompt_B"], f"Scene_{i+1}_B.png")
                ]
            else:
                p = scene.get("Image_Action_Prompt") or scene.get("Video_Action_Prompt")
                prompts_to_process = [(p, f"Scene_{i+1}.png")]

            for prompt_text, filename in prompts_to_process:
                s3_image_key = f"images/{s3_folder_prefix}/{filename}"
                task_dest_keys.append(s3_image_key)

                if await check_s3_exists(s3_image_key):
                    logger.info(f"📦 S3 Cache Hit for Scene {i+1} at {s3_image_key}")
                    tasks.append(asyncio.sleep(0, result=f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_image_key}"))
                else:
                    task = asyncio.create_task(throttled_gen(http_session, prompt_text, s3_image_key, style_suffix))
                    tasks.append(task)

        s3_image_uris = await asyncio.gather(*tasks) if tasks else []
        
        final_image_uris_list = []
        last_image_uri = None

        # Fallback processing: Ensure no None elements reach state["s3_image_urls"]
        for i, uri in enumerate(s3_image_uris):
            current_dest_key = task_dest_keys[i]

            if uri:
                final_image_uris_list.append(uri)
                last_image_uri = uri
            else:
                # Search the entire batch for ANY valid URI if previous indices were None
                if last_image_uri is None:
                    valid_uris = [u for u in s3_image_uris if u]
                    if valid_uris:
                        last_image_uri = valid_uris[0]

                if last_image_uri:
                    source_key = last_image_uri.split(".amazonaws.com")[-1].lstrip("/")
                    logger.warning(f"🔄 Invoking Fallback: Copying {source_key} to {current_dest_key}")
                    fallback_uri = await copy_s3_object(source_key, current_dest_key)
                    final_image_uris_list.append(fallback_uri)
                else:
                    logger.critical(f"🚨 Complete batch failure for Row {row_id}: No valid image generated.")
                    final_image_uris_list.append(None)

        state["s3_image_urls"] = final_image_uris_list

    # Final validation checks
    state["isimagesgenerated"] = all(bool(url) for url in state["s3_image_urls"]) and len(state["s3_image_urls"]) == total_images_needed
    
    if state["isimagesgenerated"]:
        logger.info(f"✅ All {total_images_needed} Images generated for Row {row_id}.")
    else:
        logger.error(f"❌ Image generation unrecoverable. One or more images failed completely.")
    
    return state
import os
import json
import random
import time
import requests
import asyncio
import logging
from googleapiclient.http import MediaFileUpload
from google import genai
from google.genai import types
import boto3
from urllib.parse import urlparse

from utils.schema import flowstate
from utils.youtube_auth import get_youtube_client
from utils.sheets import get_worksheet
from utils.s3_helper import download_file_from_s3, check_s3_exists, load_prompt_from_s3
from config import (
    OUTPUT_DIR, INSTA_ACCESS_TOKEN, INSTA_ACCOUNT_ID, 
    GEMINI_API_KEY_2, VIDEO_METADATA_GENERATION_MODEL, SHEET_NAME
)

# Set up production logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- HELPER 1: Metadata Generator ---
async def get_llm_metadata(topic, max_retries=5):
    client = genai.Client(api_key=GEMINI_API_KEY_2)

    social_media_metadata_filename = f"social_media_metadata_prompt.txt"
    local_sc_metadata_prompt_path = f"{OUTPUT_DIR}/{social_media_metadata_filename}"
    social_media_metadata_key = f"prompts/{social_media_metadata_filename}"
    SOCIAL_MEDIA_METADATA_PROMPT = await load_prompt_from_s3(social_media_metadata_key, local_sc_metadata_prompt_path)

    prompt = (
                f"{SOCIAL_MEDIA_METADATA_PROMPT}\n\n"
                f"### TOPIC:\n{topic}"
    )

    for attempt in range(max_retries):
        try:
            # --- Gemini API call ---
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=VIDEO_METADATA_GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )

            text = response.text.strip()

            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "").strip()

            data = json.loads(text)

            # Cleanup
            files_to_clean = [local_sc_metadata_prompt_path]
            for temp_file in files_to_clean:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return data[0] if isinstance(data, list) else data

        except Exception as e:
            err = str(e)

            # --- Handle rate limits ---
            if "429" in err or "rate" in err.lower():
                wait = (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"⚠️ Rate limit hit. Retrying in {wait:.2f}s...")
                await asyncio.sleep(wait)
                continue

            logger.error(f"❌ Video Metadata generation Error: {e}")
            return None

    logger.error("❌ Max retries exceeded for metadata generation")
    return None

# --- HELPER 2: YouTube ---
def upload_to_youtube(video_path, metadata, row_idx):
    try:
        youtube = get_youtube_client()
        body = {
            'snippet': {
                'title': metadata['title'][:100], 
                'description': metadata['description'], 
                'tags': metadata.get('tags', []),
                'categoryId': '28' 
            },
            'status': {
                'privacyStatus': 'public', 
                'selfDeclaredMadeForKids': False
            }
        }
        media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
        
        response = youtube.videos().insert(
            part="snippet,status", 
            body=body, 
            media_body=media
        ).execute()
        
        video_id = response['id']
        time.sleep(3)
        youtube.commentThreads().insert(part="snippet", body={
            "snippet": {
                "videoId": video_id, 
                "topLevelComment": {"snippet": {"textOriginal": metadata['pinned_comment']}}
            }
        }).execute()
        
        return "SUCCESS", f"https://www.youtube.com/shorts/{video_id}"
    except Exception as e:
        logger.error(f"❌ YouTube Upload Error: {e}")
        return "FAILED", None

# --- HELPER 3: Instagram ---
def upload_to_insta(video_url, metadata):
    base_url = f"https://graph.facebook.com/v19.0/{INSTA_ACCOUNT_ID}"
    try:
        raw_hashtags = metadata.get('hashtags', [])
        formatted_hashtags = []
        for tag in raw_hashtags:
            clean_tag = tag.strip().replace("#", "")
            if clean_tag:
                formatted_hashtags.append(f"#{clean_tag}")
        
        hashtag_string = " ".join(formatted_hashtags)
        full_caption = f"{metadata['caption']}\n\n{hashtag_string}"

        res = requests.post(f"{base_url}/media", data={
            'video_url': video_url, 
            'caption': full_caption,
            'media_type': 'REELS', 
            'access_token': INSTA_ACCESS_TOKEN
        }).json()
        
        container_id = res.get('id')
        if not container_id: 
            logger.error(f"❌ Insta Container Error: {res}")
            return "FAILED", None

        for i in range(45):
            time.sleep(20)
            status_res = requests.get(f"https://graph.facebook.com/v19.0/{container_id}", 
                                      params={'fields': 'status_code', 'access_token': INSTA_ACCESS_TOKEN}).json()
            s_code = status_res.get('status_code')
            logger.info(f"⏳ Insta Upload attempt {i+1}: {s_code}")
            if s_code == 'FINISHED':
                pub = requests.post(f"{base_url}/media_publish", data={'creation_id': container_id, 'access_token': INSTA_ACCESS_TOKEN}).json()
                media_id = pub.get("id")
                if not media_id:
                    return "FAILED", None
                permalink_res = requests.get(f"https://graph.facebook.com/v19.0/{media_id}",
                                    params={
                                    "fields": "permalink",
                                    "access_token": INSTA_ACCESS_TOKEN
                                    }).json()
                permalink = permalink_res.get("permalink")
                if not permalink:
                    logger.error(f"❌ Could not fetch permalink: {permalink_res}")
                    return "FAILED", None

                return "SUCCESS", permalink
            
            if s_code == 'ERROR':
                return "FAILED", None
            
        logger.error("❌ Insta processing timed out after 45 attempts")
        return "FAILED", None

    except Exception as e: 
        logger.error(f"❌ Insta Upload Exception: {e}")
        return "ERROR", None

# --- MAIN EXECUTION NODE ---
async def video_upload_node(state: flowstate) -> flowstate:
    """Node 5: Final video upload. Picks video from S3 for YouTube and uses S3 URL for Insta."""

    row_idx = state['row_index']
    topic = state['video_topic']
    s3_video_uri = state["s3_en_video_link"]
    
    logger.info(f"🚀 Starting upload sequence on Zeteon for Row {row_idx}...")

    worksheet = get_worksheet(SHEET_NAME)
    
    existing_yt_link = worksheet.cell(row_idx, 5).value
    existing_insta_link = worksheet.cell(row_idx, 6).value

    # Validation: Ensure video is generated in last node and state is updated-------
    if not state.get("isenvideogenerated") and not state.get("s3_en_video_link"):
        logger.info(f"⚠️ Skipping Video Upload: Video generation flag false in state for Row {row_idx}")
        state["isenvideouploaded"] = False
        return state

    # 1. CACHE CHECK BEFORE UPLOADING -----
    is_yt_exist = existing_yt_link and "youtube.com" in existing_yt_link
    is_ig_exist = existing_insta_link and "instagram.com" in existing_insta_link
    if is_yt_exist and is_ig_exist:
        logger.info(f"⏭️ Skipping upload sequence for Row {row_idx}, fully published already")
        logger.info(f"🔗 Existing Youtube Link: {existing_yt_link}")
        logger.info(f"🔗 Existing Instagram Link: {existing_insta_link}")
        state["yt_en_link"] = existing_yt_link
        state["ig_en_link"] = existing_insta_link
        state["isenvideouploaded"] =  True
        return state

    # 2. METADATA GENERATION AND S3 VIDEO CACHE CHECK-----
    metadata = await get_llm_metadata(topic)
    if isinstance(metadata, list):
        metadata = metadata[0]
    youtube_meta = metadata.get("youtube", {})
    insta_meta = metadata.get("insta", {})

    worksheet.update_cell(row_idx, 7, json.dumps(youtube_meta, ensure_ascii=False))
    worksheet.update_cell(row_idx, 8, json.dumps(insta_meta, ensure_ascii=False))
    
    if not metadata:
        logger.error(f"❌ Metadata generation failed for Row {row_idx}. Aborting upload sequence...")
        state["yt_en_link"] = ""
        state["ig_en_link"] = ""
        state["isenvideouploaded"] = False
        return state

    filename = s3_video_uri.split("/")[-1]
    s3_key = s3_video_uri.split(".amazonaws.com")[-1].lstrip("/")
    local_video_path = os.path.join(OUTPUT_DIR, filename)
    if not await check_s3_exists(s3_key):
        logger.error(f"❌ Critical Error: Video not found in S3 at: {s3_key}. Aborting upload sequence...")
        state["yt_en_link"] = ""
        state["ig_en_link"] = ""
        state["isenvideouploaded"] = False
        return state
    
    logger.info(f"🎬 Downloading and validating video from S3 to local for uploads (Row {row_idx})...")
    # Download to verify
    await download_file_from_s3(s3_key, local_video_path)
    # Check for 0-byte files
    if os.path.getsize(local_video_path) == 0:
        logger.error(f"❌ Critical Error: Downloaded video file is empty (0 bytes). Aborting upload sequence ...")
        state["yt_en_link"] = ""
        state["ig_en_link"] = ""
        state["isenvideouploaded"] = False
        return state

    # 3. YOUTUBE UPLOAD (Requires local file download from S3)
    if existing_yt_link:
        logger.info(f"⏭️ Skipping YouTube upload, already published: {existing_yt_link}")
        state["yt_en_link"] = existing_yt_link
    else:
        logger.info(f"📤 Publishing Video to YouTube (Row {row_idx})...")
        status, yt_link = upload_to_youtube(local_video_path, metadata['youtube'], row_idx)
        if status == "SUCCESS" and yt_link:
            logger.info(f"✅ YouTube upload successful for Row {row_idx}: {yt_link}")
            worksheet.update_cell(row_idx, 5, yt_link)
            state["yt_en_link"] = yt_link
        else:
            logger.warning(f"⚠️ Youtube publish failed (Row {row_idx}")
            state["yt_en_link"] = ""
            raise Exception(f"💥 YouTube publish failed for Row {row_idx}")

    # 4. INSTAGRAM UPLOAD (Uses S3 asset URI)
    if existing_insta_link:
        logger.info(f"⏭️ Skipping Instagram, already published: {existing_insta_link}")
        state["ig_en_link"] = existing_insta_link
    else:
        logger.info(f"📤 Publishing Video to Instagram (Row {row_idx})...")

        try:
            # 1. Parse the Bucket and Key from the S3 URI
            # Example URI: https://zeteon-media.s3.amazonaws.com/videos/row_33/video_en.mp4
            parsed_url = urlparse(s3_video_uri)
            bucket_name = parsed_url.netloc.split('.')[0]
            # Remove the leading slash from the path to get the S3 Key
            key_name = parsed_url.path.lstrip('/')

            # 2. Generate the Presigned URL
            s3_client = boto3.client(
                's3',
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                config=boto3.session.Config(signature_version='s3v4') # Required for many regions
            )

            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key_name},
                ExpiresIn=3600 # 1 hour is plenty for Insta to download
            )
            
            logger.info(f"🔗 Presigned URL generated for Instagram download.")

            # 3. Use THIS URL for the Instagram upload call
            status, ig_link = upload_to_insta(presigned_url, metadata['insta'])
            
        except Exception as e:
            logger.error(f"❌ Failed to generate Presigned URL or Upload: {e}")
            status, ig_link = "FAILED", None
   
        if status == "SUCCESS" and ig_link:
            logger.info(f"✅ Insta upload successful for Row {row_idx}: {ig_link}")
            worksheet.update_cell(row_idx, 6, ig_link)
            state["ig_en_link"] = ig_link
        else:
            logger.warning(f"⚠️ Instagram publish failed (Row {row_idx}")
            state["ig_en_link"] = ""
            raise Exception(f"💥 Instagram publish failed for Row {row_idx}")
            
    if state["yt_en_link"] and state["ig_en_link"]:
        state["isenvideouploaded"] = True
        logger.info("🏁 Upload sequence finished — Zeteon video is live on YouTube and Instagram.")
        # 🧹 Cleanup local temp files
        files_to_clean = [local_video_path]
        for temp_file in files_to_clean:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    return state
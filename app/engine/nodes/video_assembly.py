import subprocess
import os
import json
import re
import random
import logging

from utils.sheets import get_worksheet
from utils.s3_helper import check_s3_exists, upload_file_to_s3, download_file_from_s3, list_s3_objects
from config import OUTPUT_DIR, AWS_S3_BUCKET

# Set up production logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def ass_ts(sec):
    """Timestamp helper for ASS Subtitles."""
    sec = max(0, sec)
    h, m, s = int(sec // 3600), int((sec % 3600) // 60), sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

async def generate_ass_karaoke(s3_folder_prefix, OUTPUT_DIR, alignment_data, topic_comment, pause_at_end, max_words=4):
    """Helper: Generates high-retention karaoke subtitles with CTA and S3 backup."""

    ass_file = f"subtitle_en.ass"
    s3_caption_key = f"captions/{s3_folder_prefix}/{ass_file}"
    ass_path = os.path.join(OUTPUT_DIR, ass_file)
    
    chars = alignment_data["characters"]
    starts = alignment_data["character_start_times_seconds"]
    ends = alignment_data["character_end_times_seconds"]

    words, cur_word, word_start = [], "", None
    for i, ch in enumerate(chars):
        if not word_start: word_start = starts[i]
        if ch.isspace() or i == len(chars) - 1:
            if cur_word.strip():
                clean = re.sub(r'[^a-zA-Z0-9,\.\!\?\']', '', cur_word.strip())
                words.append({"text": clean.upper(), "start": word_start, "end": ends[i]})
            cur_word, word_start = "", None
        else: 
            cur_word += ch

    ass_header = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginV",
        "Style: Default,Calibri,85,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,1,1,4,0,2,280",
        "Style: CTA,Calibri,105,&H0000FFFF,&H000000FF,&H00000000,&H00000000,1,0,1,4,0,2,960",
        "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"
    ]

    events, current_chunk = [], []
    def create_line(chunk):
        s_t, e_t = chunk[0]["start"], chunk[-1]["end"]
        line_text = "".join([f"{{\\k{int((w['end']-w['start'])*100)}}}{w['text']} " for w in chunk])
        return f"Dialogue: 0,{ass_ts(s_t)},{ass_ts(e_t)},Default,,0,0,0,,{line_text.strip()}"

    for word_obj in words:
        current_chunk.append(word_obj)
        if len(current_chunk) >= max_words or any(p in word_obj["text"] for p in ["!", ".", "?"]):
            events.append(create_line(current_chunk))
            current_chunk = []

    if current_chunk:
        events.append(create_line(current_chunk))

    final_vo_time = ends[-1]
    events.append(f"Dialogue: 0,{ass_ts(final_vo_time)},{ass_ts(final_vo_time + pause_at_end)},CTA,,0,0,0,,{topic_comment.upper()}")

    ass_content = "\n".join(ass_header + events)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    await upload_file_to_s3(ass_path, s3_caption_key)
    return ass_path

# MAIN NODE
async def video_stitching_slideshow(state):
    """Node 4: Stateless FFmpeg engine for video assembly retrievs all assets (Audio, Images, Music) from S3."""
    
    row_id = state.get("row_index")
    s3_folder_prefix = state.get("s3_folder_prefix")

    video_filename = f"video_en.mp4"
    s3_video_key = f"videos/{s3_folder_prefix}/{video_filename}"
    s3_video_uri = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_video_key}"
    
    local_video_path = os.path.join(OUTPUT_DIR, video_filename)
    
    # 1. Validation: Ensure images exists and video not already generated (via S3 URL)-------
    if not state.get("isimagesgenerated") and not state.get("s3_image_urls"):
        logger.error(f"❌ Video Assembly Failed: No image URLs found for Row {row_id}")
        raise ValueError(f"Missing s3_image_urls in state for row {row_id}")
    
    if await check_s3_exists(s3_video_key):
        logger.info(f"📦 S3 Cache Hit: Video for Row {row_id} already exists at {s3_video_key}")
        state["s3_en_video_link"] = s3_video_uri
        state["isenvideogenerated"] = True
        return state

    logger.info(f"🚀 Starting Video assembly sequence for Row {row_id}...")

    # 2. Downloading voiceover, images and alignment assets to local temp location----
    s3_script_url = state.get("s3_script_en_url")
    s3_script_key = s3_script_url.split(".amazonaws.com")[-1].lstrip("/")
    script_filename = s3_script_url.split("/")[-1]
    s3_voiceover_url = state.get("s3_voiceover_en_url")
    s3_voiceover_key = s3_voiceover_url.split(".amazonaws.com")[-1].lstrip("/")
    voiceover_filename = s3_voiceover_url.split("/")[-1]
    s3_alignment_url = state.get("s3_alignment_en_url")
    s3_alignment_key = s3_alignment_url.split(".amazonaws.com")[-1].lstrip("/")
    alignment_filename = s3_alignment_url.split("/")[-1]
    
    local_script_path = os.path.join(OUTPUT_DIR, script_filename)
    local_voiceover_path = os.path.join(OUTPUT_DIR, voiceover_filename)
    local_alignment_path = os.path.join(OUTPUT_DIR, alignment_filename)

    # --- Local existence checks ---
    if not os.path.exists(local_script_path):
        await download_file_from_s3(s3_script_key, local_script_path)

    if not os.path.exists(local_voiceover_path):
        await download_file_from_s3(s3_voiceover_key, local_voiceover_path)

    if not os.path.exists(local_alignment_path):
        await download_file_from_s3(s3_alignment_key, local_alignment_path)

    image_uris = state.get("s3_image_urls", [])
    local_image_paths = []
    try:
        for uri in image_uris:
            filename = uri.split("/")[-1]
            s3_key = uri.split(".amazonaws.com")[-1].lstrip("/")
            local_path = os.path.join(OUTPUT_DIR, filename)
            await download_file_from_s3 (s3_key, local_path)
            local_image_paths.append(local_path)
    except Exception as e:
        logger.error(f"❌ Critical Failure: Image retrieval failed: {e}")
        raise

    # 3. Dynamic Background Music Selection from S3----
    selected_music_local_path = None
    try:
        music_prefix = "background_music/"
        response = await list_s3_objects(music_prefix)
        
        music_files = [ key for key in response if key.lower().endswith('.mp3')]
        if music_files:
            random_music_key = random.choice(music_files)
            music_filename = os.path.basename(random_music_key)
            selected_music_local_path = os.path.join(OUTPUT_DIR, music_filename)
            
            logger.info(f"🎵 Downloading randomly selected background music for this video: {random_music_key}")
            await download_file_from_s3 (random_music_key, selected_music_local_path)
        else:
            logger.warning("⚠️ No background music found in S3 'background_music/' folder.")
    except Exception as e:
        logger.error(f"⚠️ Background music retrieval failed: {e}")


    # 4. FFMPEG assembly process----- 
    try:
        # Calculate Timing
        cmd_dur = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{local_voiceover_path}"'
        vo_duration = float(subprocess.check_output(cmd_dur, shell=True))
        pause_at_end = 1.5 
        total_target_dur = vo_duration + pause_at_end

        with open(local_script_path, 'r') as f:
            script_data = json.load(f)

        scenes = script_data.get("scenes", [])
        metadata = script_data.get("Metadata", {})
        topic_comment = metadata.get("Topic_Comment") or "LIKE & FOLLOW FOR MORE!"

        total_scene_script_dur = sum(float(s["Scene_Duration"]) for s in scenes)
        stretch_factor = vo_duration / total_scene_script_dur
        
        final_image_list = []
        calc_durs = []
        img_ptr = 0

        for i, scene in enumerate(scenes):
            scene_dur = float(scene["Scene_Duration"]) * stretch_factor
            if "Image_Action_Prompt_B" in scene and scene["Image_Action_Prompt_B"].strip():
                half = scene_dur / 2
                calc_durs.extend([half + 0.5, half + (0.5 if i < len(scenes)-1 else pause_at_end)])
                final_image_list.extend([local_image_paths[img_ptr], local_image_paths[img_ptr+1]])
                img_ptr += 2
            else:
                calc_durs.append(scene_dur + (0.5 if i < len(scenes)-1 else pause_at_end))
                final_image_list.append(local_image_paths[img_ptr])
                img_ptr += 1

        # FFmpeg Filter Construction
        v_filters = []
        for i in range(len(final_image_list)):
            v_filters.append(
                f"[{i}:v]scale=2160:-1,format=yuv420p,fps=30,"
                f"zoompan=z='min(zoom+0.0007,1.4)':d={int(calc_durs[i]*30)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920[v{i}];"
            )

        concat_filter, last_v, cur_offset = "", "v0", 0
        for i in range(1, len(final_image_list)):
            cur_offset += (calc_durs[i-1] - 0.5)
            concat_filter += f"[{last_v}][v{i}]xfade=transition=fade:duration=0.5:offset={cur_offset:.3f}[xf{i}];"
            last_v = f"xf{i}"

        vo_idx, bg_idx = len(final_image_list), len(final_image_list) + 1
        fade_start = total_target_dur - 1.0

        if selected_music_local_path:
            audio_filter = (
                f"[{vo_idx}:a]apad=pad_dur={pause_at_end},asplit=2[vo_p1][vo_p2];"
                f"[{bg_idx}:a]volume=0.05,aloop=loop=-1:size=2e+09,afade=t=out:st={fade_start}:d=1[bg_loop];"
                f"[bg_loop][vo_p1]sidechaincompress=threshold=0.05:ratio=12:attack=20:release=200[bg_duck];"
                f"[vo_p2][bg_duck]amix=inputs=2:duration=longest:weights=1 1[a_final]"
            )
        else:
            audio_filter = f"[{vo_idx}:a]apad=pad_dur={pause_at_end}[a_final]"
        
        with open(local_alignment_path, 'r') as f:
            alignment_data = json.load(f)

        ass_path = await generate_ass_karaoke(s3_folder_prefix, OUTPUT_DIR, alignment_data, topic_comment, pause_at_end)
        escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:").replace(" ", "\\ ")

        # Assemble Command
        cmd = ["ffmpeg", "-y"]
        for i, img in enumerate(final_image_list):
            cmd += ["-loop", "1", "-t", f"{calc_durs[i]:.3f}", "-i", img]
        cmd += ["-i", local_voiceover_path]
        if selected_music_local_path: cmd += ["-i", selected_music_local_path]

        full_filter = "".join(v_filters) + concat_filter + f"[{last_v}]ass=filename='{escaped_ass}'[v_final];" + audio_filter

        cmd += [
            "-filter_complex", full_filter,
            "-map", "[v_final]", "-map", "[a_final]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast",
            "-t", f"{total_target_dur:.3f}", local_video_path
        ]

        logger.info(f"🎬 Rendering Video for Row {row_id}...")
        subprocess.run(cmd, check=True, capture_output=True)
        
    
        # 5. Video upload to S3, local temp cleanup and state management
        await upload_file_to_s3 (local_video_path, s3_video_key)

        # Update Sheet with S3 Link
        sheet_name = os.getenv("SHEET_NAME", "Main")
        sheet = get_worksheet(sheet_name)
        sheet.update_cell(row_id, 4, s3_video_uri)

        state["s3_en_video_link"] = s3_video_uri
        state["isenvideogenerated"] = True
        
        # Ephemeral Cleanup for ECS
        files_to_clean = local_image_paths + [local_voiceover_path, local_script_path, local_alignment_path, ass_path, local_video_path]
        if selected_music_local_path: files_to_clean.append(selected_music_local_path)
        
        for temp_file in files_to_clean:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except Exception as e:
        logger.error(f"❌ Critical Failure while assembling video {str(e)}", exc_info=True)
        state["s3_en_video_link"] = ""
        state["isenvideogenerated"] = False
        raise
  
    return state
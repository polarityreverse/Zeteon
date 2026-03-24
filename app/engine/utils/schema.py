from typing import TypedDict, List, Optional

class flowstate(TypedDict):

    # Tracking
    row_index: int              # The Google Sheet row we are working on
    video_topic: str             # Video Topic
    s3_folder_prefix: str       # Pattern: row_{row_index}/{run_id}/
    
    # --- S3 Asset URIs ---
    s3_script_en_url: str
    s3_voiceover_en_url: str
    s3_alignment_en_url: str       
    s3_caption_en_url: str
    s3_image_urls: List[str]     

    # --- Final Video URIs (S3) ---
    s3_en_video_link: str

    # --- YouTube Links (Final Output) ---
    yt_en_link: str
    ig_en_link: str

    # Status Flags
    isenscriptgenerated: bool
    isenvoiceovergenerated: bool
    isimagesgenerated: bool
    isenvideogenerated: bool
    isenvideouploaded: bool

    error_message: Optional[str]


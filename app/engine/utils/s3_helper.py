import aioboto3
import botocore
import logging
import asyncio
from typing import List
from config import AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

logger = logging.getLogger(__name__)

# Session management for aioboto3
session = aioboto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

async def check_s3_exists(s3_key: str) -> bool:
    """Async Cache Check: Uses HEAD request to verify file existence."""
    async with session.client("s3") as s3:
        try:
            await s3.head_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
            logger.info(f"✨ Asset Cache Hit: {s3_key}")
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            raise

async def upload_file_to_s3(local_path: str, s3_key: str) -> str:
    """Async Upload: Transfers local file to S3."""
    async with session.client("s3") as s3:
        try:
            await s3.upload_file(local_path, AWS_S3_BUCKET, s3_key)
            s3_uri = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_key}"
            logger.info(f"📤 Asset Uploaded to S3: {s3_uri}")
            return s3_uri
        except Exception as e:
            logger.error(f"❌ Asset Upload Failed: {e}")
            raise

async def download_file_from_s3(s3_key: str, local_path: str):
    """Async Download: Retrieves S3 object to local disk."""
    async with session.client("s3") as s3:
        try:
            await s3.download_file(AWS_S3_BUCKET, s3_key, local_path)
            logger.info(f"📥 Asset downloaded from s3: {s3_key}")
        except Exception as e:
            logger.error(f"❌ Asset download failed: {e}")
            raise

async def upload_bytes_to_s3(image_bytes: bytes, s3_key: str, content_type: str = "image/png") -> str:
    """
    Async Bytes Upload: Uploads raw image bytes directly to S3.
    Use this to save API responses directly without writing to local disk first.
    """
    async with session.client("s3") as s3:
        try:
            await s3.put_object(
                Bucket=AWS_S3_BUCKET,
                Key=s3_key,
                Body=image_bytes,
                ContentType=content_type
            )
            s3_uri = f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{s3_key}"
            logger.info(f"⚡ Image uploaded to S3: {s3_uri}")
            return s3_uri
        except Exception as e:
            logger.error(f"❌ Image upload failed: {e}")
            raise

async def copy_s3_object(source_key: str, dest_key: str):
    """
    Native S3-to-S3 copy. 
    Useful for image generation fallbacks (e.g., using a default image).
    """
    async with session.client("s3") as s3:
        try:
            copy_source = {'Bucket': AWS_S3_BUCKET, 'Key': source_key}
            await s3.copy_object(
                CopySource=copy_source,
                Bucket=AWS_S3_BUCKET,
                Key=dest_key
            )
            logger.info(f"🔄 S3 native copy action perfromed for {source_key} -> {dest_key}")
            return f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{dest_key}"
        except Exception as e:
            logger.error(f"❌ S3 native copy action failed: {e}")
            raise

async def list_s3_objects(prefix: str) -> List[str]:
    """
    Async List: Retrieves all object keys in a specific S3 folder (prefix).
    Uses a paginator to handle folders with >1000 items.
    """
    keys = []
    async with session.client("s3") as s3:
        try:
            paginator = s3.get_paginator("list_objects_v2")
            async for result in paginator.paginate(Bucket=AWS_S3_BUCKET, Prefix=prefix):
                if "Contents" in result:
                    for obj in result["Contents"]:
                        keys.append(obj["Key"])
            
            logger.info(f"📂 Found {len(keys)} assets in S3 prefix: {prefix}")
            return keys
        except Exception as e:
            logger.error(f"❌ Failed to list S3 assets: {e}")
            return []


async def load_prompt_from_s3(s3_key: str, local_path: str) -> str:

    await download_file_from_s3(s3_key, local_path)
    with open(local_path, "r", encoding="utf-8") as f:
        return f.read()


async def main():
    result = await list_s3_objects("background_music/")
    print (result)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import aiohttp
import json

# Replace with your actual values for a quick test
API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
API_KEY = "AIzaSyB85F19lt67vPCgxPbG0h_tqGH9L7DntUg"
PROMPT = "A photorealistic majestic lion in a forest, 8k"

def truncate_long_strings(obj):
    """Recursively truncate long base64/signature strings for clean terminal printing."""
    if isinstance(obj, dict):
        return {k: truncate_long_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncate_long_strings(item) for item in obj]
    elif isinstance(obj, str) and len(obj) > 60:
        return obj[:30] + "... [TRUNCATED] ..." + obj[-10:]
    return obj

async def test_endpoint():
    payload = {
        "model": "gemini-3.1-flash-image",
        "input": [{"type": "text", "text": PROMPT}],
        "generation_config": {
            "image_config": {
                "aspect_ratio": "9:16"
            }
        }
    }

    headers = {
        "x-goog-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=headers, json=payload) as response:
            resp_json = await response.json()
            cleaned_json = truncate_long_strings(resp_json)
            
            print("\n--- CLEANED RESPONSE STRUCTURE ---")
            print(json.dumps(cleaned_json, indent=2))

if __name__ == "__main__":
    asyncio.run(test_endpoint())
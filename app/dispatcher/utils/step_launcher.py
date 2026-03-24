import boto3
import json
import logging
import time
import sys
from config_lambda import STEP_FUNCTION_ARN, AWS_REGION

# --- LOGGING CONFIGURATION (AWS READY) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonPipeline")

def start_wait_sequence(row_id: int, topic: str, mode: str = "auto"):
    """
    Triggers the AWS Step Function to start the 60s wait period.
    """
    client = boto3.client('stepfunctions', region_name=AWS_REGION)
    
    input_payload = {
        "row_id": row_id,
        "topic": topic,
        "mode": mode
    }
    
    try:
        response = client.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f"Run_{row_id}_{int(time.time())}", # Unique name for execution
            input=json.dumps(input_payload)
        )
        logger.info(f"✅ Step Function started: {response['executionArn']}")
        return response
    except Exception as e:
        logger.error(f"❌ Failed to start Step Function: {e}")
        raise
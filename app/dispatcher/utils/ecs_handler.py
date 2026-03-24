import boto3
import logging
import os
import sys
from config_lambda import AWS_REGION, ECS_CLUSTER, ECS_TASK_DEFINITION, ECS_SUBNET_ID, ECS_SECURITY_GROUP

# --- LOGGING CONFIGURATION (AWS READY) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ZeteonPipeline")

def launch_fargate_task(row_id: int, topic: str):
    """
    Spawns a Zeteon Worker in AWS Fargate to handle video generation.
    """
    client = boto3.client('ecs', region_name=AWS_REGION)

    try:
        response = client.run_task(
            cluster=ECS_CLUSTER,
            launchType='FARGATE',
            taskDefinition=ECS_TASK_DEFINITION,
            count=1,
            platformVersion='LATEST',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': [ECS_SUBNET_ID],
                    'securityGroups': [ECS_SECURITY_GROUP],
                    'assignPublicIp': 'ENABLED'  # Required if not in a NATed private subnet
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': 'zeteon-worker', # Must match the name in Task Definition
                        'environment': [
                            {'name': 'VIDEO_TOPIC', 'value': str(topic)},
                            {'name': 'ROW_INDEX', 'value': str(row_id)},
                            {'name': 'APP_ENV', 'value': 'production'}
                        ]
                    }
                ]
            }
        )

        if response['failures']:
            logger.error(f"❌ ECS Task Launch Failure: {response['failures']}")
            raise Exception(f"ECS Launch Failed: {response['failures']}")

        task_arn = response['tasks'][0]['taskArn']
        logger.info(f"🚀 Fargate task launched: {task_arn}")
        return task_arn

    except Exception as e:
        logger.error(f"❌ Error triggering ECS: {e}")
        raise
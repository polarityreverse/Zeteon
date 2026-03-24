# 1. Identity and Regional Context
locals {
  cluster_name   = "ZeteonCluster"
  family         = "zeteon-worker-task"
  container_name = "zeteon-worker"
  cpu            = "2048"
  memory         = "4096"

  # Link environment variables directly to data sources for a single source of truth
  container_environment_vars = {
    AWS_S3_BUCKET = data.aws_s3_bucket.media.id
    APP_ENV       = "production"
    AWS_REGION    = data.aws_region.current.name
  }
}

# 2. Data Source Lookups (Bridging to Data Layer)
data "aws_s3_bucket" "media" {
  bucket = "zeteon-media"
}

data "aws_dynamodb_table" "state_store" {
  name = "Zeteon_State_Store"
}

data "aws_ecr_repository" "engine" {
  name = "zeteon-engine"
}

data "aws_ecr_repository" "dispatcher" {
  name = "zeteon-dispatcher"
}

# Managed policy for ECS Agent to pull images and stream logs
data "aws_iam_policy" "ecs_execution" {
  name = "AmazonECSTaskExecutionRolePolicy"
}

# 3. IAM: Execution Role (Infrastructure Permissions)
module "iam_ecs_task_execution_role" {
  source = "../../modules/IAM/role"

  role_name       = "zeteon-ecs-task-execution-role"
  trusted_service = "ecs-tasks.amazonaws.com"
  policy_arns     = [data.aws_iam_policy.ecs_execution.arn]
}

# 4. IAM: Task Role (Application Permissions)
module "iam_ecs_task_s3_policy" {
  source = "../../modules/IAM/policies/s3"
  bucket_arns = [
    data.aws_s3_bucket.media.arn,
    "${data.aws_s3_bucket.media.arn}/*"
  ]
  s3_read_policy_name = "Zeteon_ECS_Task_S3_Policy"
  enable_s3_write     = true
}

module "iam_ecs_task_dynamodb_policy" {
  source                          = "../../modules/IAM/policies/dynamodb"
  dynamodb_read_write_policy_name = "Zeteon_ECS_Task_DynamoDB_Policy"
  table_arns                      = [data.aws_dynamodb_table.state_store.arn]
}

module "iam_ecs_task_role" {
  source = "../../modules/IAM/role"

  role_name       = "zeteon-ecs-task-role"
  trusted_service = "ecs-tasks.amazonaws.com"

  # Using distinct and compact to safeguard the list of policy ARNs
  policy_arns = [
    module.iam_ecs_task_s3_policy.s3_read_policy_arn,
    module.iam_ecs_task_s3_policy.s3_write_policy_arn,
    module.iam_ecs_task_dynamodb_policy.dynamodb_write_policy_arn
  ]
}

# 5. ECS Task Definition
module "worker_task_definition" {
  source = "../../modules/services/ecs/task_definition"

  family             = local.family
  container_name     = local.container_name
  cpu                = local.cpu
  memory             = local.memory
  execution_role_arn = module.iam_ecs_task_execution_role.role_arn
  task_role_arn      = module.iam_ecs_task_role.role_arn
  image_uri          = "${data.aws_ecr_repository.engine.repository_url}:latest"
  log_group_name     = "/ecs/${local.family}"
  aws_region         = data.aws_region.current.name

  container_environment_vars = local.container_environment_vars
}

# 6. ECS Cluster
resource "aws_ecs_cluster" "this" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
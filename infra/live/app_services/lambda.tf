# 1. Identity, Region, and Naming Context
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  # Define the Step Function name to break circular dependency
  sfn_name = "ZeteonWaitMachine"
  
  # Construct the predicted ARN using dynamic region and account ID
  predicted_sfn_arn = "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${local.sfn_name}"

  # Map function names to their specific entry points
  # Refined to use strings for cleaner mapping
  lambda_handler_map = {
    "Dispatcher-Scheduled" = "lambda_scheduled.handler"
    "Dispatcher-Validator" = "lambda_validator.handler"
    "Dispatcher-Webhook"   = "lambda_webhook.handler"
  }
}

# 2. Generate the IAM Policies
module "iam_lambda_cloudwatch_policy" {
  source = "../../modules/IAM/policies/cloudwatch"
  
  # Dynamic ARN construction for logging
  log_group_arn                     = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
  cloudwatch_logs_write_policy_name = "Zeteon_Lambda_CloudWatch_Logs_Policy"
}

module "iam_lambda_pass_role_policy" {
  source             = "../../modules/IAM/policies/iam_pass_role"
  iam_pass_role_arns = [
    module.iam_ecs_task_execution_role.role_arn, 
    module.iam_ecs_task_role.role_arn
  ]
  iam_pass_role_policy_name = "Zeteon_Lambda_Pass_Role_Policy"
}

module "iam_lambda_s3_policy" {
  source              = "../../modules/IAM/policies/s3"
  bucket_arns         = [data.aws_s3_bucket.media.arn]
  s3_read_policy_name = "Zeteon_Lambda_S3_Policy"
  enable_s3_write     = false
}

module "iam_lambda_step_function_policy" {
  source                    = "../../modules/IAM/policies/step_function"
  trigger_resource_arns     = [local.predicted_sfn_arn]
  step_function_policy_name = "Zeteon_Lambda_Step_Function_Policy"
}

module "iam_lambda_ecs_policy" {
  source                    = "../../modules/IAM/policies/ecs"
  ecs_tasks_arns            = ["${module.worker_task_definition.task_definition_arn}"]
  ecs_run_tasks_policy_name = "Zeteon_Lambda_ECS_Run_Task_Policy"
}

# 3. Create the Execution Role
module "iam_lambda_role" {
  source          = "../../modules/IAM/role"
  role_name       = "Zeteon_Lambda_Invoke_Role"
  trusted_service = "lambda.amazonaws.com"
  
  policy_arns = [
    module.iam_lambda_cloudwatch_policy.cloudwatch_logs_write_policy_arn,
    module.iam_lambda_pass_role_policy.iam_pass_role_policy_arn,
    module.iam_lambda_s3_policy.s3_read_policy_arn,
    module.iam_lambda_step_function_policy.step_function_policy_arn,
    module.iam_lambda_ecs_policy.ecs_run_tasks_policy_arn
  ]
}

# 4. Deploy the Lambda Functions
module "my_lambdas" {
  source   = "../../modules/services/lambda"
  for_each = toset(var.lambda_function_names)

  function_name = each.value
  iam_role_arn  = module.iam_lambda_role.role_arn
  image_uri     = "${data.aws_ecr_repository.dispatcher.repository_url}:latest"

  # Lookup handler from map, converting string to list for the Docker CMD
  image_command = [lookup(local.lambda_handler_map, each.value, "lambda_scheduled.handler")]

  environment_variables = {
    BOT_TOKEN          = var.BOT_TOKEN
    CHAT_ID            = var.CHAT_ID
    ECS_SECURITY_GROUP = var.ECS_SECURITY_GROUP
    ECS_SUBNET_ID      = var.ECS_SUBNET_ID
    GEMINI_API_KEY     = var.GEMINI_API_KEY
    STEP_FUNCTION_ARN  = local.predicted_sfn_arn
  }

  memory_size = 512
  timeout     = 60
}

# 5. Webhook-Specific Infrastructure
resource "aws_lambda_function_url" "webhook_url" {
  function_name      = module.my_lambdas["Dispatcher-Webhook"].lambda_function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
  }
}

resource "aws_lambda_permission" "allow_webhook_url" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = module.my_lambdas["Dispatcher-Webhook"].lambda_function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
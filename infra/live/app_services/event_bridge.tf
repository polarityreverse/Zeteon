# 1. Generate the invocation policies
module "iam_eventbridge_policy" {
  source = "../../modules/IAM/policies/lambda"
  
  lambda_invoke_policy_name = "Zeteon_EventBridge_Invoke_Lambda_Policy"
  
  # Dynamically link to the Scheduled Dispatcher created in lambdas.tf
  lambda_arns = [
    module.my_lambdas["Dispatcher-Scheduled"].lambda_function_arn
  ]
}

# 2. Create the IAM Role for EventBridge
module "iam_eventbridge_role" {
  source          = "../../modules/IAM/role"
  role_name       = "Zeteon_EventBridge_Invoke_Lambda"
  trusted_service = "events.amazonaws.com"
  
  policy_arns = [
    module.iam_eventbridge_policy.lambda_invoke_policy_arn
  ]
}

# 3. Define the Scheduling Rule (14:00 UTC Daily)
resource "aws_cloudwatch_event_rule" "zeteon_daily_trigger" {
  name                = "Zeteon-Daily-Trigger"
  description         = "Triggers the Zeteon Scheduled Dispatcher daily"
  schedule_expression = "cron(00 14 * * ? *)"
}

# 4. Set the Lambda Target for the EventBridge Rule at 14:00 UTC Daily
resource "aws_cloudwatch_event_target" "zeteon_daily_target" {
  rule      = aws_cloudwatch_event_rule.zeteon_daily_trigger.name
  target_id = "Dispatcher-Scheduled"
  
  # Use the module output instead of a hardcoded string
  arn       = module.my_lambdas["Dispatcher-Scheduled"].lambda_function_arn
  
  # Attaching the execution role
  role_arn  = module.iam_eventbridge_role.role_arn
}


# 5. Second EventBridge Rule (22:00 UTC)
resource "aws_cloudwatch_event_rule" "zeteon_daily_night_trigger" {
  name                = "Zeteon-Daily-Night-Trigger"
  description         = "Triggers the Zeteon Scheduled Dispatcher nightly at 22:00 UTC"
  schedule_expression = "cron(30 20 * * ? *)"
}

# Target for the second rule
resource "aws_cloudwatch_event_target" "zeteon_daily_night_target" {
  rule      = aws_cloudwatch_event_rule.zeteon_daily_night_trigger.name
  target_id = "Dispatcher-Scheduled"

  arn       = module.my_lambdas["Dispatcher-Scheduled"].lambda_function_arn
  role_arn  = module.iam_eventbridge_role.role_arn
}

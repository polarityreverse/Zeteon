# 1. IAM: Step Function Policy (Permissions to Invoke Lambda)
module "iam_step_function_policy" {
  source = "../../modules/IAM/policies/lambda"

  # Providing both base ARN and versioned ARN to ensure full invocation rights
  lambda_arns = [
    module.my_lambdas["Dispatcher-Validator"].lambda_function_arn,
    "${module.my_lambdas["Dispatcher-Validator"].lambda_function_arn}:*"
  ]
  
  lambda_invoke_policy_name = "Zeteon_Step_Function_Lambda_Invoke_Policy"
}

# 2. IAM: Step Function Execution Role
module "iam_step_function_role" {
  source          = "../../modules/IAM/role"
  role_name       = "Zeteon_Step_Function_Execution_Role"
  trusted_service = "states.amazonaws.com"
  
  # Attach the invocation policy created above
  policy_arns = [
    module.iam_step_function_policy.lambda_invoke_policy_arn
  ]
}

# 3. Step Function Deployment
module "dispatcher_step_function" {
  source = "../../modules/services/step_function"

  # Use the role ARN from the role module
  sfn_role_arn = module.iam_step_function_role.role_arn
  
  # Ensure the name aligns with the predicted ARN used in the Lambda environment variables
  state_machine_name   = "ZeteonWaitMachine"
  
  # Pass the specific validator Lambda ARN
  validator_lambda_arn = module.my_lambdas["Dispatcher-Validator"].lambda_function_arn
}
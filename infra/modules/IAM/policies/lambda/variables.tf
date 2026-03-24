variable "lambda_arns" {
  description = "List of Lambda function ARNs to grant permissions to"
  type        = list(string)
}

variable "lambda_invoke_policy_name" {
  description = "Unique name for the Lambda invoke policy"
  type        = string
}
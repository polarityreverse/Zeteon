variable "state_machine_name" {
  description = "Name of the Step Function state machine"
  type        = string  
}

variable "sfn_role_arn" {
  description = "ARN of the IAM role for Step Function execution"
  type        = string
}

variable "validator_lambda_arn" {
  description = "ARN of the Lambda function used for validation in the state machine"
  type        = string
}
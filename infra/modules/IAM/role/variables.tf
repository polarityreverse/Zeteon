# variables.tf (inside the module)
variable "role_name" {
  description = "The name of the IAM role"
  type        = string
}

variable "trusted_service" {
  description = "The AWS service that can assume this role (e.g., lambda.amazonaws.com)"
  type        = string
  default     = "lambda.amazonaws.com"
}

variable "policy_arns" {
  description = "List of IAM policy ARNs to attach to the role"
  type        = list(string)
  default     = []
}
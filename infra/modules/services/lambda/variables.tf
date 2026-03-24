variable "function_name" {
  description = "The name of the Lambda function"
  type        = string
}

variable "iam_role_arn" {
  description = "The ARN of the IAM role to use for the Lambda function"
  type        = string
}

variable "image_uri" {
  description = "The URI of the container image for the Lambda function"
  type        = string
}

variable "memory_size" {
  description = "The memory size for the Lambda function"
  type        = number
}

variable "timeout" {
  description = "The timeout for the Lambda function"
  type        = number
}

variable "environment_variables" {
  description = "The environment variables for the Lambda function"
  type        = map(string)
}

variable "tags" {
  description = "The tags for the Lambda function"
  type        = map(string)
  default = {}
}

variable "image_command" {
  description = "The command to run in the container image"
  type        = list(string)
  default     = [] 
}
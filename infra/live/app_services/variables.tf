variable "lambda_function_names" {
  description = "A list of unique names for the Dispatcher Lambda functions. These names are used as keys for handler mapping and resource addressing."
  type        = list(string)
  default     = [
    "Dispatcher-Scheduled",
    "Dispatcher-Validator",
    "Dispatcher-Webhook"
  ]

  validation {
    # Ensures names follow AWS Lambda naming conventions (no spaces, special chars except - and _)
    condition     = can([for s in var.lambda_function_names : regex("^[a-zA-Z0-9-_]+$", s)])
    error_message = "Lambda function names must be alphanumeric and can only contain hyphens (-) or underscores (_)."
  }
}


#Secret variables for Lambda environment

variable "BOT_TOKEN" {
  type      = string
  sensitive = true
}

variable "CHAT_ID" {
  type = string
}

variable "ECS_SECURITY_GROUP" {
  type = string
}

variable "ECS_SUBNET_ID" {
  type = string
}

variable "GEMINI_API_KEY" {
  type      = string
  sensitive = true
}

#Hey this CI workflow test number 2
variable "cloudwatch_logs_write_policy_name" {
  description = "Unique name for the CloudWatch Logs write-only policy"
  type        = string
}

variable "log_group_arn" {
  description = "ARN of the CloudWatch Logs group for log permissions"
  type        = string
}
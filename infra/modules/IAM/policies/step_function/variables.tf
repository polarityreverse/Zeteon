
variable "trigger_resource_arns" {
  description = "List of Step Function ARNs to grant permissions to"
  type        = list(string)
}

variable "step_function_policy_name" {
  description = "Unique name for the Step Function execution policy"
  type        = string
}

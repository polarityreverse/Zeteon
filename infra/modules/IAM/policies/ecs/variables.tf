variable "ecs_tasks_arns" {
  description = "List of ECS Run Task ARNs to grant permissions to"
  type        = list(string)
}

variable "ecs_run_tasks_policy_name" {
  description = "Unique name for the ECS Run Task execution policy"
  type        = string
}

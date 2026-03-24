variable "family" {
  description = "The family of the ECS task definition"
  type        = string
}

variable "cpu" {
  description = "The CPU resources to allocate to the task"
  type        = string
}

variable "memory" {
  description = "The memory resources to allocate to the task"
  type        = string
}

variable "execution_role_arn" {
  description = "The ARN of the execution role for the task"
  type        = string
}

variable "task_role_arn" {
  description = "The ARN of the task role for the task"
  type        = string
}

variable "container_name" {
  description = "The name of the container in the task definition"
  type        = string
}

variable "image_uri" {
  description = "The URI of the container image to use in the task definition"
  type        = string
}

variable "container_environment_vars" {
  description = "A map of environment variables for the container"
  type        = map(string)
}

variable "log_group_name" {
  description = "The name of the log group for the container"
  type        = string
}

variable "aws_region" {
  description = "The AWS region for the container"
  type        = string
}
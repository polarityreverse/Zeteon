# 1. Lambda Infrastructure Outputs
output "lambda_function_arns" {
  description = "A map of Lambda function names to their respective ARNs."
  # Transform the module map into a clean name -> arn map
  value = { for k, v in module.my_lambdas : k => v.lambda_function_arn }
}

output "webhook_endpoint" {
  description = "The public HTTPS URL for the Dispatcher-Webhook function."
  value       = aws_lambda_function_url.webhook_url.function_url
}

# 2. Orchestration Outputs
output "step_function_arn" {
  description = "The ARN of the Zeteon Wait Machine (Step Function)."
  value       = module.dispatcher_step_function.state_machine_arn
}

# 3. ECS Infrastructure Outputs
output "ecs_cluster_name" {
  description = "The name of the ECS Cluster where worker tasks are executed."
  value       = aws_ecs_cluster.this.name
}

output "worker_task_definition_arn" {
  description = "The latest ARN of the Worker Task Definition."
  value       = module.worker_task_definition.task_definition_arn
}
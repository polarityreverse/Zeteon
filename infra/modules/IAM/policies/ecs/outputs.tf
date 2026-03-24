output "ecs_run_tasks_policy_arn" {
  description = "ARN of the ECS Run Tasks IAM policy"
  value       = aws_iam_policy.ecs_run_tasks.arn
}

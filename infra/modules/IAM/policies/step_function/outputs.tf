output "step_function_policy_arn" {
  description = "ARN of the Step Function execution IAM policy"
  value       = aws_iam_policy.step_function.arn
}
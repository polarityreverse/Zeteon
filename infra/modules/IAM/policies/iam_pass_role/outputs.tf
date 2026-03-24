output "iam_pass_role_policy_arn" {
  description = "ARN of the IAM Pass Role policy"
  value       = aws_iam_policy.iam_pass_role.arn
}
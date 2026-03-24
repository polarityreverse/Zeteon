output "cloudwatch_logs_write_policy_arn" {
  description = "ARN of the CloudWatch Logs write IAM policy"
  value       = aws_iam_policy.cloudwatch_logs_write.arn
}

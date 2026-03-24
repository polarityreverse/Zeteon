output "dynamodb_write_policy_arn" {
  description = "ARN of the DynamoDB write-only IAM policy"
  value       = aws_iam_policy.dynamodb_read_write.arn
}
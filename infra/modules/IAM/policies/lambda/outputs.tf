output "lambda_invoke_policy_arn" {
  description = "ARN of the Lambda invoke IAM policy"
  value       = aws_iam_policy.lambda_invoke.arn
}
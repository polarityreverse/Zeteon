output "s3_write_policy_arn" {
  description = "ARN of the S3 write-only IAM policy"
  value = join("", aws_iam_policy.s3_write[*].arn)
}

output "s3_read_policy_arn" {
  description = "ARN of the S3 read-only IAM policy"
  value = aws_iam_policy.s3_read.arn
}

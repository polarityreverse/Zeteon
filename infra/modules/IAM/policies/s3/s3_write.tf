# s3_write.tf
data "aws_iam_policy_document" "s3_write" {
  statement {
    sid    = "AllowWriteObjects"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    # This automatically adds /* to every bucket ARN in the list
    resources = [for arn in var.bucket_arns : "${arn}/*"]
  }
}

resource "aws_iam_policy" "s3_write" {
  count = var.enable_s3_write ? 1 : 0
  name        = var.s3_write_policy_name
  description = "Write access to specific S3 buckets"
  policy      = data.aws_iam_policy_document.s3_write.json
}

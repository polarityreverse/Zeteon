# s3_readonly.tf
data "aws_iam_policy_document" "s3_read_only" {
  statement {
    sid    = "AllowListBuckets"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = var.bucket_arns
  }

  statement {
    sid    = "AllowReadObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectAttributes",
      "s3:GetObjectVersion"
    ]
    # This automatically adds /* to every bucket ARN in the list
    resources = [for arn in var.bucket_arns : "${arn}/*"]
  }
}

resource "aws_iam_policy" "s3_read" {
  name        = var.s3_read_policy_name
  description = "Read-only access to specific S3 buckets"
  policy      = data.aws_iam_policy_document.s3_read_only.json
}


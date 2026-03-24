# cloudwatch_logs_write.tf
data "aws_iam_policy_document" "cloudwatch_logs_write" {
  statement {
    sid    = "AllowCreateLogGroup"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup"
    ]

    resources = [
      "${var.log_group_arn}:*"
    ]
  }

  statement {
    sid    = "AllowWriteLogStreams"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${var.log_group_arn}:log-group:/aws/lambda/*:*"
    ]
  }
}

resource "aws_iam_policy" "cloudwatch_logs_write" {
  name        = var.cloudwatch_logs_write_policy_name
  description = "Minimal CloudWatch Logs write permissions"
  policy      = data.aws_iam_policy_document.cloudwatch_logs_write.json
}
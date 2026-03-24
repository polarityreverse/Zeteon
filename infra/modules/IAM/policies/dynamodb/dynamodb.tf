# dynamodb_read.tf
data "aws_iam_policy_document" "dynamodb_read_write" {
  statement {
    sid    = "AllowReadItems"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:BatchGetItem",
      "dynamodb:DescribeTable"
    ]

    # Automatically expands each table ARN
    resources = var.table_arns
  }
}

resource "aws_iam_policy" "dynamodb_read_write" {
  name        = var.dynamodb_read_write_policy_name
  description = "Read-Write access to specific DynamoDB tables"
  policy      = data.aws_iam_policy_document.dynamodb_read_write.json
}
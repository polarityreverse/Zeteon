#lambda_invoke.terraform

data "aws_iam_policy_document" "lambda_invoke_policy" {
  statement {
    sid    = "AllowInvokeLambda"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]

    resources = var.lambda_arns
  }
}

resource "aws_iam_policy" "lambda_invoke" {
    name        = var.lambda_invoke_policy_name
    description = "Policy to allow EventBridge to invoke Lambda functions"
    policy      = data.aws_iam_policy_document.lambda_invoke_policy.json
}
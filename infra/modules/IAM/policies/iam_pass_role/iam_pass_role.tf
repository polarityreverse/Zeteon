#iam_pass_role.tf
data "aws_iam_policy_document" "iam_pass_role" {
  statement {
    sid    = "AllowPassRole"
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]

    resources = var.iam_pass_role_arns
  }
}

resource "aws_iam_policy" "iam_pass_role" {
    name        = var.iam_pass_role_policy_name
    description = "Policy to allow passing IAM roles"
    policy      = data.aws_iam_policy_document.iam_pass_role.json
}
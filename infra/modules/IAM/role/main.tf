# 1. The Trust Policy (Who can use this role)
data "aws_iam_policy_document" "trust_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = [var.trusted_service]
    }
  }
}

# 2. The Role itself
resource "aws_iam_role" "this" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.trust_policy.json
  force_detach_policies = true # Prevents delete errors
}

# 3. Dynamic Attachments (The secret sauce)
resource "aws_iam_role_policy_attachment" "attachments" {
  count      = length(var.policy_arns)
  role       = aws_iam_role.this.name
  policy_arn = var.policy_arns[count.index]
}
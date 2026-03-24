variable "iam_pass_role_arns" {
  description = "List of IAM Role ARNs to grant permissions to"
  type        = list(string)
}

variable "iam_pass_role_policy_name" {
  description = "Unique name for the IAM Pass Role policy"
  type        = string
}
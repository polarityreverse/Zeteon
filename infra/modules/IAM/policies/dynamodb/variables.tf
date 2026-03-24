# variables.tf (inside the module)
variable "dynamodb_read_write_policy_name" {
  description = "Unique name for the DynamoDB read-only policy"
  type        = string
}

variable "table_arns" {
  type = list(string)
}
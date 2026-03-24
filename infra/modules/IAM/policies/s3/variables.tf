variable "bucket_arns" {
  description = "List of S3 Bucket ARNs to grant read access to"
  type        = list(string)
}

variable "s3_write_policy_name" {
  description = "Unique name for the S3 write-only policy"
  type        = string
  default = null
}

variable "s3_read_policy_name" {
  description = "Unique name for the S3 read-only policy"
  type        = string
}

variable "enable_s3_write" {
  description = "Flag to enable S3 write policy"
  type        = bool
}
resource "aws_s3_bucket" "media" {
  bucket = "zeteon-media"
  
  lifecycle {
    prevent_destroy = true
  }
}
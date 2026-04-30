terraform {

  backend "s3" {
    bucket = "terraform-state-file-store-for-polarity"
    key    = "zeteon/global/terraform.tfstate"
    region = "us-east-1"
    use_lockfile = true
  }


  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  required_version = ">= 1.2"
}
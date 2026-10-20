terraform {
  required_version = ">= 1.11" # S3 native state locking

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 2.0"
    }
  }

  # Bucket, key and region are passed with -backend-config at init.
  backend "s3" {
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.name
      ManagedBy = "terraform"
    }
  }
}

# Credentials come from MONGODB_ATLAS_CLIENT_ID / MONGODB_ATLAS_CLIENT_SECRET.
provider "mongodbatlas" {}

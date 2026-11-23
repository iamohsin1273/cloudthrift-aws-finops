provider "aws" {
  region = var.aws_region
  default_tags {
    tags = { Project = "CloudThrift", Environment = var.environment, ManagedBy = "Terraform" }
  }
}

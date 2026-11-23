variable "aws_region" {
  type    = string
  default = "ap-south-1"
}
variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.environment))
    error_message = "Environment must be a lowercase name of at most 16 characters."
  }
}
variable "inventory_regions" {
  type    = list(string)
  default = ["ap-south-1"]
  validation {
    condition     = length(var.inventory_regions) > 0 && alltrue([for r in var.inventory_regions : can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", r))])
    error_message = "Provide at least one valid AWS region."
  }
}
variable "schedule_expression" {
  type    = string
  default = "cron(0 6 * * ? *)"
}
variable "schedule_timezone" {
  type    = string
  default = "Asia/Kolkata"
}
variable "lambda_zip" {
  type    = string
  default = "../../../build/cloudthrift.zip"
}

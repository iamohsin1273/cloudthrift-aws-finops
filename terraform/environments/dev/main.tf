data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
locals {
  name = "cloudthrift-${var.environment}"
}
module "storage" {
  source      = "../../modules/report-storage"
  bucket_name = "${local.name}-reports-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}
module "collector" {
  source            = "../../modules/collector-lambda"
  name              = local.name
  bucket_arn        = module.storage.arn
  bucket_name       = module.storage.name
  inventory_regions = var.inventory_regions
  lambda_zip        = var.lambda_zip
}
module "schedule" {
  source              = "../../modules/scheduler"
  name                = local.name
  lambda_arn          = module.collector.arn
  schedule_expression = var.schedule_expression
  timezone            = var.schedule_timezone
}

variable "name" { type = string }
variable "bucket_arn" { type = string }
variable "bucket_name" { type = string }
variable "inventory_regions" { type = list(string) }
variable "lambda_zip" { type = string }
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "this" {
  name               = "${var.name}-collector"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}
data "aws_iam_policy_document" "permissions" {
  statement {
    actions   = ["ce:GetCostAndUsage", "ec2:DescribeInstances", "sts:GetCallerIdentity"]
    resources = ["*"]
  }
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${var.bucket_arn}/reports/*"]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }
}
resource "aws_iam_role_policy" "this" {
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.permissions.json
}
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.name}-collector"
  retention_in_days = 14
}
resource "aws_lambda_function" "this" {
  function_name                  = "${var.name}-collector"
  role                           = aws_iam_role.this.arn
  runtime                        = "python3.12"
  handler                        = "cloudthrift.handlers.collector.handler"
  filename                       = var.lambda_zip
  source_code_hash               = filebase64sha256(var.lambda_zip)
  timeout                        = 300
  memory_size                    = 256
  reserved_concurrent_executions = 1
  environment {
    variables = { REPORT_BUCKET = var.bucket_name, INVENTORY_REGIONS = join(",", var.inventory_regions) }
  }
  depends_on = [aws_iam_role_policy.this, aws_cloudwatch_log_group.this]
}
output "arn" { value = aws_lambda_function.this.arn }
output "name" { value = aws_lambda_function.this.function_name }

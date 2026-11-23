variable "name" { type = string }
variable "lambda_arn" { type = string }
variable "schedule_expression" { type = string }
variable "timezone" { type = string }
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "this" {
  name               = "${var.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}
resource "aws_iam_role_policy" "this" {
  role   = aws_iam_role.this.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "lambda:InvokeFunction", Resource = var.lambda_arn }] })
}
resource "aws_scheduler_schedule" "this" {
  name                         = "${var.name}-daily"
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.timezone
  flexible_time_window { mode = "OFF" }
  target {
    arn      = var.lambda_arn
    role_arn = aws_iam_role.this.arn
    input    = jsonencode({ scheduled_time = "<aws.scheduler.scheduled-time>" })
    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }
}
output "name" { value = aws_scheduler_schedule.this.name }

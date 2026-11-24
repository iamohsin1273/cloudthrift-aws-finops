# Offline configuration test: synthetic provider values, no AWS calls or state.
mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      arn        = "arn:aws:iam::123456789012:user/offline"
      user_id    = "offline"
    }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  # The mock does not evaluate IAM policy document data sources.
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

run "phase1_offline_plan" {
  command = plan

  assert {
    condition     = module.collector.name == "cloudthrift-dev-collector"
    error_message = "Unexpected collector function name."
  }
  assert {
    condition     = module.schedule.name == "cloudthrift-dev-daily"
    error_message = "Unexpected schedule name."
  }
}

mock_provider "aws" {}

run "bootstrap_offline_plan" {
  command = plan
  variables {
    bucket_name = "cloudthrift-example-state-123456789012"
  }
  assert {
    condition     = aws_s3_bucket.state.bucket == "cloudthrift-example-state-123456789012"
    error_message = "Unexpected state bucket name."
  }
}

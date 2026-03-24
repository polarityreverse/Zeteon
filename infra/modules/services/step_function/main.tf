resource "aws_sfn_state_machine" "dispatcher" {
  name     = var.state_machine_name
  role_arn = var.sfn_role_arn

  definition = templatefile(
    "${path.module}/statemachine.json.tmpl",
    {
      validator_lambda_arn = var.validator_lambda_arn
    }
  )
}
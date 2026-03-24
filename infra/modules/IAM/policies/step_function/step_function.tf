#step_function.tf
data "aws_iam_policy_document" "step_function" {
    statement {
            sid = "AllowLambdaToStartStepFunction"
            effect = "Allow"
            actions = [
                "states:StartExecution"
            ]
            resources = var.trigger_resource_arns
        }
}

resource "aws_iam_policy" "step_function" {
    name        = var.step_function_policy_name
    description = "Policy to allow Lambda to start Step Function executions"
    policy      = data.aws_iam_policy_document.step_function.json
}
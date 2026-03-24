#ecs_run_task.tf
data "aws_iam_policy_document" "ecs_run_task" {
  statement {
    sid    = "AllowRunTask"
    effect = "Allow"
    actions = [
      "ecs:RunTask"
    ]

    resources = var.ecs_tasks_arns
  }
}

resource "aws_iam_policy" "ecs_run_tasks" {
    name        = var.ecs_run_tasks_policy_name
    description = "Policy to allow running ECS tasks"
    policy      = data.aws_iam_policy_document.ecs_run_task.json
}
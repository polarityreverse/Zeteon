resource "aws_ecs_task_definition" "this" {
  family             = var.family
  network_mode       = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                = var.cpu
  memory             = var.memory
  execution_role_arn = var.execution_role_arn
  task_role_arn      = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.container_name
      image     = var.image_uri
      essential = true
      
      # Dynamic mapping from the map(string) to the ECS format
      environment = [
        for key, value in var.container_environment_vars : {
          name  = key
          value = value
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}
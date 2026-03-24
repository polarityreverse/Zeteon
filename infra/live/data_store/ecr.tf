# --- ECR Repositories ---

# 1. Engine Repository
resource "aws_ecr_repository" "engine" {
  name                 = "zeteon-engine"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true # Automatically scans for vulnerabilities
  }
}

# 2. Dispatcher Repository
resource "aws_ecr_repository" "dispatcher" {
  name                 = "zeteon-dispatcher"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- Lifecycle Policies (Cleanup) ---

# This policy ensures you only pay to store the 10 most recent images
resource "aws_ecr_lifecycle_policy" "engine_policy" {
  repository = aws_ecr_repository.engine.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "dispatcher_policy" {
  repository = aws_ecr_repository.dispatcher.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# --- Outputs for the App Layer ---

output "ecr_engine_url" {
  value = aws_ecr_repository.engine.repository_url
}

output "ecr_dispatcher_url" {
  value = aws_ecr_repository.dispatcher.repository_url
}
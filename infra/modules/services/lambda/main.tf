resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = var.iam_role_arn
  
  # Crucial: Tells Lambda we are using a container image, not a ZIP file
  package_type  = "Image"
  image_uri     = var.image_uri
  
  image_config {
    command = var.image_command
  }

  # General Configuration
  memory_size = var.memory_size
  timeout     = var.timeout

  # Environment Variables
  environment {
    variables = var.environment_variables
  }

  # Tags are essential for billing and management
  tags = var.tags
}
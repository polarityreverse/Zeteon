resource "aws_dynamodb_table" "state_store" {
  name         = "Zeteon_State_Store"
  billing_mode = "PAY_PER_REQUEST" # Matches "On-demand" in your image
  
  # Partition Key from your image: PK (String)
  hash_key  = "PK"
  
  # Sort Key from your image: SK (String)
  range_key = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # Point-in-time recovery is currently OFF in your image
  point_in_time_recovery {
    enabled = false
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Project = "Zeteon"
    Purpose = "LangGraph_Checkpointing_v1.0.2"
  }
}
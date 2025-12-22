# ECR Repository for Lambda Container Image

resource "aws_ecr_repository" "api" {
  name                 = "finapp-api-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  # Clean up old images
  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Name        = "finapp-api-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}

# Lifecycle policy to keep only last 5 images
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}


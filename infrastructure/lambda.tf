# Lambda Function for FastAPI Backend
# Uses container image from ECR with Mangum adapter

# IAM Role for Lambda
resource "aws_iam_role" "lambda" {
  name = "finapp-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }
}

# Basic Lambda execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access policy for Lambda (to reach RDS)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Policy for Cognito access
resource "aws_iam_role_policy" "lambda_cognito" {
  name = "finapp-lambda-cognito-${var.environment}"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:GetUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminInitiateAuth"
        ]
        Resource = aws_cognito_user_pool.finapp.arn
      }
    ]
  })
}

# Security Group for Lambda
resource "aws_security_group" "lambda" {
  name        = "finapp-lambda-sg-${var.environment}"
  description = "Security group for FinApp Lambda function"
  vpc_id      = data.aws_vpc.default.id

  # Allow all outbound traffic (to reach RDS, Cognito, etc.)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "finapp-lambda-sg-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}

# Allow Lambda to access RDS
resource "aws_security_group_rule" "rds_from_lambda" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.lambda.id
  description              = "PostgreSQL from Lambda"
}

# Lambda Function
resource "aws_lambda_function" "api" {
  function_name = "finapp-api-${var.environment}"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:latest"

  # Performance settings
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  # VPC Configuration (to reach RDS)
  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Environment variables
  environment {
    variables = {
      ENVIRONMENT             = var.environment
      DATABASE_URL            = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.finapp.endpoint}/${var.db_name}"
      COGNITO_REGION          = var.aws_region
      COGNITO_USER_POOL_ID    = aws_cognito_user_pool.finapp.id
      COGNITO_APP_CLIENT_ID   = aws_cognito_user_pool_client.finapp_client.id
      COGNITO_APP_CLIENT_SECRET = aws_cognito_user_pool_client.finapp_client.client_secret
      CORS_ORIGINS            = var.cors_origins
      LOG_LEVEL               = var.environment == "prod" ? "INFO" : "DEBUG"
    }
  }

  # Ensure ECR image exists before creating Lambda
  depends_on = [
    aws_ecr_repository.api,
    aws_db_instance.finapp
  ]

  tags = {
    Name        = "finapp-api-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }

  lifecycle {
    # Ignore image_uri changes - updated via CI/CD
    ignore_changes = [image_uri]
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}


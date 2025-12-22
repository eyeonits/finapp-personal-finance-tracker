# API Gateway HTTP API for Lambda Backend

# HTTP API (cheaper and simpler than REST API)
resource "aws_apigatewayv2_api" "api" {
  name          = "finapp-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "FinApp API Gateway"

  # CORS configuration
  cors_configuration {
    allow_origins     = var.cors_origins != "" ? split(",", var.cors_origins) : ["*"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    allow_headers     = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"]
    expose_headers    = ["Content-Type", "Authorization"]
    allow_credentials = true
    max_age           = 300
  }

  tags = {
    Name        = "finapp-api-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"

  # Timeout (must be between 50ms and 30s)
  timeout_milliseconds = 30000
}

# Default route (catch-all for all requests)
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Stage (auto-deploy enabled)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  # Access logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
    })
  }

  # Throttling (prevent runaway costs)
  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/finapp-${var.environment}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }
}

# Optional: Custom domain (uncomment and configure if needed)
# resource "aws_apigatewayv2_domain_name" "api" {
#   domain_name = "api.${var.domain_name}"
#
#   domain_name_configuration {
#     certificate_arn = aws_acm_certificate.api.arn
#     endpoint_type   = "REGIONAL"
#     security_policy = "TLS_1_2"
#   }
# }
#
# resource "aws_apigatewayv2_api_mapping" "api" {
#   api_id      = aws_apigatewayv2_api.api.id
#   domain_name = aws_apigatewayv2_domain_name.api.id
#   stage       = aws_apigatewayv2_stage.default.id
# }


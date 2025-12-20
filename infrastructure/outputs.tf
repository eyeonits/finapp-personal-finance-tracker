output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.finapp.id
}

output "user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.finapp.arn
}

output "user_pool_endpoint" {
  description = "Cognito User Pool endpoint"
  value       = aws_cognito_user_pool.finapp.endpoint
}

output "app_client_id" {
  description = "Cognito App Client ID"
  value       = aws_cognito_user_pool_client.finapp_client.id
}

output "app_client_secret" {
  description = "Cognito App Client Secret"
  value       = aws_cognito_user_pool_client.finapp_client.client_secret
  sensitive   = true
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL Outputs
# -----------------------------------------------------------------------------

output "db_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.finapp.endpoint
}

output "db_address" {
  description = "RDS instance address (hostname only)"
  value       = aws_db_instance.finapp.address
}

output "db_port" {
  description = "RDS instance port"
  value       = aws_db_instance.finapp.port
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.finapp.db_name
}

output "db_connection_string" {
  description = "PostgreSQL connection string (without password)"
  value       = "postgresql://${var.db_username}:<password>@${aws_db_instance.finapp.endpoint}/${aws_db_instance.finapp.db_name}"
  sensitive   = false
}


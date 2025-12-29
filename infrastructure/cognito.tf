# Cognito User Pool
resource "aws_cognito_user_pool" "finapp" {
  name = "finapp-${var.environment}"

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  # Email verification
  auto_verified_attributes = ["email"]
  
  # Username attributes
  username_attributes = ["email"]

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Verification message template
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "FinApp - Verify your email"
    email_message        = "Your verification code is {####}"
  }

  # User attribute schema
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # MFA configuration
  mfa_configuration = "OFF"

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "finapp_client" {
  name         = "finapp-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.finapp.id

  # Token validity
  access_token_validity  = 60  # 60 minutes
  id_token_validity      = 60  # 60 minutes
  refresh_token_validity = 30  # 30 days

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Auth flows
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read and write attributes
  read_attributes = [
    "email",
    "email_verified"
  ]

  write_attributes = [
    "email"
  ]

  # Generate secret
  generate_secret = true
}

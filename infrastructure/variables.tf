variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL Variables
# -----------------------------------------------------------------------------

variable "db_instance_class" {
  description = "RDS instance class (db.t4g.micro is free tier eligible)"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB (20GB is free tier eligible)"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Name of the database to create"
  type        = string
  default     = "finapp"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "finapp_admin"
}

variable "db_password" {
  description = "Master password for the database (use terraform.tfvars or environment variable)"
  type        = string
  sensitive   = true
}

variable "db_publicly_accessible" {
  description = "Whether the database should be publicly accessible (for local development)"
  type        = bool
  default     = false
}

variable "allowed_ip" {
  description = "Your IP address for direct database access (leave empty to disable)"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Lambda Variables
# -----------------------------------------------------------------------------

variable "lambda_memory_size" {
  description = "Lambda memory size in MB (128-10240)"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds (max 900 for API Gateway)"
  type        = number
  default     = 30
}

variable "cors_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "http://localhost:3000,http://localhost:5173"
}

# -----------------------------------------------------------------------------
# Custom Domain Variables (Optional)
# -----------------------------------------------------------------------------

variable "domain_name" {
  description = "Custom domain name (e.g., 'example.com'). Leave empty to use AWS default domains."
  type        = string
  default     = ""
}

variable "frontend_subdomain" {
  description = "Subdomain for frontend (e.g., 'app' for app.example.com). Leave empty to use root domain."
  type        = string
  default     = ""
}

variable "api_subdomain" {
  description = "Subdomain for API (e.g., 'api' for api.example.com)"
  type        = string
  default     = "api"
}

variable "use_route53" {
  description = "Whether to use Route 53 for DNS (set to false if using external DNS)"
  type        = bool
  default     = true
}


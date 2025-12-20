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


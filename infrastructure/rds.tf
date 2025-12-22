# RDS PostgreSQL Database for FinApp
# Uses db.t4g.micro for cost efficiency (~$12/month or free tier eligible)

# Get default VPC (simplest approach for personal project)
data "aws_vpc" "default" {
  default = true
}

# Get default subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "finapp" {
  name       = "finapp-${var.environment}"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name        = "finapp-db-subnet-group-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "finapp-rds-${var.environment}"
  description = "Security group for FinApp RDS PostgreSQL"
  vpc_id      = data.aws_vpc.default.id

  # PostgreSQL access from within VPC
  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  # Allow access from your IP (for local development)
  dynamic "ingress" {
    for_each = var.allowed_ip != "" ? [1] : []
    content {
      description = "PostgreSQL from allowed IP"
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = ["${var.allowed_ip}/32"]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "finapp-rds-sg-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "finapp" {
  identifier = "finapp-${var.environment}"

  # Engine
  engine         = "postgres"
  engine_version = "15"

  # Instance size (free tier eligible)
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = "gp2"

  # Database settings
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.finapp.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.db_publicly_accessible

  # Backups
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # Performance Insights (free for db.t4g.micro)
  performance_insights_enabled = false

  # Cost savings for dev
  multi_az            = false
  skip_final_snapshot = var.environment != "prod"
  deletion_protection = var.environment == "prod"

  # Apply changes immediately in dev
  apply_immediately = var.environment != "prod"

  # Enable encryption
  storage_encrypted = true

  # Auto minor version upgrades
  auto_minor_version_upgrade = true

  tags = {
    Name        = "finapp-postgres-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}


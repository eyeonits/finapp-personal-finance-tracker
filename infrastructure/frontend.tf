# S3 + CloudFront for React Frontend
# Provides HTTPS and global CDN caching

# S3 Bucket for static files
resource "aws_s3_bucket" "frontend" {
  bucket = "finapp-frontend-${var.environment}-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "finapp-frontend-${var.environment}"
    Environment = var.environment
    Application = "FinApp"
  }
}

# Random suffix for globally unique bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Block public access (CloudFront will access via OAC)
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy allowing CloudFront access
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "finapp-frontend-${var.environment}"
  description                       = "OAC for FinApp frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "FinApp Frontend - ${var.environment}"
  price_class         = "PriceClass_100"  # US, Canada, Europe only (cheapest)

  # S3 Origin
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "S3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  # Default cache behavior
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    # Cache policy for static assets
    cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6"  # CachingOptimized
    origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"  # CORS-S3Origin
  }

  # SPA routing - return index.html for 404s
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  # Geo restrictions (none)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL Certificate (use CloudFront default or custom)
  viewer_certificate {
    cloudfront_default_certificate = var.domain_name == "" ? true : false
    acm_certificate_arn            = var.domain_name != "" ? aws_acm_certificate.frontend[0].arn : null
    ssl_support_method             = var.domain_name != "" ? "sni-only" : null
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  # Custom domain aliases (if configured)
  aliases = var.domain_name != "" ? [var.frontend_subdomain != "" ? "${var.frontend_subdomain}.${var.domain_name}" : var.domain_name] : []

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }

  depends_on = [aws_acm_certificate_validation.frontend]
}

# ACM Certificate for custom domain (only if domain_name is set)
resource "aws_acm_certificate" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  # Must be in us-east-1 for CloudFront
  provider = aws.us_east_1

  domain_name       = var.frontend_subdomain != "" ? "${var.frontend_subdomain}.${var.domain_name}" : var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Environment = var.environment
    Application = "FinApp"
  }
}

# Certificate validation (requires Route 53 hosted zone)
resource "aws_acm_certificate_validation" "frontend" {
  count = var.domain_name != "" && var.use_route53 ? 1 : 0

  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for record in aws_route53_record.frontend_cert_validation : record.fqdn]
}

# Route 53 records for certificate validation
resource "aws_route53_record" "frontend_cert_validation" {
  for_each = var.domain_name != "" && var.use_route53 ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60

  allow_overwrite = true
}

# Route 53 A record for CloudFront (if using Route 53)
resource "aws_route53_record" "frontend" {
  count = var.domain_name != "" && var.use_route53 ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.frontend_subdomain != "" ? "${var.frontend_subdomain}.${var.domain_name}" : var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}

# Data source for Route 53 hosted zone
data "aws_route53_zone" "main" {
  count = var.domain_name != "" && var.use_route53 ? 1 : 0
  name  = var.domain_name
}



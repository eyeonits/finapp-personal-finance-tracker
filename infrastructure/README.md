# Infrastructure Setup

This directory contains Terraform configuration for AWS Cognito User Pool setup.

## Prerequisites

1. Install Terraform: https://www.terraform.io/downloads
2. Configure AWS credentials:
   ```bash
   aws configure
   ```

## Setup AWS Cognito User Pool

### Option 1: Using Terraform (Recommended)

1. Initialize Terraform:
   ```bash
   cd infrastructure
   terraform init
   ```

2. Review the plan:
   ```bash
   terraform plan
   ```

3. Apply the configuration:
   ```bash
   terraform apply
   ```

4. Save the outputs to your `.env` file:
   ```bash
   terraform output -raw user_pool_id
   terraform output -raw app_client_id
   terraform output -raw app_client_secret
   ```

### Option 2: Using AWS Console

1. Go to AWS Console → Cognito → User Pools
2. Click "Create user pool"
3. Configure the following settings:

**Step 1: Configure sign-in experience**
- Sign-in options: Email
- User name requirements: Allow users to sign in with email

**Step 2: Configure security requirements**
- Password policy:
  - Minimum length: 8 characters
  - Require uppercase letters: Yes
  - Require lowercase letters: Yes
  - Require numbers: Yes
  - Require special characters: No
- Multi-factor authentication: Optional

**Step 3: Configure sign-up experience**
- Self-registration: Enabled
- Required attributes: email
- Email verification: Required

**Step 4: Configure message delivery**
- Email provider: Send email with Cognito
- FROM email address: Use default

**Step 5: Integrate your app**
- User pool name: `finapp-dev` (or your environment)
- App client name: `finapp-client-dev`
- Client secret: Generate a client secret
- Authentication flows:
  - ALLOW_USER_PASSWORD_AUTH
  - ALLOW_REFRESH_TOKEN_AUTH
  - ALLOW_USER_SRP_AUTH

**Step 6: Review and create**
- Review all settings and create the user pool

4. After creation, note down:
   - User Pool ID
   - App Client ID
   - App Client Secret
   - AWS Region

5. Add these values to your `.env` file (see `.env.example`)

## Email Templates

The default Cognito email templates are used. To customize:

1. Go to User Pool → Messaging → Email templates
2. Customize verification and password reset emails

## Testing

Test the Cognito setup:

```bash
# Register a test user
aws cognito-idp sign-up \
  --client-id YOUR_APP_CLIENT_ID \
  --username test@example.com \
  --password TestPassword123

# Confirm the user (admin command for testing)
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id YOUR_USER_POOL_ID \
  --username test@example.com

# Login
aws cognito-idp initiate-auth \
  --client-id YOUR_APP_CLIENT_ID \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=test@example.com,PASSWORD=TestPassword123
```

## Cleanup

To destroy the Cognito resources:

```bash
terraform destroy
```

**Warning**: This will delete all users and cannot be undone!

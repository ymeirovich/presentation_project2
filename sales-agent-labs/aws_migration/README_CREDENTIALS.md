# AWS Credentials - DO NOT COMMIT

This directory should contain AWS credentials files **which are NOT committed to git**.

## Required Files (Not in Git)

1. **presgen_user_accessKeys.csv** - AWS access key ID and secret
   - Download from AWS Console → IAM → Users → Security Credentials
   - Contains: Access Key ID, Secret Access Key

2. **presgen_user_credentials.csv** - AWS console credentials
   - Download when creating IAM user
   - Contains: Username, Password, Console URL

## Setup Instructions

1. Create IAM user in AWS Console:
   ```bash
   aws iam create-user --user-name presgen_user
   aws iam attach-user-policy --user-name presgen_user --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
   aws iam create-access-key --user-name presgen_user > presgen_user_accessKeys.json
   ```

2. Configure AWS CLI:
   ```bash
   aws configure
   # Enter Access Key ID
   # Enter Secret Access Key
   # Enter region: us-east-1
   # Enter output format: json
   ```

3. Verify credentials:
   ```bash
   aws sts get-caller-identity
   ```

## Security Notes

- **NEVER** commit these CSV files to git
- Use AWS IAM roles for EC2 instances when possible
- Rotate access keys every 90 days
- Use least-privilege IAM policies for production
- Consider using AWS SSO for human access
- Store keys in password manager or AWS Secrets Manager

## For Production

Instead of access keys, use:
1. **EC2 Instance Roles** - Automatic credential rotation
2. **AWS Secrets Manager** - Centralized secret management
3. **AWS Systems Manager Parameter Store** - Configuration management

# Create cognito test user

```bash
aws cognito-idp admin-create-user \
  --user-pool-id eu-west-2_3zc6AZqGJ \
  --username lisa@example.com \
  --user-attributes Name=email,Value=lisa@example.com Name=email_verified,Value=true \
  --temporary-password TempPass123! \
  --region eu-west-2


aws cognito-idp admin-set-user-password \
  --user-pool-id eu-west-2_3zc6AZqGJ \
  --username lisa@example.com \
  --password <set something here> \
  --permanent
```

# Add user profile to test db

```bash
aws dynamodb put-item   --table-name "elbiefit-dev-table"   --item '{
    "PK": {"S": "USER#e6b2d244-8091-70df-730d-3a2a1b855f0f"},
    "SK": {"S": "PROFILE"},
    "display_name": {"S": "Lisa Test"},
    "email": {"S": "lisa@example.com"},
    "created_at": {"S": "2025-11-13T12:00:00Z"},
    "units": {"S": "metric"},
    "timezone": {"S": "Europe/London"}
  }'
```

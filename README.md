# ElbieFit 🏋️‍♀️

ElbieFit is a lightweight workout-logging web application built with FastAPI, HTMX, and AWS serverless infrastructure.

The goal is to provide a simple, fast, modern interface that allows users to log workouts, track progress, and manage profiles — backed by clean architecture and test-focused development.

# 🚀 Features

## Backend

- FastAPI application running on AWS Lambda via Mangum
- Cognito authentication (hosted UI → callback → session cookies)
- DynamoDB datastore using a repository layer
- Pydantic models

## Frontend

- HTMX/Jinja templates rendered server-side
- TBC: plain CSS or Tailwind #TODO

## Tooling & CI/CD

- Fully automated deployment pipeline using GitHub Actions
- CloudFormation yaml templates to deploy AWS resources
- OIDC trust for secure AWS deployments
- Pipeline runs tests and pushes code to test Lambda on every push to main

Bash scripts for:

- Deploying CloudFormation stacks
- Packaging Lambda code with uv
- Uploading build artifacts
- Updating Lambda code in place
- Unit tests via pytest, including coverage

# Deployment

- Clone the repo
- Run script to deploy AWS resources:
  `./scripts/deploy_stack.sh`
  This script deploys DynamoDB, Cognito, Lambda, API Gateway, and IAM roles
  Some resources will not complete on the first run, that's expected, we wire everything up in the next step.

- Create a .env file in the project root. Example contents:

```bash
REGION="eu-west-2"
PROJECT_NAME="elbiefit"
ACCOUNT_ID="123456789"
ENV="dev"

LOG_LEVEL="DEBUG"
DDB_TABLE_NAME="elbiefit-dev-table"

COGNITO_ISSUER="eu-west-2_abcdef"
COGNITO_AUDIENCE="slajfhasdjkghhjkafb"
COGNITO_DOMAIN="elbiefit-dev-123456789-auth"
COGNITO_REDIRECT_URI="https://abcdef123.execute-api.eu-west-2.amazonaws.com/auth/callback"
```

#### Cognito Issuer

Go to AWS Console → Cognito → User Pools
Click your user pool
On the Overview tab, look for Pool Id
It looks like: eu-west-2_kadjghgh
That entire string goes in COGNITO_ISSUER.

#### Cognito Audience

Inside your User Pool → App Integration
Scroll to App clients and analytics
Click the client you created (the one for ElbieFit)
You see Client ID
Example: 2xy4a0abc00cg0i5u7n17abcd5
Put that in COGNITO_AUDIENCE.

#### Cognito Domain

User Pool → App Integration
Under Domain, you will see configured domain:
elbiefit-dev-123456789-auth

#### Cognito Redirect URI

Go to API Gateway → your API → Stages → dev (or prod)

Base Invoke URL looks like: `https://12abcd34o.execute-api.eu-west-2.amazonaws.com`

Append your callback route: /auth/callback

Final string becomes: `https://12abcd34o.execute-api.eu-west-2.amazonaws.com/auth/callback`

- Run the deploy stack script again:
  `./scripts/deploy_stack.sh`

  This will pull in the environment variables and connect everything up.

## Code updates

Once the infrastructure is deployed and your .env file is filled in, you can push code changes to the Lambda without redeploying the whole stack.

1. Package your application code

This script builds a zip containing your code and dependencies using uv:
`./scripts/deploy_code.sh`

This script will:
Export dependencies using uv
Create a build directory
Zip the application
Upload it to your S3 artifacts bucket

2. Update the Lambda function
   After the artifact is uploaded, run:
   `./scripts/update_lambda_code.sh`
   This forces AWS Lambda to update to the newest zip file.
   No need to redeploy CloudFormation — this updates only the function's code.

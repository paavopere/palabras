# Deployment on AWS

Instructions for macOS, conda, homebrew

Install Terraform and AWS CLI:

```
conda install terraform
brew install awscli
```

Create an encrypted S3 bucket to store Terraform state and a DynamoDB table to manage locking. Instructions at https://blog.gruntwork.io/how-to-manage-terraform-state-28f5697e68fa

Create a backend.hcl file with the names and region of the created bucket and table:

```hcl
# backend.hcl
bucket         = "<insert s3 bucket name>"
region         = "<insert region>"
dynamodb_table = "<insert dynamodb table name>"
encrypt        = true
```

Initialize AWS and Terraform:

```
aws configure --profile palabras
export AWS_PROFILE=palabras
terraform init -backend-config=backend.hcl
terraform plan
```

Deploy infrastructure:

```
terraform apply
```
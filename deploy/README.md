# Try it out

Try the deployed instance out with (replace `ser` with any Spanish word found on Wiktionary):

```
curl https://c9rf83tgc3.execute-api.eu-north-1.amazonaws.com/palabras/ser
```

The output is formatted for display in a true-color terminal. In other cases (e.g. navigating to the URL in a browser), you'll see character jumble from the color escape sequences.

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

Deploy infrastructure and function code (when you're in `deploy`, `..` points to project root):

```
pip install --target ./package ..
terraform apply
```
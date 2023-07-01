terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  backend "s3" {
    key = "palabras/terraform.tfstate"
  }
}

provider "aws" {
  region = "eu-north-1"
}

# vpc

resource "aws_vpc" "palabras" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {
    Name = "palabras-vpc"
  }
}

# subnet

resource "aws_subnet" "palabras" {
  vpc_id = aws_vpc.palabras.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "eu-north-1a"

  tags = {
    Name = "palabras-subnet"
  }
}

# security group

resource "aws_security_group" "palabras" {
  name = "palabras-sg"
  description = "Allow inbound traffic"

  vpc_id = aws_vpc.palabras.id

  ingress {
    from_port = 0
    to_port = 65535
    protocol = "tcp"
    cidr_blocks = ["10.0.1.0/24"]
  }

  egress {
    from_port = 0
    to_port = 65535
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# iam role and policy

resource "aws_iam_role" "palabras" {
  name = "palabras-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}


resource "aws_iam_policy" "palabras" {
  name = "palabras-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = ["arn:aws:logs:*:*:*"]
    },{
      Effect = "Allow"
      Action = [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ]
      Resource = ["*"]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "palabras" {
  policy_arn = aws_iam_policy.palabras.arn
  role = aws_iam_role.palabras.name
}

# zip the code and deploy to lambda function

data "archive_file" "python_lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  excludes    = [".git",
                 ".github",
                 ".mypy_cache",
                 ".pytest_cache",
                 ".tox",
                 "data",
                 "deploy",
                 "test",
                 ".coverage",
                 ".flake8",
                 ".DS_Store"]
  output_path = "${path.module}/palabras.zip"
}

resource "aws_lambda_function" "palabras" {
  filename         = data.archive_file.python_lambda_package.output_path
  function_name    = "palabras"
  role             = aws_iam_role.palabras.arn
  handler          = "palabras.lambda.lambda_handler"
  source_code_hash = data.archive_file.python_lambda_package.output_base64sha256
  runtime          = "python3.10"
  timeout          = 60
  memory_size      = 128

  vpc_config {
    subnet_ids         = [aws_subnet.palabras.id]
    security_group_ids = [aws_security_group.palabras.id]
  }
}

# api gateway

resource "aws_apigatewayv2_api" "palabras" {
  name = "palabras"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "palabras" {
  api_id = aws_apigatewayv2_api.palabras.id
  name = "palabras"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  route_settings {
    route_key = "GET /"
    logging_level = "INFO"
    throttling_burst_limit = 1
    throttling_rate_limit = 1
  }
}

resource "aws_apigatewayv2_integration" "palabras" {
  api_id = aws_apigatewayv2_api.palabras.id

  integration_uri    = aws_lambda_function.palabras.invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "palabras" {
  api_id = aws_apigatewayv2_api.palabras.id

  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.palabras.id}"
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name = "/aws/api_gw/${aws_apigatewayv2_api.palabras.name}"

  retention_in_days = 30
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.palabras.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.palabras.execution_arn}/*/*"
}


output "function_name" {
  description = "Name of the Lambda function."
  value = aws_lambda_function.palabras.function_name
}

output "base_url" {
  description = "Base URL for API Gateway stage."
  value = aws_apigatewayv2_stage.palabras.invoke_url
}
resource "aws_s3_bucket" "bio_data_bucket" {
  bucket = local.shared_bucket_name
  force_destroy = true
}

resource "aws_lambda_function" "ingestor" {
  function_name = "MKADataIngestor"
  role          = data.aws_iam_role.lab_role.arn
  handler       = "lambda_ingest.lambda_handler"
  runtime       = "python3.9"
  filename      = "ingest.zip" 
  environment {
    variables = { BUCKET_NAME = aws_s3_bucket.bio_data_bucket.bucket }
  }
}

resource "aws_apigatewayv2_api" "ingest_api" {
  name          = "MKAIngestAPI"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_integration" "ingest_lambda_int" {
  api_id           = aws_apigatewayv2_api.ingest_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.ingestor.invoke_arn
}

resource "aws_apigatewayv2_route" "collect_route" {
  api_id    = aws_apigatewayv2_api.ingest_api.id
  route_key = "POST /collect"
  target    = "integrations/${aws_apigatewayv2_integration.ingest_lambda_int.id}"
}

resource "aws_apigatewayv2_stage" "ingest_default_stage" {
  api_id      = aws_apigatewayv2_api.ingest_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "ingest_api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ingest_api.execution_arn}/*/*"
}


resource "aws_lambda_function" "scanner" {
  function_name = "MKAVerifyController"
  role          = data.aws_iam_role.lab_role.arn
  handler       = "lambda_verify.lambda_handler"
  runtime       = "python3.9"
  filename      = "verify.zip" 
  timeout       = 10
  
  environment {
    variables = { BUCKET_NAME =  aws_s3_bucket.bio_data_bucket.bucket }
  }
}

resource "aws_apigatewayv2_api" "bio_api" {
  name          = "MKASecurityAPI"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_integration" "verify_lambda_int" {
  api_id           = aws_apigatewayv2_api.bio_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.scanner.invoke_arn
}

resource "aws_apigatewayv2_route" "verify_route" {
  api_id    = aws_apigatewayv2_api.bio_api.id
  route_key = "POST /verify"
  target    = "integrations/${aws_apigatewayv2_integration.verify_lambda_int.id}"
}

resource "aws_apigatewayv2_stage" "verify_default_stage" {
  api_id      = aws_apigatewayv2_api.bio_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "verify_api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scanner.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.bio_api.execution_arn}/*/*"
}
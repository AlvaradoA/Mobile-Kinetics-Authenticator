output "INGEST_API_URL" {
  value = "${aws_apigatewayv2_stage.ingest_default_stage.invoke_url}/collect"
}

output "VERIFY_API_URL" {
  value = "${aws_apigatewayv2_stage.verify_default_stage.invoke_url}/verify"
}

output "BUCKET_NAME" {
  value = aws_s3_bucket.bio_data_bucket.id
}
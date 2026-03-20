provider "aws" { region = "us-east-1" }
data "aws_iam_role" "lab_role" { name = "LabRole" }
resource "random_id" "id" { byte_length = 4 }

locals {
  # Change to something globally unique (e.g., mka-data-lake-2026-xyz)
  shared_bucket_name = "mka-data-lake-${random_id.id.hex}" 
}
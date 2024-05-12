output "input_sqs_arn" {
    value = aws_sqs_queue.sqs_request_queue.arn
}

output "output_sqs_arn" {
    value = aws_sqs_queue.sqs_response_queue.arn
}

output "input_s3_bucket_arn" {
    value = aws_s3_bucket.s3_input_bucket.arn
}

output "output_s3_bucket_arn" {
    value = aws_s3_bucket.s3_output_bucket.arn
}

output "web_server_ip" {
    value = aws_instance.web_tier.public_ip
}

output "aws_ami_from_instance" {
    value = aws_ami_from_instance.app_tier_image.id
}

output "app_server_ips" {
    value = [for instance in aws_instance.app_tier_copies : instance.public_ip]
}

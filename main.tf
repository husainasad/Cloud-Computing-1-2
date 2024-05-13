provider "aws" {
    region = var.aws_region
}

resource "aws_sqs_queue" "sqs_request_queue" {
  name = var.sqs_request
}

resource "aws_sqs_queue" "sqs_response_queue" {
  name = var.sqs_response
}

resource "aws_s3_bucket" "s3_input_bucket" {
  bucket = var.s3_input
}

resource "aws_s3_bucket" "s3_output_bucket" {
  bucket = var.s3_output
}

resource "aws_instance" "web_tier" {
  ami = var.ami_id
  instance_type = var.instance_type
  security_groups = var.security_group_list
  iam_instance_profile = var.iam_profile
  key_name = var.server_key
  user_data = templatefile(var.web_server_template, {})
  user_data_replace_on_change = true
  tags = {
    Name = var.web_server
  }
}

resource "aws_instance" "app_tier" {
  ami = var.ami_id
  instance_type = var.instance_type
  security_groups = var.security_group_list
  iam_instance_profile = var.iam_profile
  key_name = var.server_key
  user_data = templatefile(var.app_server_template, {})
  user_data_replace_on_change = true
  tags = {
    Name = var.app_server
  }
}

resource "null_resource" "wait_for_instance_ready" {
  depends_on = [aws_instance.app_tier]

  connection {
    type = "ssh"
    user = "ubuntu"
    private_key = file(var.local_key_path)
    host = aws_instance.app_tier.public_ip
  }

  provisioner "remote-exec" {
    inline = [
        "echo 'Waiting for user data script to finish'",
        "cloud-init status --wait > /dev/null"
    ]
  }
}

resource "aws_ami_from_instance" "app_tier_image" {
  name = var.app_server_image 
  source_instance_id = aws_instance.app_tier.id
  depends_on = [null_resource.wait_for_instance_ready]
}

resource "aws_instance" "app_tier_copies" {
  ami = aws_ami_from_instance.app_tier_image.id
  instance_type = var.instance_type
  security_groups = var.security_group_list
  iam_instance_profile = var.iam_profile
  key_name = var.server_key
  count = var.max_app_servers
  tags = {
    Name = "${var.app_server_copies}${count.index + 1}"
  }
}
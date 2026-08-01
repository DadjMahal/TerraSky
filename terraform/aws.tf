provider "aws" {
  region = "eu-central-1"   # або не вказуйте, якщо встановлено AWS_DEFAULT_REGION
}

resource "aws_instance" "Hermes" {
  ami                         = "ami-0303e2e4a29f041a3"
  instance_type               = "t3.small"
  subnet_id                   = "subnet-0dcac864dda003ea9"
  vpc_security_group_ids      = ["sg-03ccffd621bc70fb1"]
  key_name                    = "main-key"
  associate_public_ip_address = true
  ebs_optimized               = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
  }

  credit_specification {
    cpu_credits = "unlimited"
  }

  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
    http_protocol_ipv6          = "disabled"
    instance_metadata_tags      = "disabled"
  }

  tags = {
    Name = "Hermes"
  }
}

resource "aws_instance" "Vikunja" {
  ami                         = "ami-0303e2e4a29f041a3"
  instance_type               = "t3.micro"
  subnet_id                   = "subnet-0dcac864dda003ea9"
  vpc_security_group_ids      = ["sg-07cb93dde645c83e5"]
  key_name                    = "main-key"
  associate_public_ip_address = true
  ebs_optimized               = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
  }

  credit_specification {
    cpu_credits = "unlimited"
  }

  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
    http_protocol_ipv6          = "disabled"
    instance_metadata_tags      = "disabled"
  }

  tags = {
    Name = "Vikunja"
  }
}

provider "alicloud" {
  region = var.alibaba_region
}

variable "alibaba_region" {
  default = "us-west-1"
}

resource "alicloud_instance" "AlibabaPower" {
  instance_name              = "alibaba-power"
  instance_type              = "ecs.e-c1m2.2xlarge"
  image_id                   = "ubuntu_22_04_x64_20G_alibase_20260615.vhd"
  security_groups            = ["sg-rj9gg150rqqonqi3rvxr"]
  vswitch_id                 = "vsw-rj9p1849y037bm78vsb5p"
  system_disk_category       = "cloud_essd_entry"
  system_disk_size           = 100
  internet_charge_type       = "PayByTraffic"
  internet_max_bandwidth_out = 100
  host_name                  = "iZrj9gg150rqqonqi5jo1gZ"
  password                   = "place_holder_password"
  deletion_protection        = false
  dry_run                    = false

  tags = {
    "ecs" = "trial"
  }
  volume_tags = {
    "ecs" = "trial"
  }

  cpu_options {
    core_count       = 4
    threads_per_core = 2
  }

  image_options {
    login_as_non_root = false
  }

  timeouts {}

  lifecycle {
    ignore_changes = [password]
  }
}

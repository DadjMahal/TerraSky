provider "oci" {
  # автентифікація через змінні середовища
}

resource "oci_core_instance" "Hunter" {
  availability_domain = "WheS:EU-FRANKFURT-1-AD-3"
  compartment_id      = "ocid1.tenancy.oc1..aaaaaaaassj7utykwc447s2pjkp375ab6qf2nyrgs7imyrhpbs3hsqxuid7a"
  display_name        = "retry-bot-server"
  shape               = "VM.Standard.E2.1.Micro"

  source_details {
    source_type                     = "image"
    source_id                       = "ocid1.image.oc1.eu-frankfurt-1.aaaaaaaakfbgwmypcki4ge3z4pkvkr5am7e66ti5jqqhitohkgd6ztfhbejq"
    boot_volume_size_in_gbs         = 47
    boot_volume_vpus_per_gb         = 10
    is_preserve_boot_volume_enabled = false
  }

  create_vnic_details {
    subnet_id        = "ocid1.subnet.oc1.eu-frankfurt-1.aaaaaaaanelqtzire5ztk5lodwppsmrl76ztlgnnwvjiatcsdkquiwgyflfa"
    assign_public_ip = true
    hostname_label   = "retry-vnic"
    private_ip       = "10.0.1.68"
  }

  metadata = {
    "ssh_authorized_keys" = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDGF7ZmrndKrXfa2rii6q/FF++n/Otk8R0Gwyi5jve/4ek0Yxciq4ZeARzM+JccTOIyv+hZoP5zmlSTllooULE24ar4sk9ch5YI6yydQHz5UnV/Hcqdqli7ivRGIoioORFhs9Gi3uSnfRE3mH8rZYFglFTStPvtI7DhOgEIyE4BFdXr8kDaPzO4r5Aepr/E+yPOfSeRaQg0X1wMHyUt1iRT3O4Mqvm5Q9VTM4OrIyIhRLxvkLi6nJ4i2tpslMmevr1xRZNNx4V9In8ao446oAN5myxFe2GMfZjTrN/dQbxEJ6nZIrziAmcKNFGi+4BRyQgJG9gU79ZY7Z13Wb0n6ErL ssh-key-2026-07-09"
  }

  agent_config {
    are_all_plugins_disabled = false
    is_management_disabled   = false
    is_monitoring_disabled   = false

    plugins_config {
      desired_state = "DISABLED"
      name          = "Vulnerability Scanning"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "OS Management Hub Agent"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Management Agent"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Custom Logs Monitoring"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute RDMA GPU Monitoring"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Compute Instance Monitoring"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute HPC RDMA Auto-Configuration"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute HPC RDMA Authentication"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Cloud Guard Workload Protection"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Block Volume Management"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Bastion"
    }
  }

  availability_config {
    is_live_migration_preferred = false
    recovery_action             = "RESTORE_INSTANCE"
  }

  launch_options {
    boot_volume_type                    = "PARAVIRTUALIZED"
    firmware                            = "UEFI_64"
    is_consistent_volume_naming_enabled = true
    is_pv_encryption_in_transit_enabled = true
    network_type                        = "PARAVIRTUALIZED"
    remote_data_volume_type             = "PARAVIRTUALIZED"
  }

  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }

  lifecycle {
    ignore_changes = [
      defined_tags,
      freeform_tags,
      security_attributes,
      extended_metadata,
      shape_config,
    ]
  }
}

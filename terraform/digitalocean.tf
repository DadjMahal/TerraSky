# DigitalOcean provider — managed by SkyDash.
#
# SkyDash reads Droplet inventory from terraform.tfstate (state_reader.py maps
# `digitalocean_droplet` resources) and queries live state via the DO API v2
# using the token below.  No extra Python package is needed: the provider uses
# `requests` (a transitive dependency of boto3).
#
# Required env var (put in /home/volodro/terraform/.env — NEVER commit, see
# terraform/.gitignore):
#     DIGITALOCEAN_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#
# Workflow to onboard a Droplet:
#   1. Declare it here as a `digitalocean_droplet` resource (or import an
#      existing one with `terraform import`).
#   2. `terraform init && terraform plan` populates terraform.tfstate with the
#      real droplet id / region / size.
#   3. `sudo cp terraform/terraform.tfstate /home/volodro/terraform/ && restart`
#      (or use scripts/seed_digitalocean_state.py once you have a token).
#   4. `sudo systemctl restart skydash`

terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  # token is read from DIGITALOCEAN_ACCESS_TOKEN (environment)
}

# --- Example (uncomment + rename; then import to populate state) ---
# resource "digitalocean_droplet" "example" {
#   name   = "my-droplet"
#   size   = "s-2vcpu-2gb"
#   image  = "ubuntu-22.04-x64"
#   region = "nyc3"
#   tags   = ["skydash"]
# }

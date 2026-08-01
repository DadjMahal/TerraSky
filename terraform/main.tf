terraform {
  required_version = ">= 1.0"

  # Локальний state-файл (для початку)
  backend "local" {
    path = "terraform.tfstate"
  }
}

# Провайдери будуть описані окремо, але для прикладу можна залишити пустим

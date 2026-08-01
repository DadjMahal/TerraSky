# Загальні змінні, які будуть використовуватися в модулях
variable "project_name" {
  description = "Назва проекту для тегування"
  type        = string
  default     = "multi-cloud-mgmt"
}

variable "environment" {
  description = "Середовище (dev, stage, prod)"
  type        = string
  default     = "dev"
}

provider "azurerm" {
  features {}
}

resource "azurerm_linux_virtual_machine" "Terraform" {
  name                            = "free-vm"
  resource_group_name             = "RG-FREE-VM"
  location                        = "spaincentral"
  size                            = "Standard_B2ats_v2"
  admin_username                  = "volodro"
  disable_password_authentication = true

  network_interface_ids = [
    "/subscriptions/6157d44e-7485-42d6-abc2-11d719c38654/resourceGroups/rg-free-vm/providers/Microsoft.Network/networkInterfaces/free-vm799-95c73930"
  ]

  admin_ssh_key {
    username   = "volodro"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC6nKNNZOsyz134sh+LdDV0bc6ED8Bg8KV6NW56ZORzxCLkI+JqnFSMp2YAy7eDpMzFDhA/eupkukGcXWhozA3KrC0eFtp1jL1DS7Xj0Qqnr50CWwW2+9vJnj8xQtIeUC/rYqnXsIGZsBG5QMxzWlHxiZd10ODMIMaYiAOtMyU8TfBfkwQjfh1oymxXZUEJCEeUkDX/taiQH4DPm3aKQqDwgBPOPwFMmoEEfu0dwVRNRyQBwOdqTQiyF3kyRrmLBrd2kGEFEukrSjxfZJI3RdmUiQItmx41zoHKpDb+wwqZ6dP6PCv765U6yf1NCK5f2BwAaa7V+iuOAU8j8Jg4FA2kAmC1+TjaIrJwTev6GSujDRYO3HfSiTXWeePv4bro22JR1tukFeQ8NVtz8rg5bb6LEiNL9IfRD35gdTcjQ5fNgSop187QZ+jbw7e9U/arJxz/D+7GgwmTDRwGgoGridVWkHwwler1Fhne+Pa36lkRBZybJtlA3CnmLKPwZdd7f20= generated-by-azure"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 30
  }

  source_image_reference {
    publisher = "canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  additional_capabilities {
    hibernation_enabled = false
    ultra_ssd_enabled   = false
  }

  boot_diagnostics {
    storage_account_uri = null
  }

  secure_boot_enabled = true
  vtpm_enabled        = true
  zone                = "3"
}

resource "azurerm_linux_virtual_machine" "MMO_Server" {
  name                            = "power-vm-1"
  resource_group_name             = "RG-PAID-VM"
  location                        = "polandcentral"
  size                            = "Standard_E2s_v3"
  admin_username                  = "volodro"
  disable_password_authentication = true

  network_interface_ids = [
    "/subscriptions/6157d44e-7485-42d6-abc2-11d719c38654/resourceGroups/rg-paid-vm/providers/Microsoft.Network/networkInterfaces/power-vm-1557-c13cec78"
  ]

  admin_ssh_key {
    username   = "volodro"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCy4eSKKidATfylz31YAc9D+iQWV9DwkteF+FR4zZKUK5R9fUBAKUmWDjW76XG7BGgp1FTWv3/McxUxSyfhOFUC5hCoCxPRcRGvXMqBhEEIOja0HugOB+vNUE3xdnrgKgWU6/TP4kRnbyYuTwkImWrvprcThcoPLc44lveZGxRETOz5/kPr8xuLt1lbq1unAe9kLLOGvrHHxOqn/iNnDEQquwyFyR5Lo6pdW1hGBDwfFLoFg9kk5V7gLlGqdjSJwShxyLDtS4Wv/BN8nWpEh4vPZh/SXynUSz6m90TnhXp8CxpGzwipBTNulB86Jn84ZL9vXCk6mHaIjXwlCC5FHj/OLMMkhrwvN8PPqly0NqWUKB9mq0sPX0EompRDYh/Ya6RkBTR0Ed83x05Pry0unA4jM7JyX3ZnhW0YqPXa0FqmXYiB3VlQMcE8fV6vgg58cF8S6FDvKRAmRnzn6/972ExMOaZ5w1p5XHHP701Kq0nNLypMuXuc2iI2pkMeLQCBn/U= generated-by-azure"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 30
  }

  source_image_reference {
    publisher = "canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  additional_capabilities {
    hibernation_enabled = false
    ultra_ssd_enabled   = false
  }

  boot_diagnostics {
    storage_account_uri = null
  }

  secure_boot_enabled = true
  vtpm_enabled        = true
  zone                = "3"
}

resource "azurerm_linux_virtual_machine" "MMSystem" {
  name                            = "power-vm-2"
  resource_group_name             = "rg-paid-vm"
  location                        = "polandcentral"
  size                            = "Standard_D2s_v3"
  admin_username                  = "volodro"
  disable_password_authentication = true

  network_interface_ids = [
    "/subscriptions/6157d44e-7485-42d6-abc2-11d719c38654/resourceGroups/rg-paid-vm/providers/Microsoft.Network/networkInterfaces/power-vm-2665-ce289236"
  ]

  admin_ssh_key {
    username   = "volodro"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCwaaiBv2ugR03Oj/R3//kaTNQgUaGuKJW8Z6Bad8hlmgGfiBIjk6mQ7FOXOepi0XzBZIqOoJm1NtJgNKbIr7sqxJOVA+fn8UfozoIvpkv+J1+1XIbYfkwFELkgV+mglL58OTrOcfdwSYoiLKSSemFRTaPTnABTXgg1cNZ66IvdYV30v5UYviEqk8tCmTzJJfvwaFRt6oYInny0lJeEUCRD9z8VZ75QyNf8DwwmFd2T/wAvvCRTB19eZPNpQUHj4i/T5+TqYmu5XYTBLCEdCTy1KrdTJfZgylK3Dip+5fem2TBLZjRku4Fqmo+92KtY3WxA+vEITonS0aujj6Dm9cAmyPu52X61OI/BIoq+kfmImYjDvakiKelR6UD1+ifQWpI496ktnoEEv1921xBTeW0GiNQ6HYPUeMgDB8SSaCctG2CHVrQqoUj8GiYmptcWbclXParBZflnnCIJL018LnetP2Y0XydrG1DSEKBcO/OuoC8FaAXqTVVsOnFLBR5lUw0= generated-by-azure"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  additional_capabilities {
    hibernation_enabled = false
    ultra_ssd_enabled   = false
  }

  boot_diagnostics {
    storage_account_uri = null
  }

  secure_boot_enabled = true
  vtpm_enabled        = true
  zone                = "3"
}

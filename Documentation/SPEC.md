# SPEC.md ~ Specification of project Dashboard and requirements

The long-term goal is to transform SkyDash into a lightweight multi-cloud infrastructure management panel.

## Dashboard

The main page should provide a clear overview of all infrastructure.

Each instance should display:

- Name
- Cloud Provider
- Current Status
- Region
- Availability Zone (if available)
- Instance Type
- Public IP
- Private IP
- Operating System
- CPU
- RAM
- Disk Size
- Creation Date
- Tags
- Free Tier indicator (future)
- Estimated monthly cost (future)

The dashboard should support:

- Search
- Filtering
- Sorting
- Status badges
- Provider icons
- Responsive layout
- Automatic status refresh without page reload

---

## Instance Management

Every supported provider should expose the same functionality.

Supported providers:

- AWS
- Azure
- Oracle Cloud
- Alibaba Cloud

Every instance should support:

- Start
- Stop
- Reboot (future)
- Refresh status
- Open details page

The interface should immediately reflect state changes.

Examples:

Running

Starting...

Stopping...

Stopped

Error

Unknown

---

## Instance Details Page

Every instance should have its own dedicated page.

Example:

/instance/aws-hermes

The page should contain all available information about the instance.

Possible sections:

### Overview

- Name
- Provider
- Region
- Status
- Public IP
- Private IP
- Uptime (future)

### Hardware

- Instance Type
- CPU
- RAM
- Disk
- Architecture

### Network

- Public IP
- Private IP
- Security Groups (future)

### Actions

- Start
- Stop
- Refresh

Future:

- SSH shortcut
- Console link
- Terraform resource
- Logs
- Monitoring

---

## UI / UX Goals

The interface should feel similar to modern cloud dashboards such as:

- AWS Console
- Azure Portal
- Hetzner Cloud
- DigitalOcean

Requirements:

- Clean design
- Fast loading
- Responsive
- Modern cards
- Dark/Light theme (future)
- Clear status indicators
- Minimal clicks
- Lightweight implementation
- No heavy frontend frameworks

---

## Architecture Goals

Business logic must be provider-independent.

Each provider should implement the same interface.

Example:

- get_instances()
- get_instance_details()
- get_status()
- start_instance()
- stop_instance()

This architecture should make adding new cloud providers straightforward.

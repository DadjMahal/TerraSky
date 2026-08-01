import json
import subprocess
import sys
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'change-me-to-something-random'

TERRAFORM_DIR = "/home/volodro/terraform"
STATE_FILE = f"{TERRAFORM_DIR}/terraform.tfstate"

PROVIDER_ICONS = {
    "aws": "bi-cloud-aws",
    "azurerm": "bi-microsoft",
    "alicloud": "bi-cloud",
    "oci": "bi-server",
}

def load_state():
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def get_instances():
    try:
        state = load_state()
        # У сирому файлі ресурси лежать у кореневому ключі "resources"
        res_list = state.get("resources", [])
        print(f"DEBUG: Found {len(res_list)} raw resources in state", file=sys.stderr)

        resources = []
        for res in res_list:
            res_type = res.get("type", "")
            if res_type not in [
                "aws_instance",
                "azurerm_linux_virtual_machine",
                "alicloud_instance",
                "oci_core_instance",
            ]:
                continue

            # Отримуємо атрибути з першого інстансу (зазвичай один)
            instances = res.get("instances", [])
            if not instances:
                continue
            attrs = instances[0].get("attributes", {})

            # Провайдер: обрізаємо provider["..."] до короткої назви
            provider_raw = res.get("provider", "unknown")
            provider = "unknown"
            if '["' in provider_raw:
                # Витягаємо частину всередині лапок
                provider_full = provider_raw.split('["')[1].rstrip('"]')
                provider = provider_full.split("/")[-1]
            else:
                provider = provider_raw

            # Ім'я
            name = attrs.get("tags", {}).get("Name",
                     attrs.get("display_name",
                     attrs.get("name", res.get("name", "unnamed"))))

            # Статус
            status = "unknown"
            if provider == "aws":
                status = attrs.get("instance_state", "unknown")
            elif provider == "alicloud":
                status = attrs.get("status", "unknown")
            elif provider == "oci":
                status = attrs.get("state", "unknown")
            # Azure не зберігає стан у сирому файлі

            instance_type = attrs.get("instance_type",
                            attrs.get("size",
                            attrs.get("shape", "unknown")))
            region = attrs.get("region",
                     attrs.get("location", "unknown"))
            public_ip = attrs.get("public_ip", "N/A")
            instance_id = attrs.get("id", "")

            can_manage = (provider == "aws")

            # Адреса ресурсу (для дій)
            address = f"{res_type}.{res.get('name', '')}"

            resources.append({
                "name": name,
                "provider": provider,
                "status": status.lower(),
                "type": instance_type,
                "region": region,
                "public_ip": public_ip,
                "instance_id": instance_id,
                "address": address,
                "icon": PROVIDER_ICONS.get(provider, "bi-question-circle"),
                "can_manage": can_manage,
            })

        print(f"DEBUG: Filtered {len(resources)} matching instances", file=sys.stderr)
        return resources
    except Exception as e:
        print(f"ERROR reading state: {e}", file=sys.stderr)
        return []

@app.route("/")
def index():
    instances = get_instances()
    return render_template("instances.html", instances=instances)

@app.route("/action/<path:address>/<action>")
def instance_action(address, action):
    if action not in ["start", "stop"]:
        flash("Invalid action", "danger")
        return redirect(url_for("index"))

    # Знаходимо instance_id за адресою
    state = load_state()
    instance_id = None
    for res in state.get("resources", []):
        if f"{res.get('type')}.{res.get('name')}" == address:
            instances = res.get("instances", [])
            if instances:
                instance_id = instances[0].get("attributes", {}).get("id")
            break

    if not instance_id:
        flash("Instance ID not found in state", "danger")
        return redirect(url_for("index"))

    try:
        if action == "start":
            cmd = ["aws", "ec2", "start-instances", "--instance-ids", instance_id]
        else:
            cmd = ["aws", "ec2", "stop-instances", "--instance-ids", instance_id]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            flash(f"Action '{action}' sent successfully to {instance_id}", "success")
        else:
            flash(f"AWS CLI error: {result.stderr}", "danger")
    except subprocess.TimeoutExpired:
        flash("Timeout while calling AWS CLI", "warning")
    except FileNotFoundError:
        flash("AWS CLI not found. Please install awscli", "danger")
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "danger")

    return redirect(url_for("index"))

@app.route("/refresh")
def refresh():
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)

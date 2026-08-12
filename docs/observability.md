# SkyDash Observability — Iteration 10 (§45, §81-82)

Provisioned on the production droplet `167.172.188.248` (Ubuntu 24.04) and
**verified live**. It is intentionally local-only (loopback) — no external
monitoring spend.

## Components

| Component | Version | Systemd unit | Port | Status |
|-----------|---------|--------------|------|--------|
| Prometheus | 2.45.3 (`2.45.3+ds`) | `prometheus` | 9090 | active / enabled |
| Grafana | (apt, `grafana-server`) | `grafana-server` | 3000 | active / enabled |

Prometheus scrapes **two** jobs: itself (`localhost:9090`) and SkyDash:

```yaml
# /etc/prometheus/prometheus.yml
- job_name: 'skydash'
  metrics_path: '/api/v1/metrics'
  static_configs: [{ targets: ['127.0.0.1:8080'] }]
  scrape_interval: 15s
```

## /api/v1/metrics endppoint (§45)

Public (no auth — Prometheus scrapes from 127.0.0.1), not rate-limited, served
directly by the Flask process via `skydash/prometheus_metrics.py`. Emits only
cheap, non-rate-limited data (inventory counts + provider availability + HTTP
request counter); it never triggers a cloud power-state poll, so it cannot be
used to enumerate/abuse the cloud APIs.

Exposed metrics (`skydash_*` namespace):

- `skydash_up` (gauge) — liveness.
- `skydash_uptime_seconds` (counter) — seconds since process start.
- `skydash_instances{provider="..."}` (gauge) — inventory count per provider.
- `skydash_http_requests_total` (counter) — total requests since start, fed by
  the `_count_prometheus_requests` after_request hook in `skydash/app.py`.

## Verification (real output)

```
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/v1/metrics
200   # content-type: text/plain; version=0.0.4

$ curl -s "http://127.0.0.1:9090/api/v1/targets" | jq '.data.activeTargets[] | {job,health}'
{ "job": "prometheus", "health": "up" }
{ "job": "skydash",      "health": "up" }

$ curl -s "http://127.0.0.1:9090/api/v1/query?query=skydash_instances" | jq '.data.result[].metric.provider'
"aws" / "digitalocean" / "oracle"
```

## Grafana

- **Datasource (provisioned, `uid=skydash-prom`):** Prometheus @
  `http://127.0.0.1:9090`, default data source.
  File: `/etc/grafana/provisioning/datasources/skydash-datasource.yaml`.
- **Dashboard (provisioned):** `SkyDash Overview` (`uid=skydash-overview`),
  folder `SkyDash`, auto-refresh 15s. Panels: SkyDash up (stat), Instances by
  provider (series), HTTP requests total (series), Uptime (stat).
  File: `/etc/grafana/provisioning/dashboards/files/skydash-dashboard.json`.
- **Default credentials on first boot:** `admin` / `admin` (change via the UI).

## Notes / limits

- All scrape traffic stays on the loopback interface — the droplet's public IP
  exposes only the Flask dashboard (nginx `:80`) and **not** :9090/:3000.
- Alerting rules are staged in the repo (`/root/TerraSky/skydash/alerts/` if
  present) but **not yet loaded** into Prometheus `rule_files` (Iteration 10
  hardening — deferred until the alerting owner decision).

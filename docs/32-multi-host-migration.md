# 32 — Multi-Host Migration

When and how to leave single-host Docker Compose for a real orchestrator.

## Stay on Compose if

- < 5 000 daily active users
- Single tenant or small set of tenants
- Acceptable downtime windows (5–30 min) for upgrades
- Single ops engineer comfortable with `ssh + docker compose`
- One geographic region

## Move to Kubernetes (or Swarm) when

- > 5 000 DAU sustained
- Need rolling deploys without downtime
- Multi-region requirements
- Need autoscaling (especially Celery workers under spiky AI load)
- Compliance requires fine-grained pod-level network policies
- Multiple ops engineers with k8s fluency

## Migration outline

### 1. Containers — already done

The Compose images are already production-grade (see `docker-compose.prod.yml`).
Same images run in Kubernetes.

### 2. Stateful services

- **Postgres**: managed service (RDS, Cloud SQL) or operator (CloudNativePG).
- **Redis**: managed (ElastiCache) or operator (Redis Operator).
- **Object storage**: S3-compatible — already cloud-friendly.

### 3. Workloads

| Workload | Replicas | Notes |
|---|---|---|
| `backend` | 3+ behind a Service | rolling deploys |
| `worker` (Celery) | autoscaled by queue depth | KEDA scaler |
| `beat` | exactly 1 | leader election via lease |
| `migrate` | Job (one-shot per release) | runs before backend rollout |
| `admin-ui` | 2+ behind a Service | static, easy to scale |
| `portal-ui` | 2+ behind a Service | same |

### 4. Networking

- Ingress controller (NGINX or Traefik) replaces our nginx container.
- Cert-manager replaces certbot.
- Network policies isolate `worker` from public ingress.
- `/api/realtime/` requires sticky sessions per backend pod **only if** SSE
  state is held in-memory; with Redis Pub/Sub backplane, sticky sessions are
  not required.

### 5. Configuration

- Secrets in `Secret` resources (External Secrets Operator → Vault / KMS).
- ConfigMaps for non-secret env.
- Helm chart in `deploy/helm/` (planned) parameterizes images, replicas,
  resources, ingress hosts.

### 6. Observability

- Prometheus Operator scrapes `backend`, `worker`, `redis-exporter`,
  `postgres-exporter`.
- Loki + Promtail for logs.
- Grafana with the engine's dashboards.

### 7. Cutover plan

1. Provision k8s cluster + managed Postgres + managed Redis.
2. Restore latest backup into managed Postgres.
3. Deploy engine via Helm chart (single replica).
4. Run smoke E2E against the new cluster.
5. Shift DNS to the new cluster (low TTL beforehand).
6. Keep Compose host cold-standby for 7 days.
7. Decommission old host.

## What we explicitly defer

- Service mesh (Istio / Linkerd) — not needed at our complexity.
- gRPC internal traffic — HTTP+JSON is enough.
- Sharding Postgres — single primary + read replicas covers our load.
- Vertical autoscaling on stateful services — keep them sized manually.

## Migration risks

- Stateful migration windows — plan for 30–60 min of read-only mode if needed.
- `AI_SECRET_KEY` rotation across pods — use the same secret in `Secret`
  resource; never bake into images.
- Sticky sessions in legacy proxies — confirm SSE works without them.

# Deployment: Kubernetes (local) and AWS EKS

Two paths: **local** (free, with `kind`) to prove the manifests work, and **AWS EKS**
(real cloud, costs money) for the production demo.

## Manifests

`k8s/base/` contains 14 resources:
- `00-namespace-config.yaml` — namespace, ConfigMap, Secret template
- `10-postgres.yaml` — Postgres + pgvector as a StatefulSet with a persistent volume
- `20-services.yaml` — extraction, rag, agent Deployments + Services (probes, resource limits)
- `30-frontend-ingress.yaml` — frontend Deployment + Service + Ingress

Every backend pod reads config from the ConfigMap and the OpenAI key from the Secret —
secrets never live in the manifests.

## Local (kind) — start here

```bash
# Prereqs: docker, kind, kubectl
export OPENAI_API_KEY=sk-...        # or rely on .env
./scripts/deploy-kind.sh
```

The script creates a cluster, installs the nginx ingress controller, builds all
images, loads them into kind, applies the manifests, and waits for rollouts. When it
finishes, the app is at http://localhost.

Inspect and tear down:
```bash
kubectl -n fleet get pods,svc,ingress
kind delete cluster --name fleet-local
```

## AWS EKS — the cloud demo

> **Cost warning:** an EKS control plane is ~$0.10/hour (~$2.40/day) plus node costs.
> Budget a few dollars, capture your screenshots/GIF, then run the teardown. Set a
> billing alert in the AWS console first.

### 1. One-time: create the cluster (eksctl is easiest)
```bash
eksctl create cluster \
  --name fleet-eks \
  --region eu-central-1 \
  --nodes 2 --node-type t3.small \
  --managed
```

### 2. Install the AWS Load Balancer Controller
Follow the AWS docs to install the controller so the Ingress provisions an ALB. (This
needs an IAM OIDC provider + the controller's IAM policy — the AWS guide walks through it.)

### 3. Deploy the app
```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=eu-central-1
export OPENAI_API_KEY=sk-...
./scripts/deploy-eks.sh
```

This pushes images to ECR, rewrites the manifests to pull from ECR, applies them, and
waits for rollouts. Get the public URL:
```bash
kubectl -n fleet get ingress fleet-ingress
```

### 4. Tear down (IMPORTANT)
```bash
./scripts/eks-teardown.sh
```

### Production note
For a real deployment you'd use **Amazon RDS for PostgreSQL** (with the `pgvector`
extension) instead of the in-cluster StatefulSet, so the database is managed, backed
up, and survives cluster changes. The in-cluster Postgres here keeps the demo
self-contained and cheap. This is called out as a deliberate tradeoff, not an oversight.

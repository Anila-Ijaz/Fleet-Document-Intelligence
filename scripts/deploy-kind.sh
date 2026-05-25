#!/usr/bin/env bash
# Deploy the full stack to a LOCAL Kubernetes cluster using kind.
# Prereqs: docker, kind, kubectl. Set OPENAI_API_KEY in your environment or .env.
set -euo pipefail

CLUSTER=fleet-local
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load OPENAI_API_KEY from .env if present and not already set.
if [[ -z "${OPENAI_API_KEY:-}" && -f .env ]]; then
  export "$(grep -E '^OPENAI_API_KEY=' .env | xargs)"
fi
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY (env or .env) before deploying}"

echo "==> 1/6 Create kind cluster (if missing)"
if ! kind get clusters | grep -q "^${CLUSTER}$"; then
  kind create cluster --name "$CLUSTER"
fi

echo "==> 2/6 Install nginx ingress controller"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s || true

echo "==> 3/6 Build images"
docker build -t fleet/extraction:latest ./services/extraction
docker build -t fleet/rag:latest ./services/rag
docker build -t fleet/agent:latest ./services/agent
docker build -t fleet/frontend:latest ./frontend

echo "==> 4/6 Load images into kind"
for img in extraction rag agent frontend; do
  kind load docker-image "fleet/${img}:latest" --name "$CLUSTER"
done

echo "==> 5/6 Apply manifests + secret"
kubectl apply -f k8s/base/00-namespace-config.yaml
kubectl -n fleet create secret generic fleet-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/base/10-postgres.yaml
kubectl apply -f k8s/base/20-services.yaml
kubectl apply -f k8s/base/30-frontend-ingress.yaml

echo "==> 6/6 Wait for rollouts"
kubectl -n fleet rollout status deploy/extraction --timeout=120s
kubectl -n fleet rollout status deploy/rag --timeout=120s
kubectl -n fleet rollout status deploy/agent --timeout=120s
kubectl -n fleet rollout status deploy/frontend --timeout=120s

echo ""
echo "Done. The app is reachable via the ingress at http://localhost"
echo "Inspect with:  kubectl -n fleet get pods,svc,ingress"
echo "Tear down with: kind delete cluster --name ${CLUSTER}"

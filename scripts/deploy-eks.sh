#!/usr/bin/env bash
# Build images and push them to AWS ECR, then point the k8s manifests at ECR.
# Prereqs: aws cli (configured), docker, an existing EKS cluster + kubectl context.
#
# COST WARNING: an EKS cluster costs ~$0.10/hr for the control plane plus EC2/Fargate
# for nodes — roughly a few USD per day. Tear it down when done (see eks-teardown.sh).
set -euo pipefail

: "${AWS_REGION:=eu-central-1}"          # Frankfurt - close to a German employer
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> 1/5 Ensure ECR repositories exist"
for repo in fleet/extraction fleet/rag fleet/agent fleet/frontend; do
  aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" >/dev/null 2>&1 \
    || aws ecr create-repository --repository-name "$repo" --region "$AWS_REGION" >/dev/null
done

echo "==> 2/5 Log in to ECR"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "==> 3/5 Build, tag, and push images"
for svc in extraction rag agent; do
  docker build -t "${REGISTRY}/fleet/${svc}:latest" "./services/${svc}"
  docker push "${REGISTRY}/fleet/${svc}:latest"
done
docker build -t "${REGISTRY}/fleet/frontend:latest" ./frontend
docker push "${REGISTRY}/fleet/frontend:latest"

echo "==> 4/5 Apply manifests with ECR image references"
# Rewrite the local image names to ECR on the fly (sed), then apply.
kubectl apply -f k8s/base/00-namespace-config.yaml
kubectl -n fleet create secret generic fleet-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/base/10-postgres.yaml

for f in k8s/base/20-services.yaml k8s/base/30-frontend-ingress.yaml; do
  sed "s#image: fleet/#image: ${REGISTRY}/fleet/#g" "$f" | kubectl apply -f -
done

echo "==> 5/5 Wait for rollouts"
for d in extraction rag agent frontend; do
  kubectl -n fleet rollout status "deploy/$d" --timeout=180s
done

echo ""
echo "Deployed to EKS. Get the load balancer URL with:"
echo "  kubectl -n fleet get ingress fleet-ingress"
echo "REMEMBER to tear down the cluster when finished: ./scripts/eks-teardown.sh"

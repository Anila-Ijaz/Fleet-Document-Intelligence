#!/usr/bin/env bash
# Tear down the EKS deployment to stop incurring costs.
# This removes the app and (optionally) the cluster created with eksctl.
set -euo pipefail

: "${AWS_REGION:=eu-central-1}"
CLUSTER="${EKS_CLUSTER_NAME:-fleet-eks}"

echo "==> Deleting app resources from namespace 'fleet'"
kubectl delete namespace fleet --ignore-not-found

echo ""
read -r -p "Also delete the entire EKS cluster '${CLUSTER}'? This stops ALL charges. [y/N] " ans
if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
  echo "==> Deleting EKS cluster (this takes ~10-15 min)"
  eksctl delete cluster --name "$CLUSTER" --region "$AWS_REGION"
  echo "Cluster deleted. You are no longer being billed for it."
else
  echo "Cluster left running. NOTE: the control plane still costs ~\$0.10/hr."
fi

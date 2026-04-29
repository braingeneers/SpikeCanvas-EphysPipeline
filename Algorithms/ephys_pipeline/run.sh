#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TAG:-}" ]]; then
  echo "Error: TAG environment variable is not set. Example: TAG=v0.78 ./run.sh" >&2
  exit 1
fi

make ephys-build TAG="${TAG}"
make ephys-push TAG="${TAG}"

kubectl delete job sjg-simplified-r2 || true
sleep 5
kubectl create -f run_kilosort2.yaml
sleep 5
watch "kubectl get pods | grep sjg"

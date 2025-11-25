#!/usr/bin/env bash
kubectl delete job sjg-simplified-r2
sleep 5
docker build -f docker/Dockerfile -t surygeng/ephys_pipeline:v0.1 .
sleep 2
docker push surygeng/ephys_pipeline:v0.1
sleep 2
kubectl create -f run_kilosort2.yaml
sleep 5
watch "kubectl get pods | grep sjg"
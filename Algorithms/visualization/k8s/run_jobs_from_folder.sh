#!/bin/bash

# Directory containing the job YAML files
JOB_DIR="visualization_jobs_autocuration"

# Apply all job YAML files
# go through the directory and create a job for each file
for file in $JOB_DIR/*.yaml; do
    # Extract the job name from the filename
    job_name=$(basename "$file" .yaml)
    
    # Create a job using the YAML file
    kubectl create -f "$file"
    
    # Check if the job was created successfully
    if [ $? -eq 0 ]; then
        echo "Job $job_name created successfully."
    else
        echo "Failed to create job $job_name."
    fi
done
# kubectl apply -f $JOB_DIR

# # Function to check job status
# check_job_status() {
#     kubectl get jobs -o custom-columns=NAME:.metadata.name,STATUS:.status.succeeded
# }

# # Function to clean up completed jobs
# clean_up_jobs() {
#     kubectl delete jobs --field-selector status.successful=1
# }

# # Monitor job progress
# echo "Monitoring job progress. Press Ctrl+C to stop monitoring."
# while true; do
#     check_job_status
#     sleep 30  # Check every 30 seconds
# done

# Note: After the script finishes or you stop it, you may want to run:
# clean_up_jobs
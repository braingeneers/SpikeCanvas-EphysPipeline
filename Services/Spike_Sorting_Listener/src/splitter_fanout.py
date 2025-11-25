###############################################################################
# splitter_fanout.py
#  – Submit *one* splitter Job
#  – Background thread watches it; when Succeeded → fan-out 6 sorter Jobs
#  – Uses mqtt_listener.format_job_name so all Job names are K8s-safe
###############################################################################
from kubernetes import client, config
from k8s_kilosort2 import Kube
import threading, time, os, logging
import traceback

# import shared utilities
from job_utils import format_job_name, JOB_PREFIX, NAMESPACE, DEFAULT_S3_BUCKET

# Note: Removed module-level kube config loading to avoid connection sharing issues

def spawn_splitter_fanout(uuid: str,
                          experiment: str,
                          splitter_cfg: dict,
                          sorter_tpl: dict):
    """Submit splitter Job + start a watcher thread."""
    logging.info(f"=== spawn_splitter_fanout called ===")
    logging.info(f"Parameters - UUID: {uuid}, Experiment: {experiment}")
    
    # Input validation
    if not uuid or not experiment:
        raise ValueError(f"UUID and experiment must be provided: uuid='{uuid}', experiment='{experiment}'")
    
    if not splitter_cfg or not sorter_tpl:
        raise ValueError("splitter_cfg and sorter_tpl must be provided")
    
    # Validate required fields in configs
    required_splitter_fields = ['args', 'cpu_request', 'memory_request', 'disk_request', 'GPU', 'image']
    missing_fields = [field for field in required_splitter_fields if field not in splitter_cfg]
    if missing_fields:
        raise ValueError(f"Missing required fields in splitter_cfg: {missing_fields}")
    
    try:
        base_exp = experiment.replace(".raw.h5", "").replace(".h5", "")
        split_raw   = f"{base_exp}-split"
        split_name  = format_job_name(split_raw, prefix=JOB_PREFIX)

        logging.info(f"Creating splitter job with name: {split_name}")
        logging.info(f"Base experiment: {base_exp}")
        logging.info(f"UUID: {uuid}")

        # -------- create splitter Job if missing ----------------------------
        # Prepare config with all required fields
        cfg = splitter_cfg.copy()
        cfg.update({"uuid": uuid, "experiment": experiment})
        
        # Create Kube object once for efficiency
        splitter_job = Kube(split_name, cfg)
        
        if not splitter_job.check_job_exist():
            logging.info(f"Splitter config: {cfg}")
            
            job_result = splitter_job.create_job()
            if job_result == -1:
                logging.error(f"Failed to create splitter job {split_name}")
                return
            
            logging.info(f"Splitter Job {split_name} submitted successfully")
            job_created = True
        else:
            logging.info(f"Splitter Job {split_name} already exists")
            job_created = False

        # Only start watcher if we have a job to watch
        # CRITICAL: The watcher thread is the ONLY way sorter jobs get created
        # Sorter jobs will NOT be created until splitter succeeds
        # background watcher (non-daemon to ensure logging works)
        watcher_thread = threading.Thread(
            target=_watch_and_fanout,
            name=f"fanout-{base_exp}",
            args=(split_name, uuid, experiment, sorter_tpl, job_created),
            daemon=False  # Changed to False to ensure proper logging
        )
        watcher_thread.start()
        logging.info(f"Started watcher thread for job {split_name}")
        logging.info(f"NOTE: Sorter jobs will be created ONLY after splitter {split_name} succeeds")
        
    except Exception as e:
        logging.error(f"Error in spawn_splitter_fanout: {e}")
        raise

# ---------------------------------------------------------------- internals
def _safe_get_job_status(job_name, max_retries=3, retry_delay=5):
    """Safely get job status with retries and connection management."""
    for attempt in range(max_retries):
        try:
            # Create fresh API client and config for each attempt
            # This helps avoid connection state issues and InvalidChunkLength errors
            config.load_kube_config()
            api = client.BatchV1Api()
            
            # Add timeout to the API call to prevent hanging
            job = api.read_namespaced_job_status(
                name=job_name, 
                namespace=NAMESPACE,
                _request_timeout=30  # 30 second timeout
            )
            return job.status
            
        except Exception as e:
            error_msg = str(e)
            # Log different types of errors with appropriate levels
            if "InvalidChunkLength" in error_msg or "Connection broken" in error_msg:
                logging.warning(f"Connection error for job {job_name} (attempt {attempt + 1}/{max_retries}): {error_msg}")
            else:
                logging.warning(f"API error for job {job_name} (attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            # If this is the last attempt, log the error and return None
            if attempt == max_retries - 1:
                logging.error(f"Failed to get status for job {job_name} after {max_retries} attempts: {error_msg}")
                return None
            
            # Progressive backoff: wait longer after each failure
            delay = retry_delay * (attempt + 1)
            logging.info(f"Waiting {delay}s before retry...")
            time.sleep(delay)
            
    return None

def _watch_and_fanout(split_name, uuid_param, experiment, tpl, job_created=True):
    """Watch splitter job and fan out sorter jobs when complete."""
    try:
        logging.info(f"Starting watcher for splitter job: {split_name} (job_created={job_created})")
        
        # Poll-based approach with robust error handling
        max_wait_time = 7200  # 2 hour timeout (extended for large MaxTwo files)
        poll_interval = 30    # Check every 30 seconds
        elapsed_time = 0
        consecutive_errors = 0
        max_consecutive_errors = 10  # Increased from 5 to handle more transient errors
        
        # If job already existed, check if it's already completed first
        if not job_created:
            try:
                job_status = _safe_get_job_status(split_name)
                if job_status is None:
                    logging.error(f"Could not get initial status for {split_name}")
                    return
                
                if job_status.succeeded and job_status.succeeded > 0:
                    logging.info(f"[{split_name}] Already completed → fan-out sorters")
                    _launch_sorters(uuid_param, experiment, tpl)
                    return
                elif job_status.failed and job_status.failed >= 2:
                    logging.error(f"[{split_name}] Already failed; skip sorters")
                    return
                    
                logging.info(f"[{split_name}] Existing job is still running, starting monitoring")
                    
            except Exception as check_err:
                logging.error(f"Error checking existing job status: {check_err}")
                logging.info(f"Will proceed with normal monitoring for {split_name}")
        
        while elapsed_time < max_wait_time:
            try:
                # Use safe status retrieval with built-in retry logic
                job_status = _safe_get_job_status(split_name, max_retries=2, retry_delay=3)
                
                if job_status is None:
                    consecutive_errors += 1
                    logging.warning(f"Failed to get job status for {split_name} (consecutive errors: {consecutive_errors})")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logging.error(f"Too many consecutive errors ({consecutive_errors}), giving up on {split_name}")
                        return
                    
                    # Progressive backoff for consecutive errors - wait longer each time
                    backoff_delay = min(poll_interval * consecutive_errors, 120)  # Cap at 2 minutes
                    logging.info(f"Backing off for {backoff_delay}s due to consecutive errors")
                    time.sleep(backoff_delay)
                    elapsed_time += backoff_delay
                    continue
                
                # Reset error counter on successful API call
                consecutive_errors = 0
                
                logging.info(f"Job {split_name} status check: succeeded={job_status.succeeded}, failed={job_status.failed}, active={job_status.active}")
                
                if job_status.succeeded and job_status.succeeded > 0:
                    logging.info(f"[{split_name}] Succeeded → fan-out sorters")
                    logging.info(f"LAUNCHING SORTERS: Splitter {split_name} completed successfully")
                    _launch_sorters(uuid_param, experiment, tpl)
                    return  # Exit successfully
                    
                if job_status.failed and job_status.failed >= 2:
                    logging.error(f"[{split_name}] Failed {job_status.failed} times; skip sorters")
                    return  # Exit due to failure
                    
                # Job is still running, wait and check again
                logging.info(f"[{split_name}] Still running, waiting {poll_interval}s... ({elapsed_time}/{max_wait_time}s elapsed)")
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                
            except Exception as api_err:
                consecutive_errors += 1
                error_msg = str(api_err)
                logging.error(f"Unexpected error in monitoring loop for {split_name} (attempt {consecutive_errors}): {error_msg}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logging.error(f"Too many consecutive errors ({consecutive_errors}), giving up on {split_name}")
                    return
                
                # Wait before retry, but don't try to refresh config immediately on every error
                logging.info(f"Waiting {poll_interval}s before retry {consecutive_errors}/{max_consecutive_errors}")
                time.sleep(poll_interval)
                elapsed_time += poll_interval
        
        # Timeout reached
        logging.error(f"Timeout waiting for job {split_name} to complete after {max_wait_time}s")
        logging.error(f"Check job status manually: kubectl get job {split_name} -n {NAMESPACE}")
            
    except Exception as e:
        logging.error(f"Error in watcher for {split_name}: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
    finally:
        logging.info(f"Watcher thread for {split_name} ending")

def _launch_sorters(uuid_param, experiment, tpl):
    """Launch 6 sorter jobs for the split wells."""
    try:
        base_exp = experiment.replace(".raw.h5", "").replace(".h5", "")
        split_dir = os.path.join(DEFAULT_S3_BUCKET, uuid_param, "original/split")
        
        logging.info(f"Launching sorters for experiment: {base_exp}")
        logging.info(f"Split directory: {split_dir}")

        jobs_created = 0
        jobs_skipped = 0
        jobs_failed = 0
        failed_wells = []
        
        for i in range(6):
            well     = f"well{i:03d}"
            raw_path = os.path.join(split_dir, f"{base_exp}_{well}.raw.h5")

            info = tpl.copy()
            info["file_path"] = raw_path
            info["uuid"] = uuid_param
            info["experiment"] = f"{base_exp}_{well}"

            raw_job_name = f"{base_exp}-{well}"
            job_name     = format_job_name(raw_job_name, prefix=JOB_PREFIX)

            logging.info(f"Creating sorter job {job_name} for well {well}")
            logging.info(f"Well file path: {raw_path}")
            
            try:
                # Create Kube object once for efficiency
                kube_job = Kube(job_name, info)
                
                if not kube_job.check_job_exist():
                    job_result = kube_job.create_job()
                    if job_result == -1:
                        logging.error(f"Failed to create sorter job {job_name}")
                        jobs_failed += 1
                        failed_wells.append(well)
                    else:
                        logging.info(f"Sorter Job {job_name} created successfully")
                        jobs_created += 1
                        # Small delay between job creations to avoid overwhelming the API
                        time.sleep(0.1)
                else:
                    logging.info(f"Sorter job {job_name} already exists, skipping")
                    jobs_skipped += 1
                    
            except Exception as job_err:
                logging.error(f"Error creating sorter job {job_name}: {job_err}")
                jobs_failed += 1
                failed_wells.append(well)
                
        logging.info(f"Sorter job creation complete: {jobs_created} created, {jobs_skipped} skipped, {jobs_failed} failed")
        
        if jobs_failed > 0:
            logging.error(f"Failed wells: {', '.join(failed_wells)}")
            # Don't raise exception - partial success is still useful
            # raise Exception(f"Failed to create {jobs_failed} out of 6 sorter jobs")
        
        if jobs_created == 0 and jobs_skipped == 0:
            raise Exception("No sorter jobs were created or found - this indicates a serious problem")
                
    except Exception as e:
        logging.error(f"Error launching sorters: {e}")
        raise

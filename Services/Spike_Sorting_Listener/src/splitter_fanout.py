###############################################################################
# splitter_fanout.py
#  – Submit *one* splitter Job
#  – Background thread watches it; when Succeeded → fan-out 6 sorter Jobs
#  – Uses mqtt_listener.format_job_name so all Job names are K8s-safe
###############################################################################
from kubernetes import client, config
from k8s_kilosort2 import Kube
import threading, time, os, logging, posixpath
import re
import traceback
from urllib.parse import urlparse

import braingeneers.utils.s3wrangler as wr

# import shared utilities
from job_utils import format_job_name, JOB_PREFIX, NAMESPACE, CACHE_S3_BUCKET, DEFAULT_S3_BUCKET

SPLITTER_JOB_PREFIX = "edp-ma2split-"

# Note: Removed module-level kube config loading to avoid connection sharing issues

def spawn_splitter_fanout(uuid: str,
                          experiment: str,
                          file_path: str,
                          splitter_cfg: dict,
                          sorter_tpl: dict):
    """Submit splitter Job + start a watcher thread."""
    logging.info(f"=== spawn_splitter_fanout called ===")
    logging.info(f"Parameters - UUID: {uuid}, Experiment: {experiment}")
    
    # Input validation
    if not uuid or not experiment or not file_path:
        raise ValueError("UUID, experiment, and file_path must be provided")
    
    if not splitter_cfg or not sorter_tpl:
        raise ValueError("splitter_cfg and sorter_tpl must be provided")
    
    # Validate required fields in configs
    required_splitter_fields = [
        'args', 'cpu_request', 'memory_request', 'disk_request', 'GPU', 'image',
        'init_args', 'init_cpu_request', 'init_memory_request', 'init_disk_request', 'init_GPU'
    ]
    missing_fields = [field for field in required_splitter_fields if field not in splitter_cfg]
    if missing_fields:
        raise ValueError(f"Missing required fields in splitter_cfg: {missing_fields}")
    
    try:
        base_exp = _normalize_experiment_name(experiment)
        split_name = _build_splitter_job_name(uuid, base_exp)

        logging.info(f"Creating splitter job with name: {split_name}")
        logging.info(f"Base experiment: {base_exp}")
        logging.info(f"UUID: {uuid}")

        # -------- create splitter Job if missing ----------------------------
        # Prepare config with all required fields
        cfg = splitter_cfg.copy()
        cfg.update({
            "file_path": file_path,
            "init_container": {
                "name": "maxtwo-download",
                "image": splitter_cfg["image"],
                "args": f"{splitter_cfg['init_args']} {file_path}",
                "cpu_request": splitter_cfg["init_cpu_request"],
                "memory_request": splitter_cfg["init_memory_request"],
                "disk_request": splitter_cfg["init_disk_request"],
                "GPU": splitter_cfg["init_GPU"],
            },
        })
        
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
            args=(split_name, uuid, experiment, file_path, sorter_tpl, job_created),
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

def _watch_and_fanout(split_name, uuid_param, experiment, file_path, tpl, job_created=True):
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
                    _launch_sorters(uuid_param, experiment, file_path, tpl)
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
                    _launch_sorters(uuid_param, experiment, file_path, tpl)
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

def _launch_sorters(uuid_param, experiment, file_path, tpl):
    """Launch sorter jobs after splitter completes."""
    try:
        base_exp = _normalize_experiment_name(experiment)
        cache_uuid = _normalize_uuid_for_cache(uuid_param)
        split_dir = posixpath.join(CACHE_S3_BUCKET, cache_uuid, "original/data")
        legacy_split_dir = posixpath.join(CACHE_S3_BUCKET, cache_uuid, "original/split")

        logging.info(f"Launching sorters for experiment: {base_exp}")
        if cache_uuid != uuid_param:
            logging.info(f"Normalized cache UUID from {uuid_param} to {cache_uuid}")
        logging.info(f"Cache directory: {split_dir}")

        split_files = _list_split_files(split_dir, base_exp)
        if not split_files and legacy_split_dir != split_dir:
            logging.info("No split files in cache data path; checking legacy split path")
            split_files = _list_split_files(legacy_split_dir, base_exp)
            if split_files:
                logging.info(f"Found {len(split_files)} split files in legacy path for {base_exp}")

        if split_files:
            logging.info(f"Found {len(split_files)} split files for {base_exp}")
            _launch_split_sorters(uuid_param, base_exp, split_files, tpl)
        else:
            logging.info("No split files found; launching single sorter job")
            _launch_single_sorter(uuid_param, experiment, file_path, tpl)
                
    except Exception as e:
        logging.error(f"Error launching sorters: {e}")
        raise


def _normalize_uuid_for_cache(uuid_param: str) -> str:
    if not uuid_param:
        return uuid_param
    if uuid_param.startswith("s3://"):
        if uuid_param.startswith(DEFAULT_S3_BUCKET):
            raw_uuid = uuid_param[len(DEFAULT_S3_BUCKET):]
            return raw_uuid.strip("/")
        parsed = urlparse(uuid_param)
        key = parsed.path.lstrip("/")
        for prefix in ("ephys/", "integrated/", "fluidics/"):
            if key.startswith(prefix):
                key = key[len(prefix):]
                break
        return key.strip("/")
    return uuid_param.strip("/")


def _list_split_files(split_dir: str, base_exp: str):
    try:
        candidates = wr.list_objects(split_dir)
    except Exception as err:
        logging.warning(f"Could not list split directory {split_dir}: {err}")
        return []

    base_name = posixpath.basename(base_exp)
    prefixes = {f"{base_exp}_well"}
    if base_name != base_exp:
        prefixes.add(f"{base_name}_well")

    split_files = []
    for path in candidates:
        name = posixpath.basename(path)
        if not (name.endswith(".raw.h5") or name.endswith(".h5")):
            continue
        if any(name.startswith(prefix) for prefix in prefixes):
            match = re.search(r"_well(\d{3})", name)
            if match and int(match.group(1)) < 1:
                continue
            split_files.append(path)
    return sorted(split_files)


def _normalize_experiment_name(experiment: str) -> str:
    """Strip trailing .raw.h5/.h5 suffixes (including repeated .raw.h5)."""
    base = experiment or ""
    while base.endswith(".raw.h5"):
        base = base[:-len(".raw.h5")]
    if base.endswith(".h5"):
        base = base[:-len(".h5")]
    return base


def _sanitize_job_fragment(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return cleaned or "x"


def _build_well_job_name(uuid_param: str, base_exp: str, well_id: str,
                         prefix: str = JOB_PREFIX, max_len: int = 63) -> str:
    """Build a job name that preserves UUID prefix and well id (front-heavy)."""
    well_part = _sanitize_job_fragment(well_id)
    uuid_part = _sanitize_job_fragment(_normalize_uuid_for_cache(uuid_param))
    if uuid_part == "x":
        uuid_part = _sanitize_job_fragment(base_exp)
    if uuid_part == "x":
        uuid_part = "data"

    # Leave room for prefix + '-' + well id
    keep = max_len - len(prefix) - len(well_part) - 1
    if keep < 1:
        return format_job_name(well_part, prefix=prefix, max_len=max_len)

    uuid_part = uuid_part[:keep]
    return f"{prefix}{uuid_part}-{well_part}"


def _build_splitter_job_name(uuid_param: str, base_exp: str,
                             prefix: str = SPLITTER_JOB_PREFIX, max_len: int = 63) -> str:
    """Build a splitter job name that preserves the UUID prefix."""
    uuid_part = _sanitize_job_fragment(_normalize_uuid_for_cache(uuid_param))
    if uuid_part == "x":
        uuid_part = _sanitize_job_fragment(base_exp)
    if uuid_part == "x":
        uuid_part = "data"

    keep = max_len - len(prefix)
    if keep < 1:
        return format_job_name(base_exp, prefix=prefix, max_len=max_len)

    return f"{prefix}{uuid_part[:keep]}"


def _launch_split_sorters(uuid_param, base_exp, split_files, tpl):
    jobs_created = 0
    jobs_skipped = 0
    jobs_failed = 0
    failed_wells = []

    for raw_path in split_files:
        well_id = posixpath.basename(raw_path)
        well_id = well_id.replace(".raw.h5", "").replace(".h5", "")
        well_id = well_id.split(f"{base_exp}_", 1)[-1]

        info = tpl.copy()
        info["file_path"] = raw_path
        info["uuid"] = uuid_param
        info["experiment"] = f"{base_exp}_{well_id}"

        job_name = _build_well_job_name(uuid_param, base_exp, well_id, max_len=56)

        logging.info(f"Creating sorter job {job_name} for well {well_id}")
        logging.info(f"Well file path: {raw_path}")

        try:
            kube_job = Kube(job_name, info)
            if not kube_job.check_job_exist():
                job_result = kube_job.create_job()
                if job_result == -1:
                    logging.error(f"Failed to create sorter job {job_name}")
                    jobs_failed += 1
                    failed_wells.append(well_id)
                else:
                    logging.info(f"Sorter Job {job_name} created successfully")
                    jobs_created += 1
                    time.sleep(0.1)
            else:
                logging.info(f"Sorter job {job_name} already exists, skipping")
                jobs_skipped += 1
        except Exception as job_err:
            logging.error(f"Error creating sorter job {job_name}: {job_err}")
            jobs_failed += 1
            failed_wells.append(well_id)

    logging.info(f"Sorter job creation complete: {jobs_created} created, {jobs_skipped} skipped, {jobs_failed} failed")
    if jobs_failed > 0:
        logging.error(f"Failed wells: {', '.join(failed_wells)}")
    if jobs_created == 0 and jobs_skipped == 0:
        raise Exception("No sorter jobs were created or found - this indicates a serious problem")


def _launch_single_sorter(uuid_param, experiment, file_path, tpl):
    info = tpl.copy()
    info["file_path"] = file_path
    info["uuid"] = uuid_param
    info["experiment"] = experiment.replace(".raw.h5", "").replace(".h5", "")

    job_name = format_job_name(info["experiment"], prefix=JOB_PREFIX)
    logging.info(f"Creating sorter job {job_name} for {file_path}")
    kube_job = Kube(job_name, info)
    if not kube_job.check_job_exist():
        job_result = kube_job.create_job()
        if job_result == -1:
            raise Exception(f"Failed to create sorter job {job_name}")
        logging.info(f"Sorter Job {job_name} created successfully")
    else:
        logging.info(f"Sorter job {job_name} already exists, skipping")

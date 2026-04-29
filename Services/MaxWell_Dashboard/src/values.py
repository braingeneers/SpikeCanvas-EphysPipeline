####---- default values that shared between scripts ----####
TOPIC = "service/csv_job"

TABLE_HEADERS = ["index", "status", "uuid", "experiment",
                 "image", "args", "params", "cpu_request",
                 "memory_request", "disk_request",
                 "GPU", "next_job"]

LOCAL_CSV = "jobs.csv"

SERVICE_BUCKET = "s3://braingeneers/services/mqtt_job_listener/csvs"

PARAMETER_BUCKET = "s3://braingeneers/services/mqtt_job_listener/params"

DEFAULT_BUCKET = "s3://braingeneers/ephys/"

JOB_PREFIX = "edp-"  # electrophysiology

NAMESPACE = 'braingeneers'

FINISH_FLAGS = ["Succeeded", "Failed", "Unknown"]

# Define the parameters for each job
JOB_PARAMETERS = {
    0: ["parameter not yet available"],
    1: ["parameter not yet available"],
    2: ["Minimum SNR (rms)", 
        "Minimum Firing Rate (Hz)", 
        "Maximum ISI Violation (/1)"],
    3: ["parameter not yet available"],
    4: ["Raster Bin Size (seconds)", 
        "Cross-correlogram Window (ms)", 
        "Maximum Functional Latency (ms)",
        "Maximum Poisson p Value"],
    5: ["Analysis Start Time (seconds)", 
        "Analysis End Time (seconds)"]
}

CONVERT_TO_READABLE = {
        "min_fr": "Minimum Firing Rate (Hz)",
        "min_snr": "Minimum SNR (rms)",
        "max_isi_viol": "Maximum ISI Violation (/1)",
        "binary_bin_size": "Raster Bin Size (seconds)",
        "ccg_win": "Cross-correlogram Window (ms)",
        "func_latency": "Maximum Functional Latency (ms)",
        "p_test": "Maximum Poisson p Value",
        "start_time": "Analysis Start Time (seconds)",
        "end_time": "Analysis End Time (seconds)",
    }

CONVERT_TO_JSON = {
    "Minimum Firing Rate (Hz)": "min_fr",
    "Minimum SNR (rms)": "min_snr",
    "Maximum ISI Violation (/1)": "max_isi_viol",
    "Raster Bin Size (seconds)": "binary_bin_size",
    "Cross-correlogram Window (ms)": "ccg_win",
    "Maximum Functional Latency (ms)": "func_latency",
    "Maximum Poisson p Value": "p_test",
    "Analysis Start Time (seconds)": "start_time",
    "Analysis End Time (seconds)": "end_time",
}

DEFAULT_JOBS = {"batch":
                    {"image": "braingeneers/ephys_pipeline:v0.78",
                     "args": "./run.sh",
                     "cpu_request": 12,
                     "memory_request": 32,
                     "disk_request": 400,
                     "GPU": 1,
                     "params_label": "pipeline",
                     "next_job": "None"
                     },
                "chained": {
                    0: {"image": "braingeneers/ephys_pipeline:v0.78",  # for running individual recording
                        "args": "./run.sh",
                        "cpu_request": 12,
                        "memory_request": 32,
                        "disk_request": 400,
                        "GPU": 1,
                        "params_label": "pipeline",
                        "next_job": "None"},
                    2: {"image": "surygeng/qm_curation:v0.2",
                        "args": "python si_curation.py",
                        "cpu_request": 8,
                        "memory_request": 32,
                        "disk_request": 400,
                        "GPU": 0,
                        "params_label": "curation",
                        "next_job": "None"},
                    3: {"image": "surygeng/visualization:v0.1",
                        "args": "python viz.py",
                        "cpu_request": 2,
                        "memory_request": 16,
                        "disk_request": 8,
                        "GPU": 0,
                        "params_label": "visualization",
                        "next_job": "None"},
                    4: {"image": "surygeng/connectivity:v0.1",
                        "args": "python run_conn.py",
                        "cpu_request": 2,
                        "memory_request": 16,
                        "disk_request": 8,
                        "GPU": 0,
                        "params_label": "connectivity",
                        "next_job": "None"},
                    5: {"image": "surygeng/local_field_potential:v0.1",
                        "args": "python run_lfp.py",  # Parameters: start_time, end_time (in seconds)
                        "cpu_request": 4,
                        "memory_request": 64,
                        "disk_request": 64,
                        "GPU": 0,
                        "params_label": "lfp",
                        "next_job": "None"},
                }
                }

IMG_JOB_LOOPUP = {
    "surygeng/connectivity:v0.1": "Functional Connectivity Analysis",
    "braingeneers/ephys_pipeline:v0.78": "Ephys Pipeline (Kilosort2, Auto-Curation, Visualization)",
    "surygeng/local_field_potential:v0.1": "Local Field Potential Subbands",
    "surygeng/qm_curation:v0.2": "Auto-Curation by Quality Metrics",
    "surygeng/visualization:v0.1": "Visualization"
}

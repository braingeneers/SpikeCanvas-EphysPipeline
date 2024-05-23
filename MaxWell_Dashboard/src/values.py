####---- default values that shared between scripts ----####
TOPIC = "service/csv_job"

TABLE_HEADERS = ["index", "status", "uuid", "experiment",
                 "image", "args", "cpu_request",
                 "memory_request", "disk_request",
                 "GPU", "next_job"]

LOCAL_CSV = "jobs.csv"

SERVICE_BUCKET = "s3://braingeneers/services/mqtt_job_listener/csvs"

DEFAULT_BUCKET = "s3://braingeneers/ephys/"

DEFAULT_JOBS = {"batch":
                    {"image": "surygeng/ephys_pipeline:v0.1",
                     "args": "./run.sh",
                     "cpu_request": 12,
                     "memory_request": 32,
                     "disk_request": 400,
                     "GPU": 1,
                     "next_job": "None"
                     },
                "chained": {
                    0: {"image": "surygeng/ephys_pipeline:v0.1",  # for running individual recording
                        "args": "./run.sh",
                        "cpu_request": 12,
                        "memory_request": 32,
                        "disk_request": 400,
                        "GPU": 1,
                        "next_job": "None"},
                    1: {"image": "surygeng/kilosort_docker:v0.2",
                        "args": "./run.sh",
                        "cpu_request": 12,
                        "memory_request": 32,
                        "disk_request": 400,
                        "GPU": 1,
                        "next_job": "None"},
                    2: {"image": "surygeng/qm_curation:v0.2",
                        "args": "python si_curation.py",
                        "cpu_request": 8,
                        "memory_request": 32,
                        "disk_request": 200,
                        "GPU": 0,
                        "next_job": "None"},
                    3: {"image": "surygeng/visualization:v0.1",
                        "args": "python viz.py",
                        "cpu_request": 2,
                        "memory_request": 16,
                        "disk_request": 8,
                        "GPU": 0,
                        "next_job": "None"},
                    4: {"image": "surygeng/connectivity:v0.1",
                        "args": "python run_conn.py",
                        "cpu_request": 2,
                        "memory_request": 16,
                        "disk_request": 8,
                        "GPU": 0,
                        "next_job": "None"},
                    5: {"image": "surygeng/local_field_potential:v0.1",
                        "args": "python run_lfp.py",  # TODO implement this command because right not it's different to the one in the container. 
                        "cpu_request": 4,
                        "memory_request": 64,
                        "disk_request": 64,
                        "GPU": 0,
                        "next_job": "None"},
                }
                }

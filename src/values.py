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
                    {"image": "surygeng/kilosort_docker:latest",
                     "args": "./run.sh",
                     "cpu_request": 12,
                     "memory_request": 32,
                     "disk_request": 400,
                     "GPU": 1,
                     "next_job": "None"
                     },
                "chained": {}
                }


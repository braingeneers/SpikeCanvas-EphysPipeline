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
                "chained": {
                    0: {"image": "surygeng/kilosort_docker:latest",
                        "args": "./run.sh",
                        "cpu_request": 12,
                        "memory_request": 32,
                        "disk_request": 400,
                        "GPU": 1,
                        "next_job": "None"},
                    1: {"image": "surygeng/kilosort2:0.1",
                        "args": "./run.sh",
                        "cpu_request": 12,
                        "memory_request": 32,
                        "disk_request": 400,
                        "GPU": 1,
                        "next_job": "None"},
                    2: {"image": "surygeng/qm_curation:latest",
                        "args": "python si_curation.py",
                        "cpu_request": 8,
                        "memory_request": 32,
                        "disk_request": 500,
                        "GPU": 0,
                        "next_job": "None"},
                    3: {"image": "surygeng/visual_step1:latest",
                        "args": "python make_figures.py",
                        "cpu_request": 2,
                        "memory_request": 16,
                        "disk_request": 100,
                        "GPU": 0,
                        "next_job": "None"},
                    4: {"image": "surygeng/fancy_analysis:latest",
                        "args": "python fancy.py",
                        "cpu_request": 4,
                        "memory_request": 32,
                        "disk_request": 200,
                        "GPU": 0,
                        "next_job": "None"}
                }
                }

from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.utils.smart_open_braingeneers as smart_open
import braingeneers.utils.s3wrangler as wr
from tenacity import retry, stop_after_attempt
import csv
import os
import time
from datetime import datetime
import numpy as np


TOPIC = "services/csv_job"
SERVICE_BUCKET = "s3://braingeneers/services/mqtt_job_listener/csvs"
DEFAULT_BUCKET = "s3://braingeneers/ephys/"
TABLE_HEADERS = ["index", "status", "uuid", "experiment",
                 "image", "args", "params", "cpu_request",
                 "memory_request", "disk_request",
                 "GPU", "next_job"]
DEFAULT_JOBS = {"chained": 
                    {3: {"image": "surygeng/visualization:v0.1",
                        "args": "python viz.py",
                        "cpu_request": 2,
                        "memory_request": 16,
                        "disk_request": 8,
                        "GPU": 0,
                        "param_label": "visualization",
                        "next_job": "None"}
                    }
                }

@retry(stop=stop_after_attempt(5))
def upload_to_s3(file, s3_path):
    try:
        with smart_open.open(s3_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=TABLE_HEADERS)
            writer.writeheader()
            for row in file:
                writer.writerow(row)
        return None
    except Exception as err:
        print(err)
        return f"Uploading file to s3 failed, please try later. {err}"

def create_csv_message(uuid, selected_files, job=3):
    rows = []
    job_index = []
    # uuid = f"s3://braingeneers/ephys/{uuid}derived/kilosort2/"
    uuid = f"s3://braingeneers/ephys/{uuid}derived/autocuration/"
    for j in range(len(selected_files)):
        file = selected_files[j]
        job_info = dict.fromkeys(TABLE_HEADERS)
        job_info["index"] = j+1
        job_info["status"] = "ready"
        job_info["uuid"] = uuid
        job_info["experiment"] = file
        for k, v in DEFAULT_JOBS["chained"][job].items():
            if k == "param_label":
                job_info["params"] = v
            else:
                job_info[k] = v
        rows.append(job_info)  
        job_index.append(j+1)   
    # save to csv on s3
    # print(f"DUBGGING, rows: {rows}")
    now = datetime.now()
    curr_dt_csv = now.strftime("%Y%m%d%H%M%S") + '.csv'
    s3_csv_path = os.path.join(SERVICE_BUCKET, curr_dt_csv)
    msg = upload_to_s3(rows, s3_csv_path)
    if msg is not None:
        print(msg)
        message = None
    else:
        message = {"csv": s3_csv_path,
                   "update": {"Start": job_index},
                   "refresh": False
                }
    return message

if __name__ == '__main__':
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))

    print("############### Welcome to Braingeneers Electrophysiology Data Pipeline: Visualization ###############")
    print(f"Default bucket: {DEFAULT_BUCKET}")

    # Let user input uuid, and file label
    data_path = None
    uuid = None
    get_uuid = True
    get_label = True

    while get_uuid:
        uuid = input("Please enter a UUID: ")
        uuid = "".join(uuid.split())
        print("Checking sorted files in this UUID ... ")
        if uuid.endswith("/"):
            s3_path = os.path.join(DEFAULT_BUCKET, uuid)
        else:
            uuid += "/"
            s3_path = os.path.join(DEFAULT_BUCKET, uuid)
        if os.path.join(s3_path, "derived/") in wr.list_directories(s3_path):
            # data_path = os.path.join(s3_path, "derived/kilosort2/")
            data_path = os.path.join(s3_path, "derived/autocuration/")
            files = wr.list_objects(data_path)
            print(f"Found {len(files)} files.")
            for f in files:
                print(f)
            get_uuid = False
        else:
            print("No available files. Please input another UUID")
    
    file_list = wr.list_objects(data_path)
    # file_name = [f.split("/kilosort2/")[1] for f in file_list]
    file_name = [f.split("/autocuration/")[1] for f in file_list]

    selected_files = []
    # get file label
    while get_label:
        file_label = input("Please enter the file label: ")
        for f in file_name:
            if file_label in f and "figure.zip" not in f:
                selected_files.append(f)
                get_label = False
        if len(selected_files) == 0:
            print("No file match this label. Please input another file label")

    # create message
    print(f"Selected {len(selected_files)} files.")
    for f in selected_files:
        print(f)
    print(f"Getting ready for sending message to {TOPIC} topic ...")
    message = create_csv_message(uuid, selected_files)
    if message is not None:
        # print(f"DUBEGGING, message is not sent. Message: {message}")
        mb.publish_message(topic=TOPIC, message=message, confirm_receipt=True)
        time.sleep(.01)
        print(f"Sent {message} to {TOPIC} topic for plotting {len(selected_files)} files.")
        print("############### Thank You ###############")
    else:
        print("Failed to send message to topic, please try again later.")
        print("############### Thank You ###############")

from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.data.datasets_electrophysiology as ephys
import braingeneers.utils.smart_open_braingeneers as smart_open
import argparse
import braingeneers.utils.s3wrangler as wr
import os
from datetime import datetime
import pandas as pd
from tenacity import retry, stop_after_attempt
import csv
import time

TOPIC = "services/csv_job"
DEFAULT_BUCKET = "s3://braingeneers/ephys"
INTEGRATED_BUCKET = "s3://braingeneers/integrated"
PARAMETER_BUCKET = "s3://braingeneers/services/mqtt_job_listener/params"
SERVICE_BUCKET = "s3://braingeneers/services/mqtt_job_listener/csvs"
TABLE_HEADERS = ["index", "status", "uuid", "experiment",
                 "image", "args", "params", "cpu_request",
                 "memory_request", "disk_request",
                 "GPU", "next_job"]
CURATION_JOB_INFO = {"image": "surygeng/qm_curation:v0.3",
                    "args": "python si_curation.py",
                    "cpu_request": 8,
                    "memory_request": 32,
                    "disk_request": 200,
                    "GPU": 0,
                    "params_label": "curation",
                    "next_job": "None"}

def load_hunter_csv(csv_path):
    data = pd.read_csv(csv_path)
    print(f"header {data.columns}")
    print(data)
    # take uuids only 
    # read experiments for each uuid from s3 because the csv does not have the extension of the experiment file 
    uuids = data["uuids"].unique()
    return uuids 

@retry(stop=stop_after_attempt(5))
def upload_to_s3(file, s3_path):
    """
    :param file: file content
    :param s3_path:
    :return:
    """
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

def mqtt_start_job(csv_path, job_index):
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    topic = "services/csv_job"
    message = {"csv": csv_path,
               "update": {"Start": job_index},
               "refresh": False
               }
    try:
        mb.publish_message(topic=topic, message=message, confirm_receipt=True)
        print("Sent message:", topic, message)
        time.sleep(.01)
        return None
    except Exception as err:
        return str(err)

## run curation for the hunter's uuids 
if __name__ == '__main__':
    integrated = True
    nwb = True
    csv_path = "/media/kang/Seagate_External/temp_data/Hunter/catalog_baseline.csv"
    params_file = "curation/params_params_low_ISI.json" 
    print(f"Apply parameter setting by this file {params_file}")

    
    if integrated:
        uuids = ["2024-05-24-efi-mouse-7plex-followup"] # ["2024-06-01-efi-mouse-feast"]
        chip_id = 24442 # 24522 # 24442 # 24645 # 24551 # 24522 # 24646 # "24442"  # "20402" # "19945" # "19944" # "19943" # "19894"
        S3_BUCKET = INTEGRATED_BUCKET
    else:
        uuids = load_hunter_csv(csv_path)
        chip_id = None
        S3_BUCKET = DEFAULT_BUCKET

    # generate a job run csv for all the uuids to run curation with the given parameter file  
    # create a csv file with the header
    job_csv = pd.DataFrame(columns=TABLE_HEADERS)
    job_csv_list = []
    job_index = 1
    for uuid in uuids:
        
        if integrated:
            uuid_csv = f"{S3_BUCKET}/{uuid}/ephys/"
            if nwb:
                data_path = f"{S3_BUCKET}/{uuid}/ephys/shared/{chip_id}/"
            else:
                data_path = f"{S3_BUCKET}/{uuid}/ephys/original/data/{chip_id}/"
        else:
            uuid_csv = f"{S3_BUCKET}/{uuid}/"
            data_path = f"{S3_BUCKET}/{uuid}/original/data/"

        recs = wr.list_objects(data_path)
        if nwb:
            exp_name = [exp.split("shared/")[1] for exp in recs]
        else:
            exp_name = [exp.split("data/")[1] for exp in recs]
        print(f"Data path {data_path} has {len(recs)} recordings.")
        for exp in exp_name:
            new_row = {"index": job_index,
                        "status": "ready", 
                        "uuid": uuid_csv, 
                        "experiment": exp, 
                        "image": CURATION_JOB_INFO["image"],
                        "args": CURATION_JOB_INFO["args"], 
                        "params": params_file,
                        "cpu_request": CURATION_JOB_INFO["cpu_request"],
                        "memory_request": CURATION_JOB_INFO["memory_request"],
                        "disk_request": CURATION_JOB_INFO["disk_request"],
                        "GPU": CURATION_JOB_INFO["GPU"], 
                        "next_job": CURATION_JOB_INFO["next_job"]}
            job_csv = pd.concat([job_csv, pd.DataFrame([new_row])],
                                ignore_index=True)
            job_csv_list.append(new_row)
            job_index += 1

    # save csv using current time stamp, upload to s3 and send a message to the listener
    
    now = datetime.now()
    curr_dt_csv = now.strftime("%Y%m%d%H%M%S") + '.csv'
    s3_path = os.path.join(SERVICE_BUCKET, curr_dt_csv)
    msg = upload_to_s3(job_csv_list, s3_path)
    if msg is None:
        print(f"Uploaded job csv to {s3_path}")
        job_index = [int(d['index']) for d in job_csv_list if d['next_job'] == "None"]
        msg_return = mqtt_start_job(s3_path, job_index)
        if msg_return is None:
            print("Sent job start message to listener")
        else:
            print(f"Failed to send job start message to listener {msg_return}")
    else:
        print(f"Failed to upload job csv to s3 {msg}")
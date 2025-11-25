from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
import numpy as np
import csv
import time

# send a csv job message 
def mqtt_start_job(csv_path, job_index):
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    topic = "services/csv_job"
    message = {"csv": csv_path,
               "update": {"Start": job_index},
               "refresh": False
               }

    mb.publish_message(topic=topic, message=message, confirm_receipt=True)
    print("Sent message:", topic, message)
    time.sleep(.01)

if __name__ == "__main__":
    ## generate csv file
    uuid = "2023-09-16-efi-mouse-5plex-official"
    chip_id = "19894"

    to_csv = {"index": [],
              "status": [],
              "uuid": [],
              "experiment": [],
              "file_path": [], # full path to the file to be processed
              "image": [],
              "args": [],
              "cpu_request": [],
              "memory_request": [],
              "disk_request": [],
              "GPU": [],
              "next_job": []}
    
    init_status = "ready"
    init_image = "surygeng/connectivity:v0.1"
    init_args =  "python run_conn.py" # s3://braingeneers/ephys/2024-01-18-e-P001515/derived/kilosort2/interneurons_20231216_16_33_58_acqm.zip"
    init_cpu_request = 1
    init_memory_request = 16
    init_disk_request = 2
    init_GPU = 0
    init_next_job = "None"

    # list files in this uuid and chip_id
    files = wr.list_objects(f"s3://braingeneers/integrated/{uuid}/ephys/derived/pipeline/{chip_id}/")
    acqm_files = [f for f in files if f.endswith("acqm.zip")]
    for i in range(len(acqm_files)):
        f = acqm_files[i]
        print(i, f)
        exp = f.split("/")[-1].replace("_acqm.zip", "")
        to_csv["index"].append(i+1)
        to_csv["status"].append(init_status)
        to_csv["uuid"].append(uuid)
        to_csv["experiment"].append(exp)
        to_csv["file_path"].append(f)
        to_csv["image"].append(init_image)
        to_csv["args"].append(init_args)
        to_csv["cpu_request"].append(init_cpu_request)
        to_csv["memory_request"].append(init_memory_request)
        to_csv["disk_request"].append(init_disk_request)
        to_csv["GPU"].append(init_GPU)
        to_csv["next_job"].append(init_next_job)
    
    save = False
    if save:
        # save to csv
        with open('20240227212358.csv', 'w', newline='') as csvfile:
            fieldnames = ["index", "status", "uuid", "experiment", "file_path", "image", "args", "cpu_request", "memory_request", "disk_request", "GPU", "next_job"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for i in range(len(to_csv["index"])):
                writer.writerow({k: to_csv[k][i] for k in fieldnames})
        print("Done!")
    
    mqtt_start_job("s3://braingeneers/services/mqtt_job_listener/csvs/20240227212358.csv", [i+1 for i in range(len(acqm_files))])


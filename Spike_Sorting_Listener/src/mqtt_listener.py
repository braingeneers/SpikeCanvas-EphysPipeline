from braingeneers.utils import messaging
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
import uuid as uuidgen
from k8s_kilosort2 import Kube
import time
import csv
import os
from pprint import pprint

# some parameters
## use my personal bucket for testing
TEMP_S3_BUCKET = "s3://braingeneers/personal/suryjg/"
LOCAL_CSV = "jobs.csv"
TEMP_CSV = "temp.csv"
JOB_PREFIX = "edp-"
TOPIC = "services/csv_job"


def start_listening():
    print("Listening to messages...")
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    q = messaging.CallableQueue()
    mb.subscribe_message(topic=TOPIC, callback=q)

    while True:
        topic, message = q.get()
        print(f"Received message from topic: {topic}")
        # try:
        execute_message(message)
        # except:
        #     print("Can't execute message")
        #     pass


def execute_message(message):
    csv_path = message.get("csv")
    update = message.get("update")
    update_info = None
    job_index = None
    for k, v in update.items():
        update_info = str(k)
        job_index = v
    print("message: ", csv_path, update_info, job_index, type(job_index), type(job_index[0]))
    run_job_from_csv(csv_path, update_info, job_index)


def download_csv(csv_path):
    if os.path.isfile(LOCAL_CSV):
        os.remove(LOCAL_CSV)
    if os.path.isfile(TEMP_CSV):
        os.remove(TEMP_CSV)
    wr.download(csv_path, LOCAL_CSV)


def upload_csv(csv_path):
    assert os.path.isfile(TEMP_CSV) is True, f"{TEMP_CSV} not exist"
    wr.upload(TEMP_CSV, csv_path)


def run_job_from_csv(csv_path, update_info, job_index):
    """
    # run jobs that are ready
    # run the next job when next is not None
    # run next job after update job status (wait until the csv file is uploaded)
    :param
    :return:
    """

    download_csv(csv_path)
    print(f"Downloaded {csv_path} to {LOCAL_CSV}")
    with open(LOCAL_CSV, newline='') as f:
        reader = csv.DictReader(f)
        new_f = open(TEMP_CSV, 'w', newline='')
        writer = csv.DictWriter(new_f, fieldnames=reader.fieldnames)
        writer.writeheader()
        next_job = set()
        for row in reader:
            if update_info == "Start" and int(row["index"]) in job_index:
                launch_job(csv_path, row)
                row["status"] = "started"
            elif update_info == "Succeeded" and int(row["index"]) in job_index:
                if row["next_job"] != "None":
                    next_index = list(row["next_job"].split('/'))
                    for n in next_index:
                        next_job.add(int(n))
                row["status"] = update_info
            elif update_info not in ["Start", "Succeeded"]:
                row["status"] = update_info
            elif bool(next_job) and int(row["index"]) in next_job:
                launch_job(csv_path, row)
                row["status"] = "started"
                next_job.remove(int(row["index"]))
            writer.writerow(row)
        new_f.close()

    upload_csv(csv_path)
    print(f"Uploaded {TEMP_CSV} to {csv_path}")


def launch_job(csv_path, csv_row):
    job_info = dict(csv_row).copy()
    job_ind = job_info["index"]
    job_name = format_job_name(csv_path, job_ind)
    print(f"creating job: {job_name}")
    # create job using job_info
    newJob = Kube(job_name, job_info)
    if not newJob.check_job_exist():
        resp = newJob.create_job()
        # pprint(resp)
    else:
        if not newJob.check_job_status():
            newJob.delete_job()
            print("delete old job")
            time.sleep(1)
            resp = newJob.create_job()
            # pprint(resp)


def format_job_name(path, job_ind, prefix=JOB_PREFIX):  # csv file name should be ymdt.csv
    file_name = path.split('mqtt_job_listener/csvs/')[1]
    file_name = file_name.split('.csv')[0] + "-" + str(job_ind)

    for i in range(len(file_name)):
        if file_name[i] == "_" or file_name[i] == ".":
            file_name[i] = "-"
        elif file_name[i].isupper():
            file_name[i] = file_name[i].lower()
    # if len(file_name) >= (63 - len(prefix)):    # the file_name should be much shorter than 63 and all numbers
    #     file_name = file_name[-(63 - len(prefix)) + 1:]
    #     if file_name[0] == '-':
    #         file_name[0] = "x"
    file_name = "".join(file_name)
    job_name = prefix + file_name
    return job_name


if __name__ == "__main__":
    start_listening()

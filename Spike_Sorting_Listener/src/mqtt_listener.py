from braingeneers.utils import messaging
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
import uuid as uuidgen
from k8s_kilosort2 import Kube
import time
import csv
import os
import logging
import re
import posixpath
import zipfile
import json

LOCAL_CSV = "csv/"
JOB_PREFIX = "edp-"
TOPIC = ["services/csv_job", "experiments/upload", "telemetry/+/log/experiments/upload"]
TO_SLACK_TOPIC = "telemetry/slack/TOSLACK/ephys-data-pipeline"
LOG_FILE_NAME = "listener.log"
LOG_PATH = "s3://braingeneers/services/mqtt_job_listener/" + LOG_FILE_NAME
DEFAULT_S3_BUCKET = "s3://braingeneers/ephys/"

# setup logging
stream_handler = logging.StreamHandler()
# stream_handler.setLevel(logging.INFO)
stream_handler.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE_NAME, mode="a"),
                              stream_handler])


########################## Listener ##########################
class JobMessage:
    def __init__(self, topic, message):
        self.topic = topic
        self.message = message

    def parse_topic(self):
        """
        Execute message according to topic
        """
        if self.topic.endswith("upload"):
            self.run_sorting()
        elif self.topic.endswith("csv_job"):
            self.run_csv_job()

    def run_sorting(self):
        uuid = self.message.get('uuid')
        s3_base = s3_basepath(uuid)
        logging.info(f"Getting experiments from {s3_base}{uuid}")
        if "stitch" in self.message:
            stitch = self.message.get('stitch')
        else:
            stitch = False
        if "overwrite" in self.message:
            overwrite = self.message.get('overwrite')
        else:
            overwrite = False
        # Loop over ephys_experiments
        if not stitch or stitch in ["False", "false"]:
            logging.info(f"stitch is {stitch}, loop over experiments...")
            try:
                for exp, exp_data in self.message.get('ephys_experiments').items():
                    # Get the path to the raw data
                    path = exp_data.get('blocks')[0].get('path')
                    logging.info(f"Experiment: {exp}")
                    logging.info(f"Data path: {path}")
                    file_path = posixpath.join(s3_base, uuid, path)
                    if path.startswith("ephys"):
                        chip_id = re.search(r'/[0-9]*/', path).group(0)
                        result_path = posixpath.join(s3_base, uuid, "ephys/derived/kilosort2",
                                                     chip_id[1:-1], exp + "_phy.zip")
                    else:
                        result_path = posixpath.join(s3_base, uuid, "derived/kilosort2",
                                                     exp + "_phy.zip")
                    logging.info(f"Result path: {result_path}")
                    if overwrite:
                        create_sort(exp, file_path)
                        logging.info(f"Overwrite sorting result because overwrite is {overwrite}")
                    elif not check_exist(result_path):
                        create_sort(exp, file_path)
                    else:
                        logging.info(f"Sorting result exists. Moving on to next experiment... ")
                do_logging(f"Done looping experiments. ", "info")
            except Exception as err:
                do_logging(f"Error with experiments, {err}", "error")
        else:
            # TODO: use Ash's stitch image for all experiments in this metadata
            do_logging(f"stitch is {stitch}, function to be implemented!", "info")

    def run_csv_job(self):
        logging.info(f"csv job message: {self.message}")
        csv_path = self.message.get("csv")
        if "update" in self.message:
            update = self.message.get("update")
            if bool(update):
                logging.info(f"Message to update {csv_path}")
                for k, v in update.items():
                    res = run_job_from_csv(csv_path=csv_path, update_info=k, job_index=v)
                    if res == -1:
                        logging.error(f"{csv_path} does not exist. Discard message. ")
                    else:
                        logging.info(f"Done processing {k, v}")

        if "refresh" in self.message:
            refresh = self.message.get("refresh")
            if refresh or refresh in ["True", "true"]:
                upload_csv(csv_path)
                logging.info(f"Found 'refresh' in message, uploaded local file to {csv_path}")

        if "clean" in self.message:
            clean = self.message.get("clean")
            if clean or clean in ["True", "true"]:
                remove_csv(csv_path)
                logging.info(f"Found 'clean' in message, removed local file of {csv_path}")


def get_csv_name(csv_path):
    return csv_path.split("csvs/")[-1]


def download_csv(csv_path):
    if wr.does_object_exist(csv_path):
        csv_file = get_csv_name(csv_path)
        wr.download(csv_path, os.path.join(LOCAL_CSV, csv_file))
        return csv_file
    else:
        return None


def upload_csv(csv_path):
    csv_file = get_csv_name(csv_path)
    local_path = os.path.join(LOCAL_CSV, csv_file)
    wr.upload(local_path, csv_path)


def remove_csv(csv_path):
    csv_file = get_csv_name(csv_path)
    local_path = os.path.join(LOCAL_CSV, csv_file)
    if os.path.isfile(local_path):
        os.remove(local_path)


def csv_exists(csv_path):
    csv_file = get_csv_name(csv_path)
    local_path = os.path.join(LOCAL_CSV, csv_file)
    if os.path.isfile(local_path):
        return True
    else:
        return False


def run_job_from_csv(csv_path, update_info, job_index):
    """
    # run jobs that are ready
    # run the next job when next is not None
    # run next job after update job status
    :param
    csv_file: name of the csv, not s3 path or a local path
    :return:
    """
    if not csv_exists(csv_path):
        logging.info(f"Download csv from {csv_path}")
        csv_file = download_csv(csv_path)
    else:
        logging.info(f"Found a local csv.")
        csv_file = get_csv_name(csv_path)

    if csv_file is None:
        return -1

    new_rows_list = []
    with open(f"{LOCAL_CSV}{csv_file}", 'r') as file1:
        reader = csv.DictReader(file1)
        fieldnames = reader.fieldnames
        # print(fieldnames)
        next_job = set()
        for row in reader:
            if int(row["index"]) in job_index:
                if update_info == "Start":
                    launch_job_csv(csv_file, row)
                elif update_info == "Succeeded":
                    if row["next_job"] != "None":
                        next_index = list(row["next_job"].split('/'))
                        for n in next_index:
                            next_job.add(int(n))
                row["status"] = update_info
            elif bool(next_job) and int(row["index"]) in next_job:
                launch_job_csv(csv_file, row)
                row["status"] = "Started"
                next_job.remove(int(row["index"]))
            new_rows_list.append(row)
    # Do the writing
    with open(f"{LOCAL_CSV}{csv_file}", 'w', newline='') as file2:
        writer = csv.DictWriter(file2, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows_list)
    return csv_file


def launch_job_csv(csv_file, csv_row):
    job_info = dict(csv_row).copy()
    job_ind = job_info["index"]
    job_name = format_job_name(csv_file, job_ind)
    logging.info(f"creating job for job name: {job_name}")
    resp = create_kube_job(job_name, job_info)
    # TODO: resp should have many info inside. Parse it by a better way
    if resp == -1:
        logging.error(f"Error creating {job_name}. Err message {resp}")  # TODO: catch error message...
    else:
        logging.info(f"Job {job_name} created")


########################## Utils ##########################
def create_kube_job(job_name, job_info):
    global resp
    newJob = Kube(job_name, job_info)
    if not newJob.check_job_exist():
        resp = newJob.create_job()
    else:
        if not newJob.check_job_status():
            newJob.delete_job()
            logging.info(f"Remove the inactiva old job and create a new one")
            time.sleep(1)
            resp = newJob.create_job()
    if resp == -1:
        # send message to slack 
        message_slack(job_name, job_info, message_text="Error creating job")
        logging.error(f"Error creating {job_name}. Err message {resp}")  # TODO: catch error message...
    else:
        # send message to slack
        message_slack(job_name, job_info, message_text="Job created")
        logging.info(f"Job {job_name} created")
    return resp


def format_job_name(file_name, job_ind=None, prefix=JOB_PREFIX):
    if file_name.endswith(".csv") and job_ind is not None:
        file_name = list(file_name.split('.csv')[0] + "-" + str(job_ind))
    elif file_name.endswith(".raw.h5"):
        file_name = list(file_name.split(".raw.h5")[0])
    elif file_name.endswith(".h5"):
        file_name = list(file_name.split(".h5")[0])

    if not isinstance(file_name, list):
        file_name = list(file_name)
    for i in range(len(file_name)):
        if file_name[i] in [" ", "_", ".", "/"]:
            file_name[i] = "-"
        elif file_name[i].isupper():
            file_name[i] = file_name[i].lower()
    np = len(prefix)
    if len(file_name) >= (63 - np):
        file_name = file_name[-(63 - np) + 1:]
        if file_name[0] == '-':
            file_name[0] = "x"
    file_name = "".join(file_name)
    job_name = prefix + file_name
    return job_name


def s3_basepath(UUID):
    if not isinstance(UUID, str):
        UUID = str(UUID)
    match = re.search(r'-[a-z]*-', UUID).group(0)
    if "-e-" in match:
        s3_basepath_ = 's3://braingeneers/ephys/'
    elif "-f-" in match:
        s3_basepath_ = 's3://braingeneers/fluidics/'
    else:
        s3_basepath_ = 's3://braingeneers/integrated/'
    return s3_basepath_


def write_log(local_file, s3_file):
    with open(local_file) as f:
        history = f.read()
    with smart_open.open(s3_file, 'w') as sf:
        sf.write(history)
    return None


def do_logging(log_msg, info_type):
    if info_type == "error":
        logging.error(log_msg)
    elif info_type == "info":
        logging.info(log_msg)
    write_log(LOG_FILE_NAME, LOG_PATH)
    time.sleep(0.1)


def check_exist(path):
    if wr.does_object_exist(path):
        with smart_open.open(path, 'rb') as f:
            with zipfile.ZipFile(f, 'r') as f_zip:
                if 'params.py' in f_zip.namelist():
                    return True
    return False


def create_sort(experiment, file_path):
    with open("sorting_job_info.json") as f:
        job_info = json.load(f)

    job_info["file_path"] = file_path
    job_name = format_job_name(experiment)
    resp = create_kube_job(job_name, job_info)
    # if resp == -1:
    #     # send message to slack 
    #     message_slack(job_name, job_info, message_text="Error creating job")
    #     logging.error(f"Error creating {job_name}. Err message {resp}")  # TODO: catch error message...
    # else:
    #     # send message to slack
    #     message_slack(job_name, job_info, message_text="Job created")
    #     logging.info(f"Job {job_name} created")


def start_listening():
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    q = messaging.CallableQueue()
    for TP in TOPIC:
        mb.subscribe_message(topic=TP, callback=q)
        logging.info(f"Subscribed to {TP}")
        logging.info("Listening to messages...")
    try:
        while True:
            topic, message = q.get()
            logging.info(f"Received message from topic: {topic}")
            job_message = JobMessage(topic=topic, message=message)
            job_message.parse_topic()
    except Exception as err:
        do_logging(f"RED ALARM! Service Down. Error message: {err}", "error")

def message_slack(job_name, job_info, message_text):
    with open("job_type_table.json", "r") as f:
        job_lookup = json.load(f)
    if "file_path" in job_info:
        s3_path = job_info["file_path"]
    else:
        if job_info["uuid"].startswith("s3"):
            s3_path = os.path.join(job_info["uuid"],
                                    "original/data",
                                    job_info["experiment"])
        else:
            s3_path = os.path.join(DEFAULT_S3_BUCKET,
                                    job_info["uuid"],
                                    "original/data",
                                    job_info["experiment"])
    img = job_info["image"]
    if img in job_lookup:
        job_type = job_lookup[img]
    else:
        job_type = "Unknown"

    if "params" in job_info:
        job_parameter = job_info["params"]
    else:
        job_parameter = "Hardcoded"

    slack_message = {
        "NRP Job": job_name,
        "Data Path": s3_path,
        "Parameter": job_parameter,
        "Job": job_type,
        "Status": message_text
    }
    slack_message_text = format_dict_textarea(slack_message)
    message={"message": slack_message_text}
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    mb.publish_message(topic=TO_SLACK_TOPIC, 
                       message=message, 
                       confirm_receipt=True)
    logging.info(f"Sent {message} to Slack channel {TO_SLACK_TOPIC}")
    time.sleep(.01)

def format_dict_textarea(input_dict):
    """
    format dictionary to string with indent for textarea
    :param input_dict:
    :return:
    """
    global out_str
    out_str = ""

    def walk_dict(d, depth=0):
        global out_str
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict):
                    if depth == 0:
                        out_str += "".join(["*", "\t"*depth, str(k), "*", ": ", "\n"])
                    else:
                        # out_str += "".join(["> ", "\t"*depth, str(k), ": ", "\n"])
                        out_str += "".join(["> ", str(k), ": ", "\n"])
                    walk_dict(v, depth + 1)
                else:
                    out_str += "".join(["\t" * depth, str(k), ": ", str(v), "\n"])
                    walk_dict(v, depth)

    walk_dict(input_dict)
    return out_str

if __name__ == "__main__":
    start_listening()

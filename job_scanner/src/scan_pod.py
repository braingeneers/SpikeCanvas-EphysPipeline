# scan ephys data pipeline (edp) jobs on nrp and update their status to slack every 30 minutes
# group the jobs by their uuid 
# Remove jobs that are finished (includeing failed and unknown) from status_table after updating their status
# do not actually remove jobs from nrp 

from braingeneers.iot import messaging
from kubernetes import client, config
import os
import time
import uuid as uuidgen
from kubernetes.client.rest import ApiException
import logging
import json
import datetime
from dateutil.tz import tzutc, gettz

# TODO: add check output function from Kate's repo https://github.com/braingeneers/integrated-system-modules/tree/main/maxwell (analysis_tools.py)

# set up parameters
JOB_PREFIX = "edp-"  # electrophysiology
NAMESPACE = 'braingeneers'
TO_SLACK_TOPIC = "telemetry/slack/TOSLACK/ephys-data-pipeline"
# TO_SLACK_TOPIC = "telemetry/slack/TOSLACK/iot-experiments"
LOG_FILE_NAME = "edp_scanner.log"
FINISH_FLAGS = ["Succeeded", "Failed", "Unknown"]
RUNNING_FLAGS = ["Running"]

# setup logging
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE_NAME, mode="a"),
                              stream_handler])

class edpScanner:
    def __init__(self, namespace, job_prefix):
        self.namespace = namespace
        self.job_prefix = job_prefix
        self.status_table = dict()
        # load job type look table
        with open("job_type_table.json", "r") as f:
            self.job_lookup = json.load(f)
        print(f"Job lookup table {self.job_lookup}")

    def scan_edp(self):
        config.load_kube_config()
        core_v1 = client.CoreV1Api()
        logging.info(f"Start scanning {JOB_PREFIX} jobs for namespace {self.namespace}")

        while True:
            try:
                pod_list = core_v1.list_namespaced_pod(namespace=self.namespace)
            except:
                logging.info("Refresh token")
                config.load_kube_config()
                core_v1 = client.CoreV1Api()
                pod_list = core_v1.list_namespaced_pod(namespace=self.namespace)

            current_pods = []
            for pod in pod_list.items:
                pname = pod.metadata.name
                current_pods.append(pname)
                if pname.startswith(self.job_prefix):
                    sts = pod.status.phase
                    img = pod.spec.containers[0].image
                    if img in self.job_lookup:
                        jtype = self.job_lookup[img]
                    else:
                        jtype = "unknown"
                    if pname not in self.status_table:
                        data_path, params_path = parse_data_path(pod)
                        self.status_table[pname] = {"job_type": jtype, 
                                                    "data_path": data_path, # parse_data_path(pod),
                                                    "parameter": params_path,
                                                    "status": sts} 
                    else:
                        self.status_table[pname]["status"] = sts
                        
                    if sts in RUNNING_FLAGS:
                        start_timestamp = pod.status.start_time  # this is utc
                        # change utc to local time and format to a string
                        start_ts_str = convert_time(start_timestamp)
                        self.status_table[pname]["start_time"] = start_ts_str
                    if sts in FINISH_FLAGS:
                        start_timestamp = pod.status.start_time  
                        start_ts_str = convert_time(start_timestamp)
                        if pod.status.conditions is not None:
                            end_timestamp = pod.status.conditions[1].last_transition_time  
                            end_ts_str = convert_time(end_timestamp)
                        else:
                            end_ts_str = "Unknown"
                        self.status_table[pname]["start_time"] = start_ts_str
                        self.status_table[pname]["end_time"] = end_ts_str
                            
            self.update_status_to_slack()
            # remove finished jobs from status_table
            for pname in self.status_table.copy():
                if pname not in current_pods:
                    del self.status_table[pname]
                else:
                    status = self.status_table[pname]
                    if status["status"] in FINISH_FLAGS:
                        del self.status_table[pname]
                        # also remove the pod from nrp
                        try:
                            api_response = \
                                core_v1.delete_namespaced_pod(pname,
                                                                namespace=self.namespace,
                                                                body=client.V1DeleteOptions(
                                                                    propagation_policy='Foreground',
                                                                    grace_period_seconds=0)
                                                                )
                            logging.info(f"Delete {status["status"]} pod {api_response.metadata.name}")
                            time.sleep(0.1)
                        except ApiException as e:
                            logging.error(f"Exception when calling CoreV1Api->delete_namespaced_pod: {e}")
            
            logging.info(f"status_table after removing finished jobs: {self.status_table}")
            time.sleep(30*60) # scan every 30 minutes

    def update_status_to_slack(self):
        uuid_status_table = dict()
        for pname, status in self.status_table.items():
            uuid = status["data_path"].split("/")[4]
            if uuid not in uuid_status_table:
                uuid_status_table[uuid] = {}
            rec_name = status["data_path"].split("/")[-1]
            if status["parameter"] is not None:
                parameter = status["parameter"].split("params/")[-1]
            else:
                parameter = "Hardcoded"
            uuid_status_table[uuid][rec_name] = {"Status": status["status"],
                                                 "Job": status["job_type"],
                                                 "Parameter": parameter
                                                #  "NRP pod": pname,
                                                }
            if "start_time" in status:
                uuid_status_table[uuid][rec_name]["Start Time"] = status["start_time"]
            if "end_time" in status:
                uuid_status_table[uuid][rec_name]["End Time"] = status["end_time"]
        # convert dict to text and send to slack
        status_message = format_dict_textarea(uuid_status_table)  
        message = {"message": status_message}
        mb = messaging.MessageBroker(str(uuidgen.uuid4()))
        mb.publish_message(topic=TO_SLACK_TOPIC, message=message, confirm_receipt=True)
        logging.info(f"Sent {message} to Slack {TO_SLACK_TOPIC.split('/')[-1]} channel")
        time.sleep(.01)

def parse_data_path(pod):
    """
    Parse the container's argument to get data path and parameter file path
    The argument is structured as 
        "python script_name.py data_path param_file_path other_input_args_if_any"
    or 
        "./script_name.sh data_path param_file_path other_input_args_if_any"
    """
    args = pod.spec.containers[0].args[0]
    if args.startswith("./"):
        data_path = args.split()[1]
        if "mqtt_job_listener/params" in args:
            params_path = args.split()[2]
        else:
            params_path = None
    elif args.startswith("python"):
        data_path = args.split()[2]
        if "mqtt_job_listener/params" in args:
            params_path = args.split()[3]
        else:
            params_path = None
    return data_path, params_path


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

def convert_time(timestamp, timezone = "US/Pacific"):
    """
    convert utc time to local time and format to a string
    :param timestamp: must be a datetime object
    :return:
    """
    to_zone = gettz(timezone)
    local_ts = timestamp.astimezone(to_zone)
    ts_str = local_ts.strftime("%Y-%m-%d %H:%M:%S")
    return ts_str

if __name__ == "__main__":
    scanner = edpScanner(NAMESPACE, JOB_PREFIX)
    scanner.scan_edp()


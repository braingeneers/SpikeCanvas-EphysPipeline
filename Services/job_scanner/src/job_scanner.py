from braingeneers.iot import messaging
from kubernetes import client, config
import os
import time
import uuid as uuidgen
from kubernetes.client.rest import ApiException
import logging

# CSV storage path - configurable via environment (default built from S3_BUCKET if available)
_s3_bucket = os.getenv("S3_BUCKET")
_service_root = os.getenv("SERVICE_ROOT")
if _service_root:
    CSV_UUID = f"{_service_root}/csvs/"
elif _s3_bucket:
    CSV_UUID = f"s3://{_s3_bucket}/services/mqtt_job_listener/csvs/"
else:
    CSV_UUID = None  # Will fail if CSV operations attempted without configuration

JOB_PREFIX = "edp-"  # electrophysiology
TOPIC = "services/csv_job"
# Kubernetes namespace configurable via NRP_NAMESPACE env var
NAMESPACE = os.getenv('NRP_NAMESPACE', 'braingeneers')
TO_SLACK_TOPIC = "telemetry/slack/TOSLACK/iot-experiments"
LOG_FILE_NAME = "scanner.log"
FINISH_FLAGS = ["Succeeded", "Failed", "Unknown"]

# setup logging
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE_NAME, mode="a"),
                              stream_handler])


class Scanner:
    def __init__(self, namespace, job_prefix):
        self.namespace = namespace
        self.job_prefix = job_prefix
        self.status_table = dict()  # {"pname": {"status": None, "slack": True}}

    def scan_pod(self):
        """
        scan prp pods every 30 seconds and update status to mqtt_job_listener
        "pod.status.phase" values (dtype: str):
        Pending    Running    Succeeded    Failed    Unknown
        self.status_table = {"pname": {"status": None/Status, "slack": True/False}}
        :param namespace:
        :return:
        """
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

            for pod in pod_list.items:
                pname = pod.metadata.name
                if pname.startswith(self.job_prefix):
                    sts = pod.status.phase
                    if pname not in self.status_table and sts not in FINISH_FLAGS:
                        data_path = parse_data_path(pod)
                        if "-efi-" in data_path:
                            self.status_table[pname] = {"status": sts, "slack": True}
                        else:
                            self.status_table[pname] = {"status": sts, "slack": True}
                    elif pname in self.status_table:
                        if sts != self.status_table[pname]["status"]:
                            if sts in FINISH_FLAGS:
                                if self.status_table[pname]["slack"]:
                                    update_status_to_slack(pod, sts)  # send a message to slack iot channel
                                else:
                                    update_pod_status(pname, sts)  # send a message to update csv job status
                                del self.status_table[pname]
                                # also delete pod
                                try:
                                    api_response = \
                                        core_v1.delete_namespaced_pod(pname,
                                                                      namespace=self.namespace,
                                                                      body=client.V1DeleteOptions(
                                                                          propagation_policy='Foreground',
                                                                          grace_period_seconds=0)
                                                                      )
                                    logging.info(f"Delete {sts} pod {api_response.metadata.name}")
                                    time.sleep(0.1)
                                except ApiException as e:
                                    logging.error(f"Exception when calling CoreV1Api->delete_namespaced_pod: {e}")
                            else:
                                if not self.status_table[pname]["slack"]:
                                    update_pod_status(pname, sts)
                                self.status_table[pname]["status"] = sts
            time.sleep(30)  # scan namespace every 30 seconds
            logging.info(f"Status table: {self.status_table}")


def parse_data_path(pod):
    args = pod.spec.containers[0].args[0]
    data_path = args.split()[-1]
    return data_path


def update_pod_status(pod_name, status):
    """
    Parse pod name to get csv path and job index
    Example pod name:
        edp-20230828163030-1-PodSuffix
    :param pod_name:
    :param status:
    :return:
    """
    name_comp = pod_name.split('-')
    csv_file = f"{name_comp[1]}.csv"  # need the job name to be a string of numbers
    csv_path = os.path.join(CSV_UUID, csv_file)
    job_index = int(name_comp[2])
    topic = TOPIC
    message = {"csv": csv_path,
               "update": {status: [job_index]},
               "refresh": False,
               "clean": False
               }
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    mb.publish_message(topic=topic, message=message, confirm_receipt=True)
    logging.info(f"Sent {message} to {topic}")
    time.sleep(.01)


def update_status_to_slack(pod, status):
    data_path = parse_data_path(pod)
    text = f"Sorting {status} for {data_path}"
    message = {"message": text}
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    mb.publish_message(topic=TO_SLACK_TOPIC, message=message, confirm_receipt=True)
    logging.info(f"Sent {message} to Slack IOT channel")
    time.sleep(.01)


if __name__ == "__main__":
    new_scan = Scanner(namespace=NAMESPACE, job_prefix=JOB_PREFIX)
    new_scan.scan_pod()

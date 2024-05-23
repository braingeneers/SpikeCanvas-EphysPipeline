# scan selected pods and save their kubernetes info when they finished running
# save the info to json since the info is arranged as a dictionary
from kubernetes import client, config
import json
import os
import time
from kubernetes.client.rest import ApiException
import logging
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open


NAMESPACE = "braingeneers"
JOB_PREFIX = "edp-"  # electrophysiology data pipeline
FINISH_FLAGS = ["Succeeded", "Failed", "Unknown"]
LOG_FILE_NAME = "temp_pod_scanner.log"
json_save_to = "s3://braingeneers/services/mqtt_job_listener/logs/pod_info/"
log_save_to = "s3://braingeneers/services/mqtt_job_listener/logs/"


# setup logging
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE_NAME, mode="a"),
                              stream_handler])




if __name__ == "__main__":
    config.load_kube_config()
    core_v1 = client.CoreV1Api()
    logging.info(f"Start scanning {JOB_PREFIX} jobs for namespace {NAMESPACE}")

    while True:
        try:
            pod_list = core_v1.list_namespaced_pod(namespace=NAMESPACE)
        except:
            logging.info("Refresh namespace token")
            config.load_kube_config()
            core_v1 = client.CoreV1Api()
            pod_list = core_v1.list_namespaced_pod(namespace=NAMESPACE)

        saved = wr.list_objects(json_save_to)
        for pod in pod_list.items:
            pname = pod.metadata.name
            # find edp- pods
            if pname.startswith(JOB_PREFIX):
                # take only the finished ones
                if pod.status.phase in ["Succeeded", "Failed", "Unknown"]:
                    pod_json = f"{json_save_to}{pod.metadata.name}.json"
                    # save their info
                    if pod_json not in saved:
                        logging.info(f"pod {pname} is {pod.status.phase}, saving info to {pod_json}")
                        pod_dict = client.ApiClient().sanitize_for_serialization(pod)
                        with smart_open.open(pod_json, "w") as f:
                            json.dump(pod_dict, f, indent=4)
                            logging.info(f"Saved")
        # wait 10 min
        time.sleep(10*60)









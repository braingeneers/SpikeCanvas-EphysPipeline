import braingeneers.utils.s3wrangler as wr
from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.utils.smart_open_braingeneers as smart_open
from tenacity import retry, stop_after_attempt
import os
import csv
from values import *
import time


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
        return "Uploading file to s3 failed, please try later"


def mqtt_start_job(csv_path, job_index):
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))
    topic = "services/csv_job"
    message = {"csv": csv_path,
               "update": {"Start": job_index}
               }
    try:
        mb.publish_message(topic=topic, message=message, confirm_receipt=True)
        print("Sent message:", topic, message)
        time.sleep(.01)
        return None
    except Exception as err:
        return str(err)

def format_dict_textarea(input_dict):
    """
    format dictionary to string with indent for textarea
    :param input_dict:
    :return:
    """
    return str(input_dict)

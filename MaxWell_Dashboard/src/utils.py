import braingeneers.utils.s3wrangler as wr
from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.utils.smart_open_braingeneers as smart_open
from tenacity import retry, stop_after_attempt
import os
import csv
from values import *
import time

# TODO: change print to logging


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


def parse_dict(metadata):
    """
    Note: rec length may not be correct because the frame number
    in metadata.json is incorrect.
    :param metadata:
    :return:
    """
    def convert_length(frames, fs):
        if isinstance(frames, str):
            frames = int(frames)
        if isinstance(fs, str):
            fs = float(fs)
        return time.strftime('%Hhr %Mmin %Ss', time.gmtime(frames / fs))

    def convert_fs(fs):
        if isinstance(fs, str):
            fs = float(fs)
        if fs >= 1000:
            return str(fs / 1000) + " kHz"
        else:
            return str(fs) + " Hz"

    if isinstance(metadata, dict):
        if "maxwell_chip_id" in metadata:
            summary = {"Number of Recordings":
                           len(metadata["ephys_experiments"]),
                       "Chip ID": metadata["maxwell_chip_id"],
                       "Notes": metadata["notes"],
                       "Recordings": {}}
        else:
            summary = {"Number of Recordings":
                           len(metadata["ephys_experiments"]),
                       "Notes": metadata["notes"],
                       "Recordings": {}}
        if isinstance(metadata["ephys_experiments"], list):
            for i, exp in enumerate(metadata["ephys_experiments"]):
                name = exp["blocks"][0]["path"].split("/")[1]
                summary["Recordings"][name] = \
                    {"Hardware": exp["hardware"],
                     "Sample Rate": convert_fs(exp["sample_rate"]),
                     "Length":
                         convert_length(exp["blocks"][0]["num_frames"],
                                        exp["sample_rate"]),
                     "Time": exp["timestamp"],
                     "Number of Channels": exp["num_channels"]
                     }
        elif isinstance(metadata["ephys_experiments"], dict):
            if "metadata_version" in metadata:
                fs = "sampling_rate"
                diff_key = ("HPF", "high_pass_filter")
            else:
                fs = "sample_rate"
                diff_key = ("Time", "timestamp")
            for name, exp in metadata["ephys_experiments"].items():
                summary["Recordings"][name] = \
                    {"Hardware": exp["hardware"],
                     "Sample Rate": convert_fs(exp[fs]),
                     "Length":
                         convert_length(exp["blocks"][0]["num_frames"],
                                        exp["sample_rate"]),
                     diff_key[0]: exp[diff_key[1]],
                     "Number of Channels": exp["num_channels"]
                     }
        return summary
    else:
        return {"Note": "Metadata not available"}


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
                    out_str += "".join(["\t" * depth, str(k), ": ", "\n"])
                    walk_dict(v, depth + 1)
                else:
                    out_str += "".join(["\t" * depth, str(k), ": ", str(v), "\n"])
                    walk_dict(v, depth)

    walk_dict(input_dict)
    return out_str


def filter_dropdown(search_value=None):
    print("search_value:", search_value)
    uuids = wr.list_directories(DEFAULT_BUCKET)
    if search_value is not None:
        filtered = [id for id in uuids if search_value in id]
        print(f"number of filtered uuids {len(filtered)}")
        return filtered
    else:
        print(f"number of total uuids {len(uuids)}")
        return uuids
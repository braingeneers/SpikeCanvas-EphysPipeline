import braingeneers.utils.s3wrangler as wr
from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.utils.smart_open_braingeneers as smart_open
from tenacity import retry, stop_after_attempt
import os
import csv
from values import *
try:
    from Services.common.config import load_config, s3_uri
    _cfg = load_config()
except Exception:
    _cfg = None
import time
import logging
from dateutil.tz import gettz

# TODO: change print to logging
# Patch for JWT/shadows database issue in braingeneerspy
# The MessageBroker tries to access jwt_service_account_token property which triggers
# shadows database access even though it is not needed for MQTT messaging.
# This monkey-patch prevents that unnecessary access.
# Updated: 2025-11-25 - Fixed property replacement v2

# Define the patched property function
def _patched_jwt_getter(self):
    """Patched JWT property getter that returns None to skip shadows database access"""
    return None

# Apply the patch by completely deleting and recreating the property
if hasattr(messaging.MessageBroker, "jwt_service_account_token"):
    # Delete the old property descriptor completely
    delattr(messaging.MessageBroker, "jwt_service_account_token")
    # Create new property with our patched getter
    setattr(messaging.MessageBroker, "jwt_service_account_token", property(
        fget=_patched_jwt_getter,
        doc="Patched JWT property - returns None to bypass shadows database"
    ))

# Logger setup
logger = logging.getLogger("dashboard-utils")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


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
        logger.error(err)
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
        logger.info(f"Sent message: {topic} {message}")
        time.sleep(.01)
        return None
    except Exception as err:
        logger.error(f"mqtt_start_job error: {err}")
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

def readable_keys(input_dict):
    readable_dict = {}
    for k, v in input_dict.items():
        if k in CONVERT_TO_READABLE:
            k = CONVERT_TO_READABLE[k]
        readable_dict[k] = v
    logger.debug(readable_dict)
    return readable_dict

def convert_to_json_key(param_name):
    if param_name in CONVERT_TO_JSON:
        return CONVERT_TO_JSON[param_name]
    else:
        return param_name

def filter_dropdown(search_value=None):
    logger.debug(f"search_value: {search_value}")
    # Use configuration-derived bucket/prefix; fallback to DEFAULT_BUCKET if config failed.
    base_bucket = DEFAULT_BUCKET if _cfg is None else _cfg.root()
    uuids = wr.list_directories(base_bucket)
    if search_value is not None:
        filtered = [id for id in uuids if search_value in id]
        logger.info(f"Filtered UUID count {len(filtered)}")
        return filtered
    else:
        logger.info(f"Total UUID count {len(uuids)}")
        return uuids
    

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


def get_pod_completion_time(pod):
    """
    Safely extract the completion time from pod conditions.
    Searches for the most recent transition time from appropriate condition types.
    
    Returns:
        str: Formatted time string or "Unknown" if no completion time found
    """
    if pod.status.conditions is None or len(pod.status.conditions) == 0:
        return "Unknown"
    
    # Look for the most recent transition time from any condition
    # This is more robust than hardcoded index access
    latest_timestamp = None
    
    # Iterate through all conditions and find the latest transition time
    for condition in pod.status.conditions:
        if condition.last_transition_time:
            if latest_timestamp is None or condition.last_transition_time > latest_timestamp:
                latest_timestamp = condition.last_transition_time
    
    if latest_timestamp:
        return convert_time(latest_timestamp)
    else:
        return "Unknown"


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

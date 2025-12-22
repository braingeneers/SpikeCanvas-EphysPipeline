from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.data.datasets_electrophysiology as ephys
import argparse
import braingeneers.utils.s3wrangler as wr
import os
import time
from pathlib import Path
import sys

TOPIC = "experiments/upload"
INTER_BUCKET = "original/data/"


def create_message(uuid, exp_list, ow=False):
    """
    create the minimum dictionary of metadata if the metadata.json is not available
    or the input experiment is a subset of all experiments
    :param uuid:
    :param exp_list:
    :return:
    """
    if uuid.endswith("/"):
        uuid = uuid[:-1]
    message = {
        "uuid": uuid,
        "stitch": "False", 
        "overwrite": ow,
        "ephys_experiments": {},
        "output": f"s3://braingeneers/{uuid}/derived/stitch/result_phy.zip"
    }
    experiments = {}
    for exp in exp_list:
        # exp_dataset = exp.split(INTER_BUCKET)[1]
        exp_dataset = Path(exp).name 
        # exp_name = exp_dataset.split(".")[0]
        if exp_dataset.endswith(".raw.h5"):
            exp_name = exp_dataset.split(".raw.h5")[0]
        elif exp_dataset.endswith(".h5"):
            exp_name = exp_dataset.split(".h5")[0]
        elif exp_dataset.endswith(".nwb"):
            exp_name = exp_dataset.split(".nwb")[0]
        else:
            exp_name = exp_dataset
        experiments[exp_name] = {"blocks": 
                                 [{"path": f"{INTER_BUCKET}{exp_dataset}"}],
                                 "data_format": "maxtwo"
                                 }
        
    message["ephys_experiments"] = experiments
    print(message)
    return message


def parse_args():
    parser = argparse.ArgumentParser(
        description="Send electrophysiology debug messages to the message broker."
    )
    parser.add_argument("--uuid", help="UUID of the experiment to process", required=True)
    parser.add_argument("--inter-bucket", default=INTER_BUCKET,
                        help="Intermediate bucket path segment (default: original/data/)")
    parser.add_argument("--experiments", nargs="*", default=None,
                        help="List of experiment filenames to process. If omitted, all are processed.")
    parser.add_argument("--overwrite", type=lambda v: v.lower() in ["y", "yes", "true", "1"],
                        default=False, help="Whether to overwrite results (y/n)")
    return parser.parse_args()


def validate_and_process(uuid, inter_bucket, experiment_selection, overwrite):
    default_bucket = "s3://braingeneers/ephys/"
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))

    print("############### Welcome to Braingeneers Electrophysiology Data Pipeline ###############")
    print(f"Default bucket: {default_bucket}")
    print(f"Default inter bucket: {inter_bucket}")

    data_path = None
    print("Checking recordings in this UUID ... ")
    if uuid.endswith("/"):
        s3_path = os.path.join(default_bucket, uuid)
    else:
        uuid += "/"
        s3_path = os.path.join(default_bucket, uuid)
        print(wr.list_directories(s3_path))
    if os.path.join(s3_path, inter_bucket.split("/")[0]+"/") in wr.list_directories(s3_path):
        data_path = os.path.join(s3_path, inter_bucket)
        # if wr.does_object_exist(os.path.join(s3_path, "metadata.json")):
        #     metadata = ephys.load_metadata(uuid)
        print(f"data path is {data_path}")
        recs = wr.list_objects(data_path)
        print(f"Found {len(recs)} recordings.")
        for rec in recs:
            print(rec)
    else:
        raise ValueError("No available recording for the provided UUID.")

    exp_list = wr.list_objects(data_path)
    # More robust extraction of experiment names from S3 paths
    exp_name = []
    for exp in exp_list:
        # Use Path to extract just the filename
        filename = Path(exp).name
        exp_name.append(filename)

    print("Available experiment files:")
    for name in exp_name:
        print(f"  {name}")
    experiment = set(experiment_selection) if experiment_selection is not None else set()

    if experiment_selection is not None:
        for i, exp in enumerate(experiment):
            if not exp.endswith(".h5"):
                raise ValueError("Please input the full name of the experiment, including the extension .h5 or .raw.h5")
            if exp not in exp_name:
                raise ValueError(f"Experiment {exp} is not in the provided UUID")

    exp_exist = []
    if len(experiment) == 0:  # run for all experiments
        exp_exist = exp_list.copy()
        print(f"Getting ready for all {len(exp_exist)} experiments...")
    else:
        exp_exist = [os.path.join(data_path, exp) for exp in experiment]
        print(f"Getting read for the selected {len(exp_exist)} experiments...")

    ow = overwrite
    print(f"User set overwrite to {ow}")
    metadata = create_message(uuid, exp_exist, ow)
    mb.publish_message(topic=TOPIC, message=metadata, confirm_receipt=True)
    time.sleep(0.1)
    print(f"Message sent to {TOPIC} for UUID {uuid} for processing {len(exp_exist)} experiments")
    print("############### Thank You ###############")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        default_bucket = "s3://braingeneers/ephys/"
        mb = messaging.MessageBroker(str(uuidgen.uuid4()))

        print("############### Welcome to Braingeneers Electrophysiology Data Pipeline ###############")
        print(f"Default bucket: {default_bucket}")
        print(f"Default inter bucket: {INTER_BUCKET}")

        change_inter_bucket = input("Do you want to change the inter bucket? y/n")
        if change_inter_bucket == "y":
            INTER_BUCKET = input("Please input the new inter bucket: ")
            print(f"Inter bucket changed to {INTER_BUCKET}")

        data_path = None
        uuid = None
        get_uuid = True
        get_exp = True
        get_overwrite = True
        while get_uuid:
            uuid = input("Please enter a UUID: ")
            uuid = "".join(uuid.split())
            print("Checking recordings in this UUID ... ")
            if uuid.endswith("/"):
                s3_path = os.path.join(default_bucket, uuid)
            else:
                uuid += "/"
                s3_path = os.path.join(default_bucket, uuid)
                print(wr.list_directories(s3_path))
            if os.path.join(s3_path, INTER_BUCKET.split("/")[0]+"/") in wr.list_directories(s3_path):
                data_path = os.path.join(s3_path, INTER_BUCKET)
                # if wr.does_object_exist(os.path.join(s3_path, "metadata.json")):
                #     metadata = ephys.load_metadata(uuid)
                print(f"data path is {data_path}")
                recs = wr.list_objects(data_path)
                print(f"Found {len(recs)} recordings.")
                for rec in recs:
                    print(rec)
                get_uuid = False
            else:
                print("No available recording. Please input another UUID")

        exp_list = wr.list_objects(data_path)
        # More robust extraction of experiment names from S3 paths
        exp_name = []
        for exp in exp_list:
            # Use Path to extract just the filename
            filename = Path(exp).name
            exp_name.append(filename)

        print("Available experiment files:")
        for name in exp_name:
            print(f"  {name}")
        # get experiment
        experiment = None
        while get_exp:
            experiment = input("Enter experiment name \n"
                            "(To run for all of the experiments in the provided UUID, press Enter) \n"
                            "(To run on a selection of experiments, input the name one after another,"
                            " separate them by space): ")
            experiment = set(experiment.split(" "))
            while "" in experiment:
                experiment.remove("")
            num = len(experiment)
            if num > 0:
                for i, exp in enumerate(experiment):
                    if not exp.endswith(".h5"):
                        print("Please input the full name of the experiment, including the extension .h5 or .raw.h5")
                        break
                    else:
                        if exp not in exp_name:
                            print(f"Experiment {exp} is not in the provided UUID")
                            break
                        else:
                            if i == num - 1:
                                get_exp = False
            else:
                get_exp = False


        exp_exist = []
        if len(experiment) == 0:  # run for all experiments
            exp_exist = exp_list.copy()
            print(f"Getting ready for all {len(exp_exist)} experiments...")
        else:
            exp_exist = [os.path.join(data_path, exp) for exp in experiment]
            print(f"Getting read for the selected {len(exp_exist)} experiments...")

        while get_overwrite:
            ow_input = input("Overwrite result? y/n")
            if ow_input == "y":
                ow = True
            else:
                ow = False
            print(f"User set overwrite to {ow}")
            get_overwrite = False
        metadata = create_message(uuid, exp_exist, ow)
        mb.publish_message(topic=TOPIC, message=metadata, confirm_receipt=True)
        time.sleep(0.1)
        print(f"Message sent to {TOPIC} for UUID {uuid} for processing {len(exp_exist)} experiments")
        print("############### Thank You ###############")
    else:
        args = parse_args()
        INTER_BUCKET = args.inter_bucket
        validate_and_process(args.uuid, INTER_BUCKET, args.experiments, args.overwrite)

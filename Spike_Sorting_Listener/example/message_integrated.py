from braingeneers.iot import messaging
import uuid as uuidgen
import braingeneers.data.datasets_electrophysiology as ephys
import argparse
import braingeneers.utils.s3wrangler as wr
import os
import time

TOPIC = "experiments/upload"
chip_id = "19894"
SUB_BUCKET = "original/data"
# SUB_BUCKET = "shared"


def create_message(uuid, chip_id, exp_list):
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
        "overwrite": "True",
        "ephys_experiments": {}
    }
    experiments = {}
    for exp in exp_list:
        exp_dataset = exp.split(f"/{SUB_BUCKET}/{chip_id}/")[1]
        if exp_dataset.endswith(".raw.h5"):
            exp_name = exp_dataset.split(".raw.h5")[0]
        else:
            exp_name = exp_dataset
        experiments[exp_name] = {"blocks": [{"path": f"ephys/{SUB_BUCKET}/{chip_id}/{exp_dataset}"}]}

    message["ephys_experiments"] = experiments
    print(message)
    return message


if __name__ == '__main__':
    # default_bucket = "s3://braingeneers/ephys/"
    default_bucket = "s3://braingeneers/integrated/"
    mb = messaging.MessageBroker(str(uuidgen.uuid4()))

    print("############### Welcome to Braingeneers Electrophysiology Data Pipeline ###############")
    print(f"Default bucket: {default_bucket}")
    print(f"Default chip id: {chip_id}. To change, please input your chip id")

    data_path = None
    uuid = None
    get_uuid = True
    get_exp = True
    while get_uuid:
        uuid = input("Please enter a UUID: ")
        uuid = "".join(uuid.split())
        chip_id = input("Please enter the chip id: ")
        chip_id = "".join(chip_id.split())
        print("Checking recordings in this UUID ... ")
        if uuid.endswith("/"):
            s3_path = os.path.join(default_bucket, uuid)
        else:
            uuid += "/"
            s3_path = os.path.join(default_bucket, uuid)
        if os.path.join(s3_path, "ephys/") in wr.list_directories(s3_path):
            data_path = os.path.join(s3_path, f"ephys/{SUB_BUCKET}/{chip_id}")
            # if wr.does_object_exist(os.path.join(s3_path, "metadata.json")):
            #     metadata = ephys.load_metadata(uuid)
            recs = wr.list_objects(data_path)
            print(f"Found {len(recs)} recordings.")
            for rec in recs:
                print(rec)
            get_uuid = False
        else:
            print("No available recording. Please input another UUID")

    exp_list = wr.list_objects(data_path)
    exp_name = [exp.split(f"/{chip_id}/")[1] for exp in exp_list]
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

    metadata = create_message(uuid, chip_id, exp_exist)
    mb.publish_message(topic=TOPIC, message=metadata, confirm_receipt=True)
    time.sleep(0.1)
    print(f"Message sent to {TOPIC} for UUID {uuid} for processing {len(exp_exist)} experiments")
    print("############### Thank You ###############")

from burst import Network
import numpy as np
import utils as utils
import sys
import logging
import posixpath
import os
import shutil
import braingeneers.utils.s3wrangler as wr
from braingeneers import analysis
import matplotlib.pyplot as plt

# TODO: add auto corelation analysis and save to a seperate folder.

# parametesr
OUTPUT_BUCKET = "derived/connectivity"
SUFFIX = "conn.zip"
LOG_FILE_NAME = "connectivity.log"
TILING_DELTA = 0.02 # 20 ms

# setup logging
def setup_logging(log_file):
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        handlers=[logging.FileHandler(log_file, mode="a"),
                                  stream_handler])

def parse_s3_path(data_path):
    buckets = ["derived/kilosort2", "derived/pipeline"]
    ending = data_path.split("_")[-1]
    save_to = data_path.replace(ending, SUFFIX)
    for b in buckets:
        if b in data_path:
            save_to = save_to.replace(b, OUTPUT_BUCKET)
            break
    return save_to

def upload_file(phy_path, local_file):
    upload_path = phy_path.replace("_phy.zip", "_qm_rd.zip")
    logging.info(f"Uploading data from {local_file} to {upload_path} ...")
    wr.upload(local_file=local_file, path=upload_path)
    logging.info("Done!")



if __name__ == "__main__":
    # test data: s3://braingeneers/integrated/2023-09-16-efi-mouse-5plex-official/ephys/derived/pipeline/19894/2023-09-23-T070000-chip19894_acqm.zip

    data_path = sys.argv[1]
    figure_name = data_path.split("/")[-1].replace(".zip", "")
    if not wr.does_object_exist(data_path):
        logging.exception(f"Data doesn't exist! Check the path: {data_path}")
        sys.exit(1)

    # download file from s3 to data folder
    current_folder = os.getcwd()  # python scripts are in this folder, so create subfolder for data
    data_subfolder = "/data"
    extract_subfolder = "/conn"
    data_folder = current_folder + data_subfolder
    extract_dir = data_folder + extract_subfolder
    figure_dir = extract_dir + "/figures"

    if not os.path.isdir(data_folder):
        os.mkdir(data_folder)
    # logging.info(f"Created local base folder: {data_folder}")
    if not os.path.isdir(extract_dir):
        os.mkdir(extract_dir)
    if not os.path.exists(figure_dir):
        os.makedirs(figure_dir)

    log_file = os.path.join(extract_dir, LOG_FILE_NAME)
    setup_logging(log_file)

    save_to_path = parse_s3_path(data_path=data_path)
    logging.info(f"Run connectivity analysis ...")
    logging.info(f"Download data from: {data_path}") 
    logging.info(f"Result will be saved to: {save_to_path}")

    acqm_local_path = posixpath.join(data_folder, "acqm.zip")   # use auto curation data   
    logging.info(f"Start downloading single unit data to local {acqm_local_path} ...")
    wr.download(data_path, acqm_local_path)
    logging.info("Done!")

    # read the data and run the analysis
    train, neuron_data, _, fs = utils.load_curation(acqm_local_path)
    ccg_test = Network({"train":train, "neuron_data":neuron_data}, verbose=False)
    sd = analysis.SpikeData(train, neuron_data={0: neuron_data})
    func_pairs = {}
    for (i, j), value in ccg_test.functional_pair():
        logging.info(f"Processing  unit {i}/{j}")
        tiling = sd.spike_time_tiling(i, j, delt=TILING_DELTA)
        value["tiling"] = tiling
        func_pairs[(i, j)] = value
        lags, counts, ccg_smth = value["lags"], value["ccg"], value["ccg_smth"]
        latency, p_fast = value["latency"], value["p_fast"]
        ccg_peak = np.max(counts)
        # plot figure
        fig, axs = plt.subplots(figsize=(5, 3), tight_layout=True)
        plt.suptitle(f"{figure_name}_ccg_unit_{i}_{j}")
        axs.bar(lags, counts, label=f"p_fast={p_fast:.3g} \n count={ccg_peak} \n tiling={tiling:.3f}")
        axs.plot(lags, ccg_smth, color="red")
        axs.axvline(0, linestyle="--", color="black")
        axs.scatter(latency, ccg_peak, color="red", marker="x", label=f"latency={latency}")
        axs.legend()
        axs.set_xlabel("Lags (ms)")
        axs.set_ylabel("Counts")
        plt.savefig(f"{figure_dir}/ccg_unit_{i}_{j}.png")
        plt.close()
    np.savez(f"{extract_dir}/func_pairs.npz", func_pairs=func_pairs)
    logging.info(f"Found {len(func_pairs)} functional pairs")

# package exract_dir and upload to s3
conn_file = shutil.make_archive(posixpath.join(data_folder, "conn"), format="zip", root_dir=extract_dir)
upload_file(save_to_path, conn_file)
logging.info(f"Connectivity analysis is done! Result conn.zip saved to {save_to_path}")

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
import json

# new import
from Services.common.path_utils import normalize_acqm_source, replace_original_to_derived

DEFAULT_PARAMS = {
    "binary_bin_size": 0.001,
    "ccg_win": 50,
    "func_latency": 5,
    "p_test": 0.00001
}


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

def parse_s3_path(data_path, param_file_name):
    buckets = ["derived/kilosort2", "derived/pipeline", "derived/autocuration"]
    ending = data_path.split("_")[-1]
    param_name = param_file_name.split(".")[0]
    save_to = data_path.replace(ending, f"{param_name}_{SUFFIX}")
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
    rec_path = sys.argv[1]
    param_path = sys.argv[2]
    param_file_name = param_path.split("/")[-1]

    # download file from s3 to data folder
    current_folder = os.getcwd()  # python scripts are in this folder, so create subfolder for data
    data_subfolder = "/data"
    extract_subfolder = "/conn"
    data_folder = current_folder + data_subfolder
    extract_dir = data_folder + extract_subfolder
    figure_dir = extract_dir + "/figures"
    ccg_figure_dir = figure_dir + "/ccg"
    acg_figure_dir = figure_dir + "/acg"

    if not os.path.isdir(data_folder):
        os.mkdir(data_folder)
    if not os.path.isdir(extract_dir):
        os.mkdir(extract_dir)
    if not os.path.exists(figure_dir):
        os.makedirs(figure_dir)
        os.makedirs(ccg_figure_dir)
        os.makedirs(acg_figure_dir)

    log_file = os.path.join(extract_dir, LOG_FILE_NAME)
    setup_logging(log_file)

    # normalize input to acqm zip and ensure it points to derived/<stage>
    if "derived" in rec_path and rec_path.endswith(".zip"):
        data_path = rec_path
    else:
        # replace original/data -> derived/kilosort2, then normalize suffix to _acqm.zip
        replaced = replace_original_to_derived(rec_path, stage="kilosort2")
        normalized = normalize_acqm_source(replaced)
        if not (normalized.endswith("_acqm.zip") or normalized.endswith(".zip")):
            logging.error(f"Auto-curation for {rec_path} not available.")
            logging.error(f"Exit")
            sys.exit(1)
        data_path = normalized

    if not wr.does_object_exist(data_path):
        logging.exception(f"Data doesn't exist! Check the path: {data_path}")
        sys.exit(1)

    if not wr.does_object_exist(param_path):
        logging.exception(f"Data doesn't exist! Check the path: {param_path}")
        sys.exit(1)
    
    logging.info(f"Start running connectivity analysis for {data_path} with parameter {param_path} ...")

    figure_name = data_path.split("/")[-1].replace(".zip", "")

    save_to_path = parse_s3_path(data_path=data_path, param_file_name=param_file_name)
    logging.info(f"Run connectivity analysis ...")
    logging.info(f"Download data from: {data_path}") 
    logging.info(f"Download parameter from: {param_path}")
    logging.info(f"Result will be saved to: {save_to_path}")

    acqm_local_path = posixpath.join(data_folder, "acqm.zip")   # use auto curation data   
    logging.info(f"Start downloading single unit data to local {acqm_local_path} ...")
    wr.download(data_path, acqm_local_path)
    logging.info("Done!")
    param_local_path = posixpath.join(data_folder, param_file_name) 
    logging.info(f"Start downloading parameter file to local {param_local_path} ...")
    wr.download(param_path, param_local_path)

    # read parameters
    with open(param_local_path, "r") as f:
        params = json.load(f)
    logging.info(f"Parameters for running functional connectivity: {params}")

    for k, v in DEFAULT_PARAMS.items():
        if k not in params:
            params[k] = v
    # save parameter to extract folder so that it's packaged with the results
    with open(f"{extract_dir}/params.json", "w") as f:
        json.dump(params, f)

    # read the data and run the analysis
    train, neuron_data, _, fs = utils.load_curation(acqm_local_path)
    ccg_test = Network({"train":train, "neuron_data":neuron_data}, 
                       binary_bin_size=params["binary_bin_size"], 
                       ccg_win=params["ccg_win"], 
                       func_latency=params["func_latency"], 
                       func_prob=params["p_test"],
                       verbose=True)
    sd = analysis.SpikeData(train, neuron_data={0: neuron_data})
    func_pairs = {}
    for (i, j), value in ccg_test.functional_pair():
        logging.info(f"Processing unit {i}/{j}")
        tiling = sd.spike_time_tiling(i, j, delt=TILING_DELTA)
        value["tiling"] = tiling
        func_pairs[(i, j)] = value
        lags, counts, ccg_smth = value["lags"], value["ccg"], value["ccg_smth"]
        latency, p_fast = value["latency"], value["p_fast"]
        ccg_peak = np.max(counts)
        # plot figure
        fig, axs = plt.subplots(figsize=(5, 3))
        plt.suptitle(f"{figure_name}_ccg_unit_{i}_{j}")
        axs.bar(lags, counts, label=f"p_fast={p_fast:.3g} \n count={ccg_peak} \n tiling={tiling:.3f}")
        axs.plot(lags, ccg_smth, color="red")
        axs.axvline(0, linestyle="--", color="black")
        axs.scatter(latency, ccg_peak, color="red", marker="x", label=f"latency={latency}")
        axs.legend()
        axs.set_xlabel("Lags (ms)")
        axs.set_ylabel("Counts")
        plt.tight_layout()
        plt.savefig(f"{ccg_figure_dir}/ccg_unit_{i}_{j}.png", dpi=300)
        plt.close()
    np.savez(f"{extract_dir}/func_pairs.npz", func_pairs=func_pairs)
    logging.info(f"Found {len(func_pairs)} functional pairs")

    # also run acg for each unit, plot figure and save them 
    acg_dict = {}
    for k, value in ccg_test.acg():
        logging.info(f"Running acg for unit {k}")
        acg_dict[k] = value
        counts, lags = value["acg"], value["lags"]   
        # plot figure
        fig, axs = plt.subplots(figsize=(5, 3))
        plt.suptitle(f"{figure_name}_acg_unit_{k}")
        axs.bar(lags, counts)
        axs.set_xlabel("Lags (ms)")
        axs.set_ylabel("Counts")
        plt.tight_layout()
        plt.savefig(f"{acg_figure_dir}/acg_unit_{k}.png", dpi=300)
        plt.close()
    np.savez(f"{extract_dir}/acg.npz", acg_dict=acg_dict)
    logging.info(f"Finished running autocorrelation for {len(acg_dict)} units")
# package exract_dir and upload to s3
conn_file = shutil.make_archive(posixpath.join(data_folder, "conn"), format="zip", root_dir=extract_dir)
upload_file(save_to_path, conn_file)
logging.info(f"Connectivity analysis is done! Result conn.zip saved to {save_to_path}")

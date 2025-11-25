import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)
from src import utils

import logging
import posixpath
import shutil
import numpy as np
import braingeneers.utils.s3wrangler as wr
from braingeneers import analysis
import matplotlib.pyplot as plt
import json


def acg(train_a, ccg_win=[-50, 50]):
    bt = utils.sparse_train([train_a, train_a])
    acg, lags = utils.ccg(bt[0], bt[0], ccg_win=ccg_win)
    ind = np.where(lags == 0)[0][0]
    acg[ind] = 0   # remove the value for lag=0
    return acg, lags

if __name__ == "__main__": 
    data_list_txt = "/media/kang/Seagate_External/temp_data/jesus_waveform/phy_zip_test.txt"
    save_to = "/media/kang/Seagate_External/temp_data/jesus_waveform"
    # read each line of the txt file
    with open(data_list_txt) as f:
        data_list = f.readlines()
    data_list = [x.strip() for x in data_list]
    print(data_list)

    for i, data_path in enumerate(data_list):
        if "suryjg" in data_path:
            continue
        else:
            try:
                s3_path = f"s3://{data_path}"
                print(f"Loading data from No.{i}, {s3_path} ...")
                spike_data = analysis.load_spike_data(uuid="", full_path=s3_path)
                print(f"Found {spike_data.N} units")
                print(f"Calculating acg for {spike_data.N} units ...")
                acg_array = np.empty((0, 101))
                for t in range(spike_data.N):
                    times = spike_data.train[t] / 1000
                    acg_data, lags = acg(times)
                    acg_array = np.vstack((acg_array, acg_data))
                # save the acg_array to a numpy file
                np.save(f"{save_to}/phy_zip_{i}.npy", acg_array)
                print(f"Saved acg_array to {save_to}/phy_zip_{i}.npy")
            except Exception as e:
                print(f"Failed to load data from {s3_path} with error {e}")
                continue
        
            

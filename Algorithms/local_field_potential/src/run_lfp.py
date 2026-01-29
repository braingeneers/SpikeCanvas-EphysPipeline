import numpy as np
from braingeneers import analysis
import braingeneers.utils.smart_open_braingeneers as smart_open
import braingeneers.utils.s3wrangler as wr
import h5py
import sys
import os
import logging
import posixpath
import pandas as pd
from scipy import signal
import shutil
import json


# parameters
FS = 20000.0
DEC = 20
FS_DOWN = FS / DEC
LOW_CUT = 0.1
HIGH_CUT = 200.0
hdf5_plugin_path = '/app/'


# setup logging
def setup_logging(log_file):
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        handlers=[logging.FileHandler(log_file, mode="a"),
                                  stream_handler])

def setup_hdf5():
    os.environ['HDF5_PLUGIN_PATH'] = hdf5_plugin_path
    # copy the plugin to "/usr/local/hdf5/lib/plugin" to make sure this file can be found by the script
    path_to_lib = os.path.join(hdf5_plugin_path, "libcompression.so")
    if os.path.isfile(path_to_lib):
        os.makedirs("/usr/local/hdf5/lib/plugin/")
        shutil.copy(path_to_lib, "/usr/local/hdf5/lib/plugin/libcompression.so")

def _get_maxwell_rec_and_well(dataset):
    if "recordings" not in dataset:
        raise KeyError("No recordings group found in file")
    recordings = dataset["recordings"]
    rec_key = "rec0000" if "rec0000" in recordings else sorted(recordings.keys())[0]
    rec_group = recordings[rec_key]
    well_keys = sorted([key for key in rec_group.keys() if key.startswith("well")])
    if not well_keys:
        raise KeyError("No well groups found in recording")
    return rec_group, well_keys[0]

def load_raw_maxwell(dataset_path: str, channel_list: list, rec_period: list, fs=20000.0):
    """
    To read the raw recording data from a maxwell hdf5 file, both new and old version
    :param dataset_path: local or s3 datapath
    :param channels: [0, len(channels)-1]. The index to maxwell recording channels.
    :param rec_period: [start, end] in seconds
    :param fs: sampling rate
    :return: ndarray of shape num_channels x (rec_period x fs), dtype = float32
    """
    # sort channels because loading from h5py needs a increasing order of indexing 
    if len(channel_list)  > 1:
        org_channels = channel_list.copy()
        channels = np.sort(org_channels)
        order = np.argsort(org_channels)
    else:
        channels = channel_list.copy()
    with smart_open.open(dataset_path, 'rb') as f:
        with h5py.File(f, 'r') as dataset:
            if 'mapping' in dataset.keys():
                signal = dataset['sig']
                gain_uV = dataset['settings']['lsb'][0] * 1e6
                mw_channels = np.array(dataset['mapping']['channel'])
                matched_chan = mw_channels[channels]  # channels from kilosort are 0-based
                # print(signal.shape)
            else:
                rec_group, well_key = _get_maxwell_rec_and_well(dataset)
                signal = rec_group[well_key]['groups']['routed']['raw']
                gain_uV = rec_group[well_key]['settings']['lsb'][0] * 1e6
                # mw_channels = np.array(dataset['wells']['well001']['rec0000']['settings']['mapping']['channel'])
                matched_chan = channels.copy()
            block_start_frame = int(fs * rec_period[0])
            block_end_frame = int(fs * rec_period[1])
            curr_signal = signal[matched_chan, block_start_frame: block_end_frame]
            # sort raw signal back to or_channels order
            if len(channel_list) > 1:
                _, raw_signal = zip(*sorted(zip(order, curr_signal)))
            else:
                raw_signal = curr_signal
            raw_signal = np.array(raw_signal).astype('float32') * gain_uV
            # print(raw_signal.shape)
    
    return raw_signal

def load_info_maxwell(dataset_path, fs=20000.0):
    with smart_open.open(dataset_path, 'rb') as f:
        with h5py.File(f, 'r') as dataset:
            if 'version' and 'mxw_version' in dataset.keys():
                version = dataset['mxw_version'][0]
                rec_group, well_key = _get_maxwell_rec_and_well(dataset)
                start_time = rec_group[well_key]['start_time'][0]
                stop_time = rec_group[well_key]['stop_time'][0]
                df = pd.DataFrame({'start_end': [start_time, stop_time]})
                time_stamp = pd.to_datetime(df['start_end'], unit='ms')
                config_df = pd.DataFrame({'pos_x': np.array(rec_group[well_key]['settings']['mapping']['x']), 
                          'pos_y': np.array(rec_group[well_key]['settings']['mapping']['y']),
                          'channel': np.array(rec_group[well_key]['settings']['mapping']['channel'])})                 
                raw_frame = np.array(rec_group[well_key]['spikes']['frameno'])
                raster_df = pd.DataFrame({'channel': np.array(rec_group[well_key]['spikes']['channel']),
                                         'frameno': (raw_frame - raw_frame[0]) / fs})
            else:
                version = dataset['version'][0]
                time_stamp = dataset['time'][0].decode('utf-8')
                config_df = pd.DataFrame({'pos_x': np.array(dataset['mapping']['x']), 
                                    'pos_y': np.array(dataset['mapping']['y']),
                                    'channel': np.array(dataset['mapping']['channel']),
                                    'electrode': np.array(dataset['mapping']['electrode'])})
                raw_frame = np.array(dataset['proc0']['spikeTimes']['frameno'])
                rec_startframe = dataset['sig'][-1, 0] << 16 | dataset['sig'][-2, 0]
                raster_df = pd.DataFrame({'channel': np.array(dataset['proc0']['spikeTimes']['channel']),
                                      'frameno': (raw_frame - rec_startframe) / fs,
                                       'amplitude': np.array(dataset['proc0']['spikeTimes']['amplitude'])})        
    return version, time_stamp, config_df, raster_df

def butter_bandpass_filter(data, lowcut, highcut, fs=20000, order=5):
    band = [lowcut, highcut]
    assert len(band) == 2, "Must have lowcut and highcut!"
    Wn = [e / fs * 2 for e in band]
    filter_coeff = signal.iirfilter(order, Wn, analog=False, btype='bandpass', ftype='butter', output='sos')
    filtered_traces = signal.sosfiltfilt(filter_coeff, data)
    return filtered_traces


# Downsample 
def downsample(wav_lfp, dec=20, fs=20000.0):
    wav_data = signal.decimate(wav_lfp, dec)
    return fs/dec, wav_data


if __name__ == "__main__":
    # Updated input format to match job system:
    ## s3_path, param_path
    # example:
    ## s3://braingeneers/ephys/2023-12-03-e-Hc112823_avv9hckcr1/original/data/Hc112823_avv9hckcr1_21841_120323_1.raw.h5 s3://braingeneers/services/mqtt_job_listener/params/lfp/params_example.json
    
    # Legacy support for old format (3 arguments: data_path, start_time, end_time)
    if len(sys.argv) == 4:
        # Old format: python run_lfp.py data_path start_time end_time
        data_path = sys.argv[1]
        st, end = int(sys.argv[2]), int(sys.argv[3])
    elif len(sys.argv) == 3:
        # New format: python run_lfp.py data_path param_path
        data_path = sys.argv[1]
        param_path = sys.argv[2]
        
        # Load parameters from JSON file
        try:
            if param_path.startswith('s3://'):
                # Download parameter file from S3
                param_local = "/tmp/lfp_params.json"
                wr.download(param_path, param_local)
                with open(param_local, 'r') as f:
                    params = json.load(f)
            else:
                # Local parameter file
                with open(param_path, 'r') as f:
                    params = json.load(f)
            
            # Extract parameters with defaults
            st = int(params.get('start_time', 300))
            end = int(params.get('end_time', 360))
            logging.info(f"Loaded parameters from {param_path}: start_time={st}s, end_time={end}s")
            
        except Exception as e:
            logging.error(f"Failed to load parameters from {param_path}: {e}")
            logging.info("Using default parameters: start_time=300s, end_time=360s")
            st, end = 300, 360
    else:
        logging.error("Invalid number of arguments. Expected: data_path param_path OR data_path start_time end_time")
        sys.exit(1)
    file_name = data_path.split("/")[-1].split(".")[0]
    file_name = f"{file_name}_{st}s_{end}s"
    save_to_path = f"{data_path.split('/original/data')[0]}/derived/lfp/{file_name}.zip"

    # create folder in local for saving data
    current_folder = os.getcwd()
    subfolder = "/data"
    base_folder = current_folder + subfolder
    experiment = "rec.raw.h5"
    local_data = posixpath.join(base_folder, experiment)
    output_folder = current_folder + "/lfp"

    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # setup logging 
    log = os.path.join(output_folder, "lfp.log")
    setup_logging(log)
    # setup hdf5
    setup_hdf5()
    
    # download file from s3
    if not wr.does_object_exist(data_path):
        logging.error(f"Data doesn't exist! {data_path}")
        sys.exit(1)
    else:
        logging.info(f"Start downloading raw data {data_path} ...")
        wr.download(data_path, local_data)
        logging.info("Done")
    
    version, time_stamp, config_df, raster_df = load_info_maxwell(local_data)
    raw_channels = list(config_df["channel"])

    ch = [raw_channels.index(i) for i in config_df["channel"]]
    logging.info(f"Loading raw data from {len(ch)} channels, time {st} to {end} in second...")
    raw_trace = load_raw_maxwell(local_data, ch, [st, end])
    logging.info(f"raw_trace shape {raw_trace.shape}")
    logging.info(f"size of the data {sys.getsizeof(raw_trace)/1e6} MB")
    logging.info("Generating lfp by 5th order a butter bandpass filter ...")

    all_channel_lfp = np.empty((0, int(FS_DOWN*(end-st))))
    for i in range(raw_trace.shape[0]):
        # print(f"{i}/{raw_trace.shape[0]}")
        trace = raw_trace[i]
        lfp = butter_bandpass_filter(trace, LOW_CUT, HIGH_CUT)
        lfp_down = downsample(lfp, dec=DEC)[1]
        all_channel_lfp = np.vstack((all_channel_lfp, lfp_down))
    logging.info(f"All channel LFP shape {all_channel_lfp.shape}")
    logging.info(f"Filtered with passband {LOW_CUT} - {HIGH_CUT} Hz, downsampled to {FS_DOWN} Hz.")

    # extract the subbands and save to a npz file
    logging.info(f"Subband frequency: delta (0.5-4Hz), theta (4-8Hz), alpha (8-13Hz), beta (13-30Hz), gamma (30-50Hz)")
    logging.info("Saving LFP data to npz file...")
    lfp_data = {"lfp": all_channel_lfp, 
                "delta": butter_bandpass_filter(all_channel_lfp, 0.5, 4, fs=FS_DOWN),
                "theta": butter_bandpass_filter(all_channel_lfp, 4, 8, fs=FS_DOWN),
                "alpha": butter_bandpass_filter(all_channel_lfp, 8, 13, fs=FS_DOWN),
                "beta": butter_bandpass_filter(all_channel_lfp, 13, 30, fs=FS_DOWN),
                "gamma": butter_bandpass_filter(all_channel_lfp, 30, 50, fs=FS_DOWN),
                "location": config_df[["pos_x", "pos_y"]].values,
                "fs": FS_DOWN}
    
    np.savez(f"{output_folder}/{file_name}.npz", **lfp_data)
    logging.info(f"Saved to {output_folder}/{file_name}.npz")

    # upload to s3
    # package exract_dir and upload to s3
    logging.info(f"Local field potential extraction is done! Uploading output to {save_to_path}")
    lfp_file = shutil.make_archive(posixpath.join(base_folder, "lfp"), format="zip", root_dir=output_folder)
    wr.upload(local_file=lfp_file, path=save_to_path)
    

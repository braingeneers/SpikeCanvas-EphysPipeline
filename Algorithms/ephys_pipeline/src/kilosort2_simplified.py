import spikeinterface as si
import spikeinterface.extractors as se
import spikeinterface.preprocessing as sp
import os
import MEArec as mr
from kilosort2_params import *
from scipy.io import savemat
import subprocess
import sys
import json
import pynwb
import logging
from si_curation import QualityMetrics
import utils
import plots
import plots_sua
import shutil
import h5py
import posixpath
import re

FORMAT_LIST = ["Maxwell", "mearec", "nwb"]
data_format = None
REMOVE_SINGLE_CHANNEL = False

# updated default parameters for autocuration 
DEFUALT_PARAMS =  {"min_snr": 3,
            "min_fr": 0.1,
            "max_isi_viol": 0.5}

# TODO: Fix this mearec error 
# assert filename.suffix in [".h5", ".hdf5"], "Provide an .h5 or .hdf5 file name"
# AssertionError: Provide an .h5 or .hdf5 file name

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


class RunKilosort:
    def __init__(self, rec, output_folder):
        self.rec = rec
        self.output_folder = output_folder
        self.last_output_lines = []

    def run_sorting(self):
        self.create_config()
        sorting = self.start_kilosort()
        if sorting != 0:
            logging.error("Error: Kilosort returned non-zero value.")
        else:
            kilosort_log = os.path.join(stdln_folder, "kilosort2.log")
            if os.path.isfile(kilosort_log):
                os.rename(kilosort_log, os.path.join(self.output_folder, "kilosort2.log"))
        return sorting

    def start_kilosort(self):
        logging.info("Start running Kilosort...")
        kilosort_shell = os.path.join(stdln_folder, stdln_script)
        os.chdir(stdln_folder)
        # TODO: check where the kilosort2.log is. This file was not packaged with phy files previously
        
        # Start process with pipes to capture output
        psort = subprocess.Popen(
            ["bash", kilosort_shell, runtime_folder, self.output_folder],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        
        # Stream output in real-time to both terminal and log
        while True:
            output = psort.stdout.readline()
            if output == '' and psort.poll() is not None:
                break
            if output:
                # Print to terminal (container stdout)
                print(output.strip())
                # Also log it with logging module
                logging.info(f"Kilosort: {output.strip()}")
                # Keep a tail of the output for debugging/metrics
                self.last_output_lines.append(output.strip())
                if len(self.last_output_lines) > 2000:
                    self.last_output_lines = self.last_output_lines[-1000:]
        
        # Wait for process to complete and get return code
        ret = psort.wait()
        return ret

    def get_last_threshold_crossings(self):
        try:
            import re
            last = None
            pattern = re.compile(r"found\s+(\d+)\s+threshold crossings")
            for line in self.last_output_lines:
                match = pattern.search(line)
                if match:
                    last = int(match.group(1))
            return last
        except Exception:
            return None

    def create_config(self):
        """
        create ops.mat and chanMap.mat
        """
        groups = [1] * self.rec.get_num_channels()
        positions = np.array(self.rec.get_channel_locations())

        if positions.shape[1] != 2:
            logging.error("3D electrode positions are not supported. Please set 2D positions. ")
            return -1

        # create ops.mat
        ops = {}
        ops_dict = {}
        ops_dict["NchanTOT"] = float(self.rec.get_num_channels())
        ops_dict["Nchan"] = float(self.rec.get_num_channels())
        ops_dict["fs"] = float(self.rec.get_sampling_frequency())
        ops_dict["datatype"] = 'dat'
        ops_dict["fbinary"] = os.path.join(self.output_folder, 'recording.dat')
        ops_dict["fproc"] = os.path.join(self.output_folder, 'temp_wh.dat')
        ops_dict["root"] = str(self.output_folder)
        ops_dict["chanMap"] = os.path.join(self.output_folder, 'chanMap.mat')
        ops_dict["fshigh"] = float(kilosort_params['freq_min'])
        ops_dict["minfr_goodchannels"] = float(kilosort_params['minfr_goodchannels'])
        ops_dict["Th"] = list(map(float, kilosort_params['projection_threshold']))
        ops_dict["lam"] = float(10)
        ops_dict["AUCsplit"] = 0.9
        ops_dict["minFR"] = float(kilosort_params['minFR'])
        ops_dict["momentum"] = list(map(float, np.array([20, 400])))
        ops_dict["sigmaMask"] = float(kilosort_params['sigmaMask'])
        ops_dict["ThPre"] = float(kilosort_params['preclust_threshold'])
        ops_dict["spkTh"] = float(-kilosort_params['detect_threshold'])
        ops_dict["reorder"] = float(1)
        ops_dict["nskip"] = float(25)
        ops_dict["CAR"] = float(kilosort_params['car'])
        ops_dict["GPU"] = float(1)
        ops_dict["nfilt_factor"] = float(kilosort_params['nfilt_factor'])
        ops_dict["ntbuff"] = float(kilosort_params['ntbuff'])
        ops_dict["NT"] = float(kilosort_params['NT'])
        ops_dict["whiteningRange"] = float(32)
        ops_dict["nSkipCov"] = float(25)
        ops_dict["scaleproc"] = float(200)
        ops_dict["nPCs"] = float(kilosort_params['nPCs'])
        ops_dict["useRAM"] = float(0)
        ops_dict["trange"] = kilosort_params['trange']  # trange is float, line 56
        ops["ops"] = ops_dict
        # create mat data files
        savemat(os.path.join(self.output_folder, 'ops.mat'), ops)

        # create chanMap.mat
        chan_dict = {}
        chan_dict["Nchannels"] = float(self.rec.get_num_channels())
        chan_dict["connected"] = [True] * int(self.rec.get_num_channels())
        chan_dict["chanMap"] = list(
            map(float, np.array(range(int(self.rec.get_num_channels()))) + 1))  # MATLAB counts from 1
        chan_dict["chanMap0ind"] = list(map(float, np.array(range(int(self.rec.get_num_channels())))))
        chan_dict["xcoords"] = [p[0] for p in positions]
        chan_dict["ycoords"] = [p[1] for p in positions]
        chan_dict["kcoords"] = list(map(float, groups))
        chan_dict["fs"] = float(self.rec.get_sampling_frequency())
        savemat(os.path.join(self.output_folder, 'chanMap.mat'), chan_dict, oned_as='column')


def extract_recording(rec_path, output_folder, format):
    rec = None
    if format not in FORMAT_LIST:
        logging.error(f"Data format not supported. Data format should be in {FORMAT_LIST}")
        return -1
    if format == "mearec":
        # rename the recording file to .h5
        os.rename(rec_path, rec_path + ".h5")
        rec_path = rec_path + ".h5"
        mr.convert_recording_to_new_version(rec_path)
        rec, _ = se.read_mearec(rec_path)
    elif format == "Maxwell":
        rec_names = _get_maxwell_rec_names(rec_path)
        if len(rec_names) <= 1:
            rec_name = rec_names[0] if rec_names else None
            if rec_name:
                logging.info(f"Loading Maxwell recording {rec_name}")
                rec = se.read_maxwell(rec_path, rec_name=rec_name)
            else:
                rec = se.read_maxwell(rec_path)
        else:
            logging.info(f"Detected {len(rec_names)} Maxwell recordings; concatenating: {rec_names}")
            recordings = [se.read_maxwell(rec_path, rec_name=rec_name) for rec_name in rec_names]
            try:
                rec = si.concatenate_recordings(recordings)
            except Exception as exc:
                logging.warning(f"Concatenation failed ({exc}); defaulting to first recording")
                rec = recordings[0]
    elif format == "nwb":
        rec = se.read_nwb(rec_path)
    # filter and convert to binary recording

    fs = float(rec.get_sampling_frequency())
    if fs < 20000.:
        logging.warning("Sampling frequency is less than 20 kHz, setting the bandpass filter to 300-4600 Hz instead of 300-6000 Hz.")
        band_max = 4600
    else:
        logging.warning("Sampling frequency is 20 kHz,using 300-6000 Hz for the bandpass filter.")
        band_max = 6000
    nyquist = fs / 2.0
    max_allowed = 0.9 * nyquist
    effective_max = min(band_max, max_allowed)
    if effective_max < band_max:
        logging.warning(f"Sampling frequency {fs:.1f} Hz; clamping freq_max to {effective_max:.1f} Hz")

    rec_filter = sp.bandpass_filter(rec, freq_min=band_min, freq_max=effective_max, dtype="float32")
    binary_file_path = os.path.join(output_folder, 'recording.dat')
    se.BinaryRecordingExtractor.write_recording(
        rec_filter, file_paths=binary_file_path,
        dtype='int16', total_memory=kilosort_params["total_memory"],
        n_jobs=kilosort_params["n_jobs_bin"],
        verbose=False, progress_bar=True)
    return rec_filter


def _get_maxwell_rec_names(rec_path):
    try:
        with h5py.File(rec_path, "r") as dataset:
            if "recordings" not in dataset:
                return []
            rec_names = [key for key in dataset["recordings"].keys() if key.startswith("rec")]
            return sorted(rec_names)
    except Exception as exc:
        logging.warning(f"Failed to read Maxwell recording names: {exc}")
        return []


def _normalize_metadata_path(path: str) -> str:
    if not path:
        return ""
    path = path.lstrip("/")
    if path.startswith("original/split/"):
        path = "original/data/" + path.split("/", 2)[2]
    directory, base = posixpath.split(path)
    base = re.sub(r"_well\\d{3}(?=\\.raw\\.h5$|\\.h5$|\\.nwb$)", "", base)
    base = re.sub(r"\\.+", ".", base).rstrip(".")
    return f"{directory}/{base}" if directory else base


def _data_format_from_blocks(metadata: dict, dataset_path: str):
    target = _normalize_metadata_path(dataset_path)
    if not target:
        return None
    for exp in metadata.get("ephys_experiments", {}).values():
        blocks = exp.get("blocks") or []
        for block in blocks:
            block_path = _normalize_metadata_path(block.get("path", ""))
            if block_path and block_path == target:
                return exp.get("data_format")
    return None


def _compute_retry_nt(rec, min_batches=8, min_nt=16384):
    try:
        num_samples = int(rec.get_num_samples())
    except Exception:
        return None
    if num_samples <= 0:
        return None
    target_nt = max(min_nt, int(num_samples / float(min_batches)))
    target_nt = (target_nt // 32) * 32
    if target_nt <= 0:
        return None
    if target_nt >= kilosort_params['NT']:
        return None
    return target_nt


def _apply_conservative_kilosort_params(base_params, target_nt):
    if target_nt is not None:
        kilosort_params['NT'] = target_nt
    # Conservative settings for short/low-activity recordings
    kilosort_params['nfilt_factor'] = min(base_params.get('nfilt_factor', 4), 2)
    kilosort_params['ntbuff'] = min(base_params.get('ntbuff', 64), 32)

if __name__ == "__main__":
    output_folder = os.path.join(inter_folder, "sorted/kilosort2")
    log = os.path.join(output_folder, "run_kilosort2.log")
    setup_logging(log)
    setup_hdf5()
    allow_empty_on_kilosort_fail = os.environ.get("ALLOW_EMPTY_ON_KS_FAIL", "true").lower() in ("1", "true", "yes")
    ks_min_crossings = int(os.environ.get("KS_MIN_THRESHOLD_CROSSINGS", "5000"))

    # get format from metadata
    experiment = sys.argv[1]
    logging.info(f"Start pipeline processing for experiment {experiment}")
    metadata_path = "/project/SpikeSorting/metadata.json"
    parameter_path = "/project/SpikeSorting/parameters.json"
    if not os.path.isfile(metadata_path):
        logging.error("Note: metadata.json not available. Data format default to Maxwell.")
        data_format = "Maxwell"
    else:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        dataset_path = os.environ.get("DATASET_PATH", "")
        if dataset_path:
            data_format = _data_format_from_blocks(metadata, dataset_path)
            if data_format:
                logging.info(f"Read data format from metadata.json blocks, format is {data_format}")
            else:
                logging.info(f"Data format not found in metadata.json for dataset path: {dataset_path}")
        else:
            logging.info("DATASET_PATH not set; cannot resolve data format from metadata blocks")
        if isinstance(data_format, str):
            fmt_lower = data_format.lower()
            if fmt_lower in ("maxtwo", "max2"):
                data_format = "Maxwell"
        if not data_format:
            data_format = "Maxwell"  # a patch for the old metadata.json
            logging.info(f"Data format not found in metadata.json, default to Maxwell")
    if not os.path.isfile(parameter_path):
        params = DEFUALT_PARAMS
        logging.error(f"Note: parameters.json not available. Using updated default parameters for curation. {params}")
        
    else:
        params = utils.load_paramter(parameter_path)   # TODO: save with kilosort parameters to the parameter_setting.json

    rec_filtered = extract_recording(rec_path=rec_file, output_folder=output_folder, format=data_format)
    if rec_filtered == -1:
        logging.error("Error: Recording not readable.")
        sys.exit()
    ks = RunKilosort(rec=rec_filtered, output_folder=output_folder)
    base_kilosort_params = dict(kilosort_params)
    ks_status = ks.run_sorting()
    if ks_status != 0:
        retry_nt = _compute_retry_nt(rec_filtered)
        if retry_nt is not None:
            logging.warning(
                f"Kilosort failed; retrying once with smaller NT={retry_nt} (was {kilosort_params['NT']})"
            )
            kilosort_params['NT'] = retry_nt
            ks_status = ks.run_sorting()
        if ks_status != 0:
            fallback_nt = _compute_retry_nt(rec_filtered, min_batches=32, min_nt=8192)
            if fallback_nt is not None:
                logging.warning(
                    "Kilosort failed again; retrying with conservative params "
                    f"(NT={fallback_nt}, nfilt_factor=2, ntbuff=32)"
                )
                _apply_conservative_kilosort_params(base_kilosort_params, fallback_nt)
                ks_status = ks.run_sorting()
        if ks_status != 0:
            crossings = ks.get_last_threshold_crossings()
            if allow_empty_on_kilosort_fail and crossings is not None and crossings < ks_min_crossings:
                logging.warning(
                    f"Kilosort failed after retries with low activity "
                    f"(threshold crossings={crossings} < {ks_min_crossings}); "
                    "writing failure marker and skipping curation."
                )
                os.makedirs(output_folder, exist_ok=True)
                marker = os.path.join(output_folder, "KILOSORT_FAILED_LOW_ACTIVITY.txt")
                with open(marker, "w") as f:
                    f.write(
                        f"Kilosort failed after retries.\n"
                        f"Threshold crossings: {crossings}\n"
                        f"Dataset: {experiment}\n"
                    )
                sys.exit(0)
            logging.error("Kilosort failed after retries; aborting pipeline before curation.")
            sys.exit(ks_status)

    if not os.path.isfile(os.path.join(output_folder, "spike_times.npy")):
        logging.error("Kilosort outputs missing (spike_times.npy not found); aborting pipeline before curation.")
        sys.exit(1)

    # auto-curation
    curation_folder = os.path.join(inter_folder, "sorted/curation")
    if not os.path.isdir(curation_folder):
        os.makedirs(curation_folder)
    qm = QualityMetrics(base_folder=curation_folder, rec=rec_filtered, 
                        phy_folder=output_folder, rec_path=rec_file, data_format=data_format,
                        min_snr=params["min_snr"], min_fr=params["min_fr"], max_isi_viol=params["max_isi_viol"], 
                        default=True)
    spike_data = qm.compile_data()
    logging.info(f"{len(spike_data['neuron_data'])} units after quality metrics check")

    if len(spike_data["neuron_data"]) == 0:
        logging.warning("No units remain after quality metrics; skipping curation packaging and plotting.")
        # Ensure expected output dirs exist so downstream steps don't fail
        os.makedirs(os.path.join(inter_folder, "sorted/figure"), exist_ok=True)
        os.makedirs(os.path.join(inter_folder, "sorted/curation", "curated"), exist_ok=True)
        sys.exit(0)

    if REMOVE_SINGLE_CHANNEL:
        # remove the single channel units
        spike_data_new = utils.remove_single_channel_unit(spike_data)
        logging.info(f"{len(spike_data_new['neuron_data'])} units after removing single channel units")
    else:
        spike_data_new = spike_data
        logging.info(f"REMOVE_SINGLE_CHANNEL set to {REMOVE_SINGLE_CHANNEL}, bypass single channel unit check")
    # package the qm file for upload
    qm_file = qm.package_cleaned(spike_data_new)
    # logging.info("qm file dir", qm_file)
    # upload the qm_file in run.sh

    # plot some figures (plotly)
    # save the figure and upload
    figure_folder = os.path.join(inter_folder, "sorted/figure")  
    if not os.path.isdir(figure_folder):
        os.makedirs(figure_folder)
    
    # map, map with sttc; raster; individual spike footprints; stats for fr, isi, sttc; raster with burst, stats for burst
    pe = plots.PlotlyEphys(spike_data_new, bin_size=0.05, win=5, avg=False, win_tiling=0.02,
                           gaussian=True, sigma=5, burst_rms_thr=3, title=experiment, save_to=figure_folder)
    overview_figure = pe.plot_html_page()
    overview_figure.write_html(f"{figure_folder}/{experiment}_overview.html")
    ## also save the output parameter so later I can add/delete things on the figure
    overview_figure.write_json(f"{figure_folder}/{experiment}_overview.json")
    ## save individual figures as well (for each unit)
    sua_folder = os.path.join(figure_folder, "sua")
    if not os.path.isdir(sua_folder):
        os.makedirs(sua_folder)
    psua = plots_sua.PlotSUA(spike_data_new, title=experiment, save_to=sua_folder)
    psua.plot_sua()

    logging.info("All plots are saved.")

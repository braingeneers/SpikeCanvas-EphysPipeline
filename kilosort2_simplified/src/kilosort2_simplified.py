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

FORMAT_LIST = ["Maxwell", "mearec", "nwb"]
data_format = None

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

    def run_sorting(self):
        self.create_config()
        sorting = self.start_kilosort()
        if sorting != 0:
            logging.error("Error: Kilosort returned non-zero value.")
        else:
            kilosort_log = os.path.join(stdln_folder, "kilosort2.log")
            if os.path.isfile(kilosort_log):
                os.rename(kilosort_log, os.path.join(self.output_folder, "kilosort2.log"))

    def start_kilosort(self):
        logging.info("Start running Kilosort...")
        kilosort_shell = os.path.join(stdln_folder, stdln_script)
        os.chdir(stdln_folder)
        # TODO: check where the kilosort2.log is. This file was not packaged with phy files previously
        psort = subprocess.Popen(["bash", kilosort_shell, runtime_folder, self.output_folder])
        # wait until subprocess finish
        ret = psort.wait()
        return ret

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
        rec = se.read_maxwell(rec_path)
    elif format == "nwb":
        rec = se.read_nwb(rec_path)
    # filter and convert to binary recording
    rec_filter = sp.bandpass_filter(rec, freq_min=band_min, freq_max=band_max, dtype="float32")
    binary_file_path = os.path.join(output_folder, 'recording.dat')
    se.BinaryRecordingExtractor.write_recording(
        rec_filter, file_paths=binary_file_path,
        dtype='int16', total_memory=kilosort_params["total_memory"],
        n_jobs=kilosort_params["n_jobs_bin"],
        verbose=False, progress_bar=True)
    return rec_filter

if __name__ == "__main__":
    output_folder = os.path.join(inter_folder, "sorted/kilosort2")
    log = os.path.join(output_folder, "run_kilosort2.log")
    setup_logging(log)
    setup_hdf5()

    # get format from metadata
    experiment = sys.argv[1]
    metadata_path = "/project/SpikeSorting/metadata.json"
    parameter_path = "/project/SpikeSorting/parameters.json"
    if not os.path.isfile(metadata_path):
        logging.error("Error: metadata.json not available. Data format default to Maxwell.")
        data_format = "Maxwell"
    else:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        if (experiment in metadata["ephys_experiments"]) and \
                ("data_format" in metadata["ephys_experiments"][experiment]):
            data_format = metadata["ephys_experiments"][experiment]["data_format"]
        if not data_format:
            data_format = "Maxwell"  # a patch for the old metadata.json
    if not os.path.isfile(parameter_path):
        params = {"min_snr": 5, "min_fr": 0.1, "max_isi_viol": 0.2}
        logging.error(f"Error: parameters.json not available. Using default parameters for curation. {params}")
        
    else:
        params = utils.load_paramter(parameter_path)   # TODO: save with kilosort parameters to the parameter_setting.json

    rec_filtered = extract_recording(rec_path=rec_file, output_folder=output_folder, format=data_format)
    if rec_filtered == -1:
        logging.error("Error: Recording not readable.")
        sys.exit()
    ks = RunKilosort(rec=rec_filtered, output_folder=output_folder)
    ks.run_sorting()

    # auto-curation
    curation_folder = os.path.join(inter_folder, "sorted/curation")
    if not os.path.isdir(curation_folder):
        os.makedirs(curation_folder)
    qm = QualityMetrics(base_folder=curation_folder, rec=rec_filtered, phy_folder=output_folder,
                        min_snr=params["min_snr"], min_fr=params["min_fr"], max_isi_viol=params["max_isi_viol"], 
                        default=True)
    spike_data = qm.compile_data()
    logging.info(f"{len(spike_data['neuron_data'])} units after quality metrics check")
    # remove the single channel units
    spike_data_new = utils.remove_single_channel_unit(spike_data)
    logging.info(f"{len(spike_data_new['neuron_data'])} units after removing single channel units")
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
                           gaussian=True, sigma=5, burst_rms_thr=3, title=experiment)
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

    

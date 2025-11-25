import numpy as np
import spikeinterface.extractors as se

# List of data files you want to spike sort
rec_file = "/project/SpikeSorting/Trace"

# List of intermediate folders where tmp and output files are saved
inter_folder = "/project/SpikeSorting/inter"

# # List of output folders where final matlab files are saved.
# # Matlab files will have the same name as recording files but will end with _sorted.mat
# matlab_folder = "/project/SpikeSorting/output"


# standalone executable absolute path
stdln_folder = "/project/matlab/"
stdln_script = "run_kilosort_compiled.sh"
# MATLAB runtime directory as required for running the standalone shell script
runtime_folder = "/usr/local/MATLAB/MATLAB_Runtime/v97"

# Set toolbox paths
kilosort_path = "/project/matlab"
hdf5_plugin_path = '/project/src/'

# preprocess parameters
band_min, band_max = 300, 6000

# Sorter params
kilosort_params = {
    'detect_threshold': 6,
    'projection_threshold': [10, 4],
    'preclust_threshold': 8,
    'car': 1,
    'minFR': 0.1,
    'minfr_goodchannels': 0.1,
    'freq_min': 150,
    'sigmaMask': 30,
    'nPCs': 3,
    'ntbuff': 64,
    'nfilt_factor': 4,
    'NT': 65600,
    'keep_good_only': False,
    'total_memory': "2G",
    'n_jobs_bin': 64,
    'trange': [float(0), float('inf')]
}
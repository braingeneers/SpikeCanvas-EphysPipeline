# curate by spikeinterface quality metrics and curation
import spikeinterface as si
import spikeinterface.extractors as se
import spikeinterface.core as sc
import spikeinterface.curation as curation
import spikeinterface.qualitymetrics as sqm
from spikeinterface.extractors.neoextractors import MaxwellRecordingExtractor
import spikeinterface.preprocessing as spre
import sys
import posixpath
import os
import shutil
from utils import *
import logging
import h5py
import numpy as np

# BUCKET = "s3://braingeneers/ephys/"
JOB_KWARGS = dict(n_jobs=10, progress_bar=True)
os.environ["HDF5_PLUGIN_PATH"] = os.getcwd()

# Old default parameters
# DEFUALT_PARAMS = {"min_snr": 5,
#                   "min_fr": 0.1,
#                   "max_isi_viol": 0.2}
# New default parameters using Hunter's suggestion
DEFUALT_PARAMS =  {"min_snr": 3,
                  "min_fr": 0.1,
                  "max_isi_viol": 0.5}


class QualityMetrics:
    """
    curation by quality metrics using spikeinterface API

    """

    def __init__(self, base_folder, rec, phy_folder, rec_path, 
                 data_format=None,
                 min_snr=DEFUALT_PARAMS["min_snr"], 
                 min_fr=DEFUALT_PARAMS["min_fr"], 
                 max_isi_viol=DEFUALT_PARAMS["max_isi_viol"],
                 default=True):

        self.redundant_pairs = None
        self.extract_path = None
        self.base_folder = base_folder
        self.phy_folder = phy_folder
        self.clean_folder = posixpath.join(base_folder, "cleaned_waveforms")
        phy_result = se.KiloSortSortingExtractor(phy_folder)
        self.phy_result = phy_result.remove_empty_units()
        self._rec_path = rec_path
        self._snr_thres = min_snr
        self._fr_thres = min_fr
        self._isi_viol_thres = max_isi_viol
        self.data_format = data_format

        self.we = self.extract_waveforms(rec, max_spikes=500)
        print("waveforms", self.we)

        if default:
            self.curated_ids, self.all_remove_ids = self.default_curation()
            logging.info("Saving cleaned units...")
            self.we_clean = self.we.select_units(self.curated_ids, self.clean_folder)
            logging.info(f"Saved, {self.we_clean}")

    def default_curation(self):
        all_remove_ids = set()
        ids = self.curate_by_snr()
        all_remove_ids.update(ids)
        ids = self.curate_by_isi()
        all_remove_ids.update(ids)
        ids = self.curate_by_fr()
        all_remove_ids.update(ids)
        # ids = self.curate_by_redundant()  # output the cleaned units and the original/remove list
        # all_remove_ids.update(ids)
        # ids = self.curate_by_channel(ids)   # remove single channel units

        self.redundant_pairs = self.curate_by_redundant()  # not actually remove the redundant onessort_template_amplitude

        logging.info(f"Total number of units to remove: {len(all_remove_ids)}")

        curated_excess = curation.remove_excess_spikes(self.we.sorting, self.we.recording)
        self.we.sorting = curated_excess
        return curated_excess.unit_ids, list(all_remove_ids)

    def extract_waveforms(self, rec_pre, ms_before=2., ms_after=3., max_spikes=500):
        self.extract_path = posixpath.join(self.base_folder, "extract_waveforms")
        if os.path.isdir(self.extract_path):
            we = sc.WaveformExtractor.load(folder=self.extract_path)
        else:
            we = sc.WaveformExtractor(rec_pre, self.phy_result, self.base_folder, allow_unfiltered=False)
            we.set_params(ms_before=ms_before, ms_after=ms_after, max_spikes_per_unit=max_spikes)
            we.run_extract_waveforms(**JOB_KWARGS)
            we.save(self.extract_path, overwrite=True)
        return we

    # def compute_noise_level(self):
    #     rec_pre = self.prepare_rec()
    #     noise_levels_mv = si.get_noise_levels(rec_pre, return_scaled=True)
    #     return noise_levels_mv

    def curate_by_snr(self):
        num_units = len(self.we.unit_ids)
        snr = sqm.compute_snrs(self.we)
        remove_ids = []
        for k, v in snr.items():
            if v < self._snr_thres:
                remove_ids.append(k)
        cleaned_sorting = self.we.sorting.remove_units(remove_ids)
        self.we.sorting = cleaned_sorting
        logging.info(f"Curated by SNR of {self._snr_thres} rms. "
                     f"Remove number of units: {len(remove_ids)}/{num_units}")
        return remove_ids

    def curate_by_isi(self):
        num_units = len(self.we.unit_ids)
        isi_viol_ratio, isi_viol_num = sqm.compute_isi_violations(self.we)
        remove_ids = []
        for k, v in isi_viol_ratio.items():
            if v > self._isi_viol_thres:
                remove_ids.append(k)
        cleaned_sorting = self.we.sorting.remove_units(remove_ids)
        self.we.sorting = cleaned_sorting
        logging.info(f"Curated by ISI violation (Hill method) "
                     f"of {self._isi_viol_thres}/1 of 1.5 ms refactory period. "
                     f"Remove number of units: {len(remove_ids)}/{num_units}")
        return remove_ids

    def curate_by_fr(self):
        num_units = len(self.we.unit_ids)
        firing_rate = sqm.compute_firing_rates(self.we)
        remove_ids = []
        for k, v in firing_rate.items():
            if v < self._fr_thres:
                remove_ids.append(k)
        cleaned_sorting = self.we.sorting.remove_units(remove_ids)
        self.we.sorting = cleaned_sorting
        logging.info(f"Curated by firing rate of {self._fr_thres} Hz. "
                     f"Remove number of units: {len(remove_ids)}/{num_units}")
        return remove_ids

    def curate_by_redundant(self):
        num_units = len(self.we.unit_ids)
        curated_redundant, redundant_unit_pairs = \
            curation.remove_redundant_units(self.we, align=False,
                                            remove_strategy="max_spikes", extra_outputs=True)
        print("done redundant")

        remove_ids = np.setdiff1d(self.we.sorting.unit_ids, curated_redundant.unit_ids)
        logging.info(f"Curated by checking redundant units. "
                     f"Remove number of units: {len(remove_ids)}/{num_units}")
        # self.we.sorting = curated_redundant
        # return remove_ids
        return redundant_unit_pairs

    def package_cleaned(self, spike_data=None):
        if not spike_data:
            spike_data = self.compile_data()
        curated_file = 'qm.npz'
        curated_folder = posixpath.join(self.base_folder, "curated")
        if not os.path.isdir(curated_folder):
            os.mkdir(curated_folder)
        qm_npz = posixpath.join(curated_folder, curated_file)
        np.savez(qm_npz, **spike_data)
        return qm_npz

    def compile_data(self, n=12):
        """
        compile the cleaned sorting to npz with braingeneers compatible structure
        """
        templates = self.we_clean.get_all_templates()
        clusters = self.we_clean.unit_ids
        nc = len(clusters)
        logging.info(f"Found {nc} clusters, {clusters}")
        channels = self.we_clean.recording.get_channel_ids()
        positions = self.we_clean.recording.get_channel_locations()
        best_channels = get_best_channel_cluster(clusters, channels, templates)
        phy_ids = np.load(os.path.join(self.phy_folder, "spike_clusters.npy"))
        amplitudes = np.load(os.path.join(self.phy_folder, "amplitudes.npy"))
        neuron_dict = dict.fromkeys(np.arange(nc), None)
        for i in range(nc):
            c = clusters[i]
            amps = amplitudes[phy_ids == c]
            waveforms_all = self.we_clean.get_waveforms(unit_id=c)
            temp = templates[i]
            sorted_idx = sort_template_amplitude(temp)[:n]
            temp = temp.T
            best_idx = sorted_idx[0]
            waveforms = waveforms_all[:, :, best_idx]
            neuron_dict[i] = {"cluster_id": c, 
                              "channel": best_channels[c],
                              "position": positions[best_idx],
                              "template": temp[best_idx],
                              "amplitudes": amps,
                              "waveforms": waveforms,
                              "neighbor_channels": channels[sorted_idx],
                              "neighbor_positions": positions[sorted_idx],
                              "neighbor_templates": temp[sorted_idx]
                              }
        if self.data_format == "Maxwell":
            logging.info(f"Reading electrode configuration for {self.data_format} data format")
            config = read_maxwell_mapping(self._rec_path)
        else:
            logging.info(f"Electrode configuration not available for {self.data_format} data format")
            config = {}
        spike_data = {"train": {c: self.we_clean.sorting.get_unit_spike_train(c)
                                for c in clusters},
                      "neuron_data": neuron_dict,
                      "config": config,
                      "redundant_pairs": self.redundant_pairs,
                      "fs": self.we_clean.recording.sampling_frequency}
        return spike_data


def prepare_rec(rec_path, low=300., high=6000., common_ref=True):
    rec = MaxwellRecordingExtractor(file_path=rec_path)
    gain_uv = read_maxwell_gain(rec_path)
    rec_scale = spre.ScaleRecording(rec, gain=gain_uv)
    rec_filt = spre.bandpass_filter(rec_scale, freq_min=low, freq_max=high)
    if common_ref:
        rec_cmr = spre.common_reference(rec_filt, verbose=True)
        return rec_cmr
    else:
        return rec_filt


def read_maxwell_gain(h5_file):
    dataset = h5py.File(h5_file, 'r')
    if 'mapping' in dataset.keys():
        # Legacy MaxOne format
        gain_uv = dataset['settings']['lsb'][0] * 1e6
    else:
        # Dynamically find the correct well identifier for MaxTwo data
        rec_group = dataset['recordings']['rec0000']
        # Find well groups (well000, well001, etc.)
        well_keys = [key for key in rec_group.keys() if key.startswith('well')]
        if not well_keys:
            raise KeyError("No well groups found in the recording")
        
        # Sort well keys to ensure consistent ordering (well000, well001, etc.)
        well_keys.sort()
        well_key = well_keys[0]  # Use the first well found
        
        logging.info(f"Found wells: {well_keys}, using: {well_key}")
        gain_uv = rec_group[well_key]['settings']['lsb'][0] * 1e6
    return gain_uv


def read_maxwell_mapping(h5_file):
    with h5py.File(h5_file, 'r') as dataset:
        if 'version' and 'mxw_version' in dataset.keys():
            # Dynamically find the correct well identifier for MaxTwo data
            rec_group = dataset['recordings']['rec0000']
            # Find well groups (well000, well001, etc.)
            well_keys = [key for key in rec_group.keys() if key.startswith('well')]
            if not well_keys:
                raise KeyError("No well groups found in the recording")
            
            # Sort well keys to ensure consistent ordering (well000, well001, etc.)
            well_keys.sort()
            well_key = well_keys[0]  # Use the first well found
            
            logging.info(f"Found wells: {well_keys}, using: {well_key}")
            mapping = rec_group[well_key]['settings']['mapping']
            config = {'pos_x': np.array(mapping['x']),
                      'pos_y': np.array(mapping['y']),
                      'channel': np.array(mapping['channel']),
                      'electrode': np.array(mapping['electrode'])}
        else:
            # Legacy MaxOne format
            mapping = dataset['mapping']
            config = {'pos_x': np.array(mapping['x']),
                      'pos_y': np.array(mapping['y']),
                      'channel': np.array(mapping['channel']),
                      'electrode': np.array(mapping['electrode'])}
    return config


def get_parent_data(neuron_dict):
    parent_id_dict = {v["cluster_id"]: v for _, v in neuron_dict.items()}
    parent_ids = list(parent_id_dict.keys())
    return parent_ids, parent_id_dict


def select_units(spike_train, neuron_dict, selected_ids):
    parent_ids, parent_dict = get_parent_data(neuron_dict)
    update_dict = {}
    update_trains = []
    for i in range(len(selected_ids)):
        id = selected_ids[i]
        update_dict[i] = parent_dict[id]
        update_trains.append(spike_train[parent_ids.index(id)])
    return update_trains, update_dict


def remove_units(spike_train, neuron_dict, removed_ids):
    parent_ids, _ = get_parent_data(neuron_dict)
    selected_ids = np.setdiff1d(parent_ids, removed_ids)
    update_trains, update_dict = select_units(spike_train, neuron_dict, selected_ids)
    return update_trains, update_dict

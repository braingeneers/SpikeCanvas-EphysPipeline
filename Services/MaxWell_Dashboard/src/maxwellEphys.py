# class of maxwell ephys data for displaying on the dashbaord
from braingeneers.analysis import SpikeData
import numpy as np
import pandas as pd
import braingeneers.utils.s3wrangler as wr
import zipfile
import braingeneers.utils.smart_open_braingeneers as smart_open
import io
import scipy.ndimage as simg
import scipy.signal as ssig


class MaxWellEphys:
    def __init__(self, data_path, fr_coef, sttc_delta=0.02, sttc_thr=0.35,
                 burst_rms_scaler=2, binary_bin_size=0.001,
                 before_peak_s=0.25, after_peak_s=0.5, between_burst=0.8,
                 burst_edge=0.9,
                 fs=20000.0):
        """
        load spike sorted data from s3 using analysis.read_phy_files()
        Generate dataframe for plotting functions
        Data loading priority: 
        1. _acqm.zip (latest auto-curation)
        2. _qm_rd.zip (quality metrics with manual curation) 
        3. _qm.zip (quality metrics auto-curation)
        4. _phy.zip (uncurated spike sorting results)
        """
        data_path = parse_derived_path(data_path)
        print(f"Load data from {data_path}")
        if (data_path.endswith("_qm.zip") or 
            data_path.endswith("_qm_rd.zip") or 
            data_path.endswith("_acqm.zip")):
            self.ephys_data = load_curation(data_path)
        else:
            self.ephys_data = read_phy_files(data_path)
        self.spike_times = self.ephys_data.train
        self.neuron_dict = self.ephys_data.neuron_data[0]
        self.metadata = self.ephys_data.metadata[0]
        self.fs = fs
        self.fr_coef = fr_coef
        self.sttc_delta = sttc_delta
        self.sttc_thr = sttc_thr
        self.binary_bin_size = binary_bin_size
        self.rms_scaler = burst_rms_scaler
        self.before_peak = before_peak_s
        self.after_peak = after_peak_s
        self.between_bursts = between_burst
        self.burst_edge = burst_edge
        self.num_burst = 0

    def get_data_dict(self, key):
        ch = self.neuron_dict[key]['channel']
        pos = self.neuron_dict[key]['position']
        temp_chs = self.neuron_dict[key]['neighbor_channels']
        temp_pos = self.neuron_dict[key]['neighbor_positions']
        templates = self.neuron_dict[key]['neighbor_templates']
        return ch, pos, temp_chs, temp_pos, templates

    def get_amplitudes(self, key):
        ch = self.neuron_dict[key]['channel']
        amplitudes = self.neuron_dict[key]['amplitudes']
        return ch, amplitudes

    def channel_map(self):
        """
        Create data for channel map
        :return:
        """
        config = np.asarray(list(self.metadata.values()))
        cluster_num = np.asarray(list(self.neuron_dict.keys())) + 1  # start from 1 instead of 0
        fire_rate = self.ephys_data.rates(unit='Hz')
        self.chn_pos = np.asarray([self.neuron_dict[k]['position']
                                   for k in self.neuron_dict.keys()])
        chn_map = {"cluster_number": cluster_num,
                   "pos_x": self.chn_pos[:, 0],
                   "pos_y": self.chn_pos[:, 1],
                   "fire_rate": fire_rate}
        chn_map_df = pd.DataFrame(data=chn_map)
        self.sttc = self.ephys_data.spike_time_tilings(delt=self.sttc_delta)
        return config, chn_map_df, self.sttc

    def functional_pairs(self):
        """
        Create functional pairs
        :return:
        """
        paired_direction = {"start_cls": [], "end_cls": [],
                            "start_pos": [], "end_pos": [],
                            "sttc": [], "latency": []}
        for i in range(len(self.spike_times) - 1):  # i, j are the indices to spike_times
            for j in range(i + 1, len(self.spike_times)):
                if self.sttc[i][j] >= self.sttc_thr:
                    lat = latency(self.spike_times[i], self.spike_times[j], threshold=self.sttc_delta)
                    pos_count = len(list(filter(lambda x: (x >= 0), lat)))
                    if abs(pos_count - (len(lat) - pos_count)) > 0.8 * len(lat):
                        if np.mean(lat) > 0:
                            pair = [i, j, self.chn_pos[i], self.chn_pos[j], self.sttc[i][j], np.mean(lat)]
                        else:
                            pair = [j, i, self.chn_pos[j], self.chn_pos[i], self.sttc[i][j], abs(np.mean(lat))]
                        for ind, k in enumerate(paired_direction.keys()):
                            paired_direction[k].append(pair[ind])
        paired_dir_df = pd.DataFrame(data=paired_direction)
        return paired_dir_df

    def raster(self):
        """
        Create raster data with aggregated firing rate
        :return:
        """
        raster_x, raster_y = [], []
        for i in range(self.ephys_data.N):
            raster_x.extend(self.spike_times[i])
            raster_y.extend([i + 1] * len(self.spike_times[i]))

        fr_bins, firing_rate = get_population_fr(self.spike_times)
        return raster_x, raster_y, fr_bins, firing_rate

    # TODO: move to make_texts class for showing metadata
    def print_ephys(self):
        print("Recording length: {} minutes".format(self.ephys_data.length / 60))
        print("Number of neurons: ", len(self.spike_times))

    def select_neighbor_channels(self, key, pitch=17.5, nelec=2):
        ch, position, neighbor_channels, neighbor_positions, _ = self.get_data_dict(key)
        selected_channels = []
        selected_positions = []
        for i in range(len(neighbor_channels)):
            chn_pos = neighbor_positions[i]
            if position[0] - nelec * pitch <= chn_pos[0] <= position[0] + nelec * pitch \
                    and position[1] - nelec * pitch <= chn_pos[1] <= position[1] + nelec * pitch:
                selected_channels.append(neighbor_channels[i])
                selected_positions.append(chn_pos)
        return selected_channels, selected_positions

    def two_step_smooth(self, win=20, sigma=20):
        raster = self.ephys_data.raster(bin_size=self.binary_bin_size)
        raster_sum = np.sum(raster, axis=0)
        smoothed = moving_average(raster_sum, win=win)
        smoothed_gauss = simg.gaussian_filter(smoothed, sigma)
        smoothed_gauss /= self.binary_bin_size
        bins = np.arange(0, len(smoothed_gauss) * self.binary_bin_size, self.binary_bin_size)
        return bins, smoothed_gauss

    def find_peak_loc(self, remove_edge=True):
        bins, pop_fr = self.two_step_smooth()
        bw = self.binary_bin_size
        rms = np.sqrt(np.mean(pop_fr ** 2))
        peak_thr = rms * self.rms_scaler
        peak_indices, _ = ssig.find_peaks(pop_fr, height=peak_thr,
                                          distance=self.between_bursts / bw)
        if len(peak_indices) == 0:
            return [], []
        # check the location of indices, remove the ones at
        # the beginning and the end that are not complete
        if remove_edge:
            peak_indices = peak_indices[(peak_indices > self.before_peak / bw) &
                                        (peak_indices < len(bins) - self.after_peak / bw)]
        self.num_burst = len(peak_indices)
        return pop_fr, peak_indices

    def burst_width(self, remove_edge=True):
        """
        get burst width using scipy peak_widths function
        This can return a pretty wide burst depending on the smooth window
        """
        pop_fr, peak_indices = self.find_peak_loc(remove_edge=remove_edge)
        peak_widths_tuple = ssig.peak_widths(pop_fr, peak_indices,
                                             rel_height=self.burst_edge)
        duration = peak_widths_tuple[0] * self.binary_bin_size  # width of (1-burst_edge) peak value (s)
        burst_values = tuple([peak_widths_tuple[1:][0],  # peak value (Hz)
                              peak_widths_tuple[1:][1] * self.binary_bin_size,  # burst_start (s)
                              peak_widths_tuple[1:][2] * self.binary_bin_size])  # burst_end (s)

        return duration, burst_values


def latency(train_1, train_2, threshold=0.02):
    """
    Find latency of train_2 to train_1 by labeling the two spike trains.
    If the latency is greater than the threshold, move to the next spike time.
    The threshold can be the sttc window size.
    :return: a list of latencies
    """
    label_1 = [0] * len(train_1)
    label_2 = [1] * len(train_2)
    train_inter = list(zip(label_1, train_1)) + list(zip(label_2, train_2))
    train_inter.sort(key=lambda a: a[1])

    lat = []
    i, diff, thr = 0, 0, threshold
    label = train_inter[0][0]
    coef = 1 if label == label_1[0] else -1
    while i < len(train_inter) - 1:
        if train_inter[i][0] != train_inter[i + 1][0]:
            diff = train_inter[i + 1][1] - train_inter[i][1]
            if diff > thr:
                i += 1
            else:
                if train_inter[i][0] == label:
                    lat.append(diff * coef)
                else:
                    lat.append(-diff * coef)
                i += 2
        else:
            i += 1
    return lat


def moving_fr_rate(spike_times: list, rec_length=None, bin_size=0.1):
    spike_times_all = np.sort(np.hstack(spike_times))
    if rec_length is None:
        rec_length = spike_times_all[-1]
    bin_num = int(rec_length // bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    moving = [np.histogram(spike_times_all, bins + i)[0] for i in range(int(bin_size * 1000))]
    moving_fr = np.mean(moving, axis=0) / bin_size  # hz
    return bins, moving_fr


def moving_average(data, win=5):
    """
    Save function to matlab movmean
    """
    data = np.array(data)
    assert data.ndim == 1, "input must be one-dimension"
    step = np.ceil(win / 2).astype(int)
    movmean = np.empty(data.shape)
    i = 0
    while i < movmean.shape[0]:
        for s in range(step, win):
            res = np.mean(data[:s])
            movmean[i] = res
            i += 1
        for s in range(data.shape[0] - i):
            res = np.mean(data[s:s + win])
            movmean[i] = res
            i += 1
    return movmean


def get_population_fr(trains: list, bin_size=0.1, w=5, average=False):
    N = len(trains)
    if N == 0:
        print("Input train is empty")
        return [], []
    trains = np.hstack(trains)
    rec_length = np.max(trains)
    bin_num = int(rec_length // bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    fr = np.histogram(trains, bins)[0] / bin_size
    fr_avg = np.convolve(fr, np.ones(w), 'same') / w
    if average:
        fr_avg /= N
    return bins, fr_avg


def load_curation(qm_path):
    with smart_open.open(qm_path, 'rb') as f:
        with zipfile.ZipFile(f, 'r') as f_zip:
            qm = f_zip.open("qm.npz")
            data = np.load(qm, allow_pickle=True)
            spike_times = data["train"].item()
            fs = data["fs"]
            train = [times / fs for _, times in spike_times.items()]
            config = data["config"].item()
            neuron_data = data["neuron_data"].item()
    return SpikeData(train=train, neuron_data={0: neuron_data}, metadata={0: config})


def parse_derived_path(data_path):
    if "original/data" in data_path:
        data_path = data_path.replace("original/data", "derived/kilosort2")
        if data_path.endswith(".raw.h5"):
            data_path = data_path.split(".raw.h5")[0]

        # Check for curated data in order of preference (latest first)
        for end in ["_acqm.zip", "_qm_rd.zip", "_qm.zip"]:
            qm_path = data_path + end
            if wr.does_object_exist(qm_path):
                return qm_path

        # Fall back to uncurated phy data
        phy_path = data_path.replace(".raw.h5", "_phy.zip")
        if wr.does_object_exist(phy_path):
            return phy_path
        
        # No processed data found
        return None
    else:
        return data_path


def read_phy_files(path: str, fs=20000.0):
    """
    :param path: a s3 or local path to a zip of phy files.
    :return: SpikeData class with a list of spike time lists and neuron_data.
            neuron_data = {0: neuron_dict, 1: config_dict}
            neuron_dict = {"new_cluster_id": {"channel": c, "position": (x, y),
                            "amplitudes": [a0, a1, an], "template": [t0, t1, tn],
                            "neighbor_channels": [c0, c1, cn],
                            "neighbor_positions": [(x0, y0), (x1, y1), (xn,yn)],
                            "neighbor_templates": [[t00, t01, t0n], [tn0, tn1, tnn]}}
            config_dict = {chn: pos}
    """
    assert path[-3:] == 'zip', 'Only zip files supported!'
    with smart_open.open(path, 'rb') as f0:
        f = io.BytesIO(f0.read())

        with zipfile.ZipFile(f, 'r') as f_zip:
            assert 'params.py' in f_zip.namelist(), "Wrong spike sorting output."
            with io.TextIOWrapper(f_zip.open('params.py'), encoding='utf-8') as params:
                for line in params:
                    if "sample_rate" in line:
                        fs = float(line.split()[-1])
            clusters = np.load(f_zip.open('spike_clusters.npy')).squeeze()
            templates = np.load(f_zip.open('templates.npy'))  # (cluster_id, samples, channel_id)
            channels = np.load(f_zip.open('channel_map.npy')).squeeze()
            templates_w = np.load(f_zip.open('templates.npy'))
            wmi = np.load(f_zip.open('whitening_mat_inv.npy'))
            spike_templates = np.load(f_zip.open('spike_templates.npy')).squeeze()
            spike_times = np.load(f_zip.open('spike_times.npy')).squeeze() / fs * 1e3  # in ms
            positions = np.load(f_zip.open('channel_positions.npy'))
            amplitudes = np.load(f_zip.open("amplitudes.npy")).squeeze()
            if 'cluster_info.tsv' in f_zip.namelist():
                cluster_info = pd.read_csv(f_zip.open('cluster_info.tsv'), sep='\t')
                cluster_id = np.array(cluster_info['cluster_id'])
                # select clusters using curation label, remove units labeled as "noise"
                # find the best channel by amplitude
                labeled_clusters = cluster_id[cluster_info['group'] != "noise"]
            else:
                labeled_clusters = np.unique(clusters)

    df = pd.DataFrame({"clusters": clusters, "spikeTimes": spike_times, "amplitudes": amplitudes})
    cluster_agg = df.groupby("clusters").agg({"spikeTimes": lambda x: list(x),
                                              "amplitudes": lambda x: list(x)})
    cluster_agg = cluster_agg[cluster_agg.index.isin(labeled_clusters)]

    cls_temp = dict(zip(clusters, spike_templates))
    neuron_dict = dict.fromkeys(np.arange(len(labeled_clusters)), None)

    # un-whitten the templates before finding the best channel
    templates = np.dot(templates_w, wmi)

    neuron_attributes = []
    for i in range(len(labeled_clusters)):
        c = labeled_clusters[i]
        temp = templates[cls_temp[c]]
        amp = np.max(temp, axis=0) - np.min(temp, axis=0)
        sorted_idx = [ind for _, ind in sorted(zip(amp, np.arange(len(amp))))]
        nbgh_chan_idx = sorted_idx[::-1][:12]
        nbgh_temps = temp.transpose()[sorted_idx]
        best_chan_temp = nbgh_temps[0]
        nbgh_channels = channels[nbgh_chan_idx]
        nbgh_postions = [tuple(positions[idx]) for idx in nbgh_chan_idx]
        best_channel = nbgh_channels[0]
        best_position = nbgh_postions[0]
        # neighbor_templates = dict(zip(nbgh_postions, nbgh_temps))
        cls_amp = cluster_agg["amplitudes"][c]
        neuron_dict[i] = {"cluster_id": c, "channel": best_channel, "position": best_position,
                          "amplitudes": cls_amp, "template": best_chan_temp,
                          "neighbor_channels": nbgh_channels, "neighbor_positions": nbgh_postions,
                          "neighbor_templates": nbgh_temps}
    config_dict = dict(zip(channels, positions))
    neuron_data = {0: neuron_dict}
    metadata = {0: config_dict}
    spikedata = SpikeData(list(cluster_agg["spikeTimes"]),
                          neuron_data=neuron_data,
                          metadata=metadata)
    return spikedata

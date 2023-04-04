# class of maxwell ephys data for displaying on the dashbaord
from braingeneers import analysis
import numpy as np
import pandas as pd


class MaxWellEphys:
    def __init__(self, phy_path, fr_coef, sttc_delta, sttc_thr, fs):
        """
        load spike sorted data from s3 using analysis.read_phy_files()
        :param phy_path: a s3 path
        :return: a list of spike_times as [spike_times] and neuron_data
        dictionary structured as {new_cluster_id:
        [channel_id, (chan_pos_x, chan_pos_y), [chan_template], {channel_id:cluster_templates}]}
        Generate dataframe for plotting functions
        """
        self.ephys_data = analysis.read_phy_files(phy_path)
        self.spike_times = self.ephys_data.train
        self.neuron_dict = self.ephys_data.neuron_data[0]
        self.metadata = self.ephys_data.metadata[0]
        self.fs = fs
        self.fr_coef = fr_coef
        self.sttc_delta = sttc_delta
        self.sttc_thr = sttc_thr

    def get_data_dict(self, key):
        ch = self.neuron_dict[key]['channel']
        pos = self.neuron_dict[key]['position']
        temp_chs = self.neuron_dict[key]['neighbor_channels']
        temp_pos = self.neuron_dict[key]['neighbor_positions']
        templates = self.neuron_dict[key]['neighbor_templates']
        return ch, pos, temp_chs, temp_pos, templates

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
            raster_x.extend(self.spike_times[i] / 1000)
            raster_y.extend([i + 1] * len(self.spike_times[i]))

        fr_bins, firing_rate = moving_fr_rate(self.spike_times)
        return raster_x, raster_y, fr_bins, firing_rate

    # TODO: move to make_texts class for showing metadata
    def print_ephys(self):
        print("Recording length: {} minutes".format(self.ephys_data.length / 1000 / 60))
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

# TODO: move to utils?
def latency(train_1, train_2, threshold=20):
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


def moving_fr_rate(spike_times: list, rec_length=None, bin_size=100):
    spike_times_all = np.sort(np.hstack(spike_times))
    if rec_length is None:
        rec_length = spike_times_all[-1]
    bin_num = int(rec_length // bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    moving = [np.histogram(spike_times_all, bins + i)[0] for i in range(bin_size)]
    moving_fr = np.mean(moving, axis=0) / bin_size * 1000  # hz
    return bins, moving_fr

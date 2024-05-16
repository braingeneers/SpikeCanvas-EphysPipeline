import numpy as np
import scipy
import ephysplus.utils as utils
from braingeneers.analysis import SpikeData

# remove duplicate units by running CCG -- this is very slow
# try sttc and spike times shift (latency) approach

class curate:
    def __init__(self, spike_data, ccg_win=[-10, 10], 
                 rms_thr=2, dist_thr=1, nspike_thr=0.8):
        self.sd = spike_data
        self.ccg_win = ccg_win
        self.rms_thr = rms_thr
        self.nspike_thr = nspike_thr
        self.dist_thr=dist_thr

    def binarize_train(self, trains: list, bin_size=0.001):
        rec_start = 0
        rec_length = np.max(np.hstack(trains))
        bin_num = int(rec_length// bin_size) + 1
        bins = np.linspace(rec_start, rec_length, bin_num)
        binned = [np.histogram(t, bins)[0] for t in trains]
        return binned


    def CCG(self, bt1, bt2):
        t_lags_shift = 0
        left_edge, right_edge = np.subtract(self.ccg_win, t_lags_shift)
        lags = np.arange(self.ccg_win[0], self.ccg_win[1] + 1)
        pad_width = min(max(-left_edge, 0), max(right_edge, 0))
        bt2_pad = np.pad(bt2, pad_width=pad_width, mode='constant')
        cross_corr = scipy.signal.fftconvolve(bt2_pad, bt1[::-1], mode="valid")
        return np.round(cross_corr), lags


    def find_redundant_pairs(self, i, j, pitch=17.5):
        """
        Use number of spikes, CCG and the distance of best channels to find redundant pairs
        sd is a SpikeData object; i,j are unit index 
        """
        st1, st2 = self.sd.train[i], self.sd.train[j]
        # TODO: change this condition to check the number of latencies
        # that below threshold between spikes
        # because one can have a redundant subset of the other one
        if min(len(st1), len(st2)) / max(len(st1), len(st2)) >= self.nspike_thr:  
            bt1, bt2 = self.binarize_train([st1, st2])
            ccg, lags = self.CCG(bt1=bt1, bt2=bt2)
            rms = np.sqrt(np.mean(ccg**2))
            if np.max(ccg) >= self.rms_thr*rms and abs(lags[np.argmax(ccg)]) <= 1:
                # check distance of the best channels
                pos1 = self.sd.neuron_data[0][i]["position"]
                pos2 = self.sd.neuron_data[0][j]["position"]
                distance = abs(np.linalg.norm(pos1-pos2))
                if distance <= self.dist_thr * np.sqrt(pitch**2):
                    return True
        else:
            return False
        
    def remove_redundant_units(self):
        redundant = []
        for i in range(self.sd.N-1):
            for j in range(i+1, self.sd.N):
                if self.find_redundant_pairs(i=i, j=j):
                    redundant.append((i, j))
        to_merge = utils.merge_lists(redundant)

        to_remove = []
        for units in to_merge:
            units = np.array(list(units))
            lengths = [self.sd.train[i].shape[0] for i in units]
            indices = np.setdiff1d(np.arange(len(units)), [np.argmax(lengths)])
            remove_units = units[indices]
            to_remove += list(remove_units)
        selected_units = np.setdiff1d(np.arange(self.sd.N), to_remove)
        selected_units = list(selected_units)
        
        filtered_train = [self.sd.train[s] for s in selected_units]
        filtered_neuron_data = {selected_units.index(s): self.sd.neuron_data[0][s] for s in selected_units}
        if self.sd.metadata is not None:
            metadata = self.sd.metadata
        filtered_sd = SpikeData(filtered_train, 
                                neuron_data={0: filtered_neuron_data},
                                metadata=metadata)
        return filtered_sd
    


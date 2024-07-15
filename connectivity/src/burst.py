import scipy.signal as ssig
import scipy.ndimage as simg
from scipy.ndimage import gaussian_filter1d
import numpy as np
import utils as utils
import logging

class Network:
    def __init__(self, spike_data,
                 smooth_win=20, smooth_sigma=20,
                 smooth_bin=0.001,
                 rms_scaler=2, burst_edge=0.9,
                 before_peak_s=0.25, after_peak_s=0.5, between_bursts=0.8,
                 binary_bin_size=0.001, ccg_win=50, func_latency=5, func_prob=0.00001,
                 verbose=True, unit="s"):
        """
        rms_scaler: burst peak threshold = fr_rms * rms_scalar
        burst_edge: the percent drop to the peak for detecting burst width
        backbone_spikes: a neuron has to firing at least this number of spikes in a burst
        backbone_burst_thr: a neuron has to fire at least thr*100% of bursts
        """
        self.train = spike_data["train"]
        self.rec_len = np.max([t[-1] for t in self.train])
        self.unit_count = len(self.train)
        logging.info(f"Got {self.unit_count} units for plotting")
        self.neuron_data = spike_data["neuron_data"]
        self.rms_scaler = rms_scaler
        self.burst_edge = burst_edge
        self.smooth_sigma = smooth_sigma
        self.bin_width = smooth_bin
        self.smooth_win = smooth_win
        self.before_peak = before_peak_s
        self.after_peak = after_peak_s
        self.between_bursts = between_bursts
        self.unit = unit
        self.num_burst = None
        self.binary_bin_size = binary_bin_size
        self.peak_thr = 0
        self.ccg_window = [-ccg_win, ccg_win]
        self.func_latency = func_latency
        self.func_prob = func_prob
        self.verbose = verbose

        self.sparse_train = utils.sparse_train(self.train, bin_size=self.binary_bin_size)
        if self.verbose:
            print(f"spare train shape {self.sparse_train.shape}")

    def two_step_smooth(self):
        sparse_sum = np.sum(self.sparse_train, axis=0)
        smoothed = utils.moving_average(sparse_sum, win=self.smooth_win)
        smoothed_gauss = simg.gaussian_filter(smoothed, self.smooth_sigma)
        smoothed_gauss /= self.binary_bin_size
        bins = np.arange(0, (len(smoothed_gauss)+1) * self.binary_bin_size, self.binary_bin_size)
        return bins, smoothed_gauss

    def find_peak_loc(self, two_step_smooth=True, remove_edge=True):
        if two_step_smooth:
            bins, pop_fr = self.two_step_smooth()
            bw = self.binary_bin_size
        else:
            bins, pop_fr = utils.get_population_fr(self.train,
                                                   bin_size=self.bin_width,
                                                   w=self.smooth_win)
            bw = self.bin_width
        logging.info(f"Max population rate {np.max(pop_fr)}")
        rms = np.sqrt(np.mean(pop_fr ** 2))
        self.peak_thr = rms * self.rms_scaler
        peak_indices, _ = ssig.find_peaks(pop_fr, height=self.peak_thr,
                                          distance=self.between_bursts / self.bin_width)
        if len(peak_indices) == 0:
            self.num_burst = 0
            return pop_fr, bins, []
        # check the location of indices, remove the ones at
        # the beginning and the end that are not complete
        if remove_edge:
            peak_indices = peak_indices[(peak_indices > self.before_peak / bw) &
                                        (peak_indices < len(bins) - self.after_peak / bw)]
        self.num_burst = len(peak_indices)
        return pop_fr, bins, peak_indices

    def burst_width(self, remove_edge=True):
        """
        get burst width using scipy peak_widths function
        This can return a pretty wide burst depending on the smooth window
        """
        pop_fr, _, peak_indices = self.find_peak_loc(remove_edge=remove_edge)
        peak_widths_tuple = ssig.peak_widths(pop_fr, peak_indices,
                                             rel_height=self.burst_edge)
        duration = peak_widths_tuple[0] * self.bin_width  # width of (1-burst_edge) peak value (s)
        burst_values = tuple([peak_widths_tuple[1:][0],  # peak value (Hz)
                              peak_widths_tuple[1:][1] * self.bin_width,  # burst_start (s)
                              peak_widths_tuple[1:][2] * self.bin_width])  # burst_end (s)

        return duration, burst_values

    def inter_burst_interval(self):
        _, burst_values = self.burst_width()
        ibi = burst_values[1][1:] - burst_values[2][:-1]
        return ibi

    def spike_time_tilings(self, delt=0.02):
        """
        Compute the full spike time tiling coefficient matrix.
        """
        T = self.rec_len
        num = len(self.train)
        ts = [utils._sttc_ta(ts, delt, T) / T for ts in self.train]

        ret = np.diag(np.ones(num))
        for i in range(num):
            for j in range(i + 1, num):
                ret[i, j] = ret[j, i] = utils._spike_time_tiling(
                    self.train[i], self.train[j], ts[i], ts[j], delt
                )
        return ret


    # TODO: output these figures together with the overview figure
    def functional_pair(self):
        """
        Get putative pre- and post-synaptic neuron pairs
        Take the first neuron as the presynaptic neuron
        so that the delay is positive
        """
        func_pairs = {}
        if self.unit_count < 2:
            return func_pairs
        for i in range(self.unit_count-1):
            for j in range(i+1, self.unit_count):
                counts, lags = utils.ccg(self.sparse_train[i],
                             self.sparse_train[j],
                             ccg_win=self.ccg_window)
                max_ind = np.argmax(counts)
                latency = lags[max_ind]
                if latency >= -self.func_latency and latency <= self.func_latency:
                    if max_ind != np.diff(self.ccg_window)//2:
                        # ccg_smth = gaussian_filter1d(counts, sigma=10)   
                        ccg_smth = utils.hollow_gaussian_filter(counts, sigma=10) 
                        lambda_slow_peak = ccg_smth[max_ind]
                        ccg_peak = int(counts[max_ind])
                        # estimate p_fast
                        p_fast_est = utils.p_fast(ccg_peak, lambda_slow_peak)
                        if self.verbose:
                            print(f"Putative functional pair {i}, {j}")
                            print(f"Cross correlation latency: {latency} ms, counts: {ccg_peak}, smoothed counts: {lambda_slow_peak}")
                            print(f"p_fast: {p_fast_est}")
                        if p_fast_est <= self.func_prob:    # test with self.func_prob = 10e-5
                            yield (i, j), {"latency": latency,
                                        "p_fast": p_fast_est,
                                        "ccg": counts,
                                        "lags": lags,
                                        "ccg_smth": ccg_smth}
                            

    
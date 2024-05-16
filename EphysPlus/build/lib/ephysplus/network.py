# characters of neuronal circuitry
# burst detection, get values of IBI and burst duration
# 1. find peak from population rate
# 2. use a large kernel to smooth the rate 
# 3. find peak width using the smoothed rate and peak index
#    width defined as 0.9 drop of the peak rate
from braingeneers.analysis import SpikeData
import scipy.signal as ssig
import scipy.ndimage as simg
import numpy as np
import ephysplus.utils as utils

class PopulationBurst(SpikeData):
    # TODO: smooth_win has to fit the burst width for each rec. 
    # What's a good value? --small window, big kernel? 
    def __init__(self, spike_trains, *, neuron_data={}, 
                 smooth_win=15, smooth_sigma=20, 
                 acc_smooth_win=5, acc_smooth_sigma=1,   # for scipy, sigma is 1/5 of matlab value
                 smooth_bin=0.001, 
                 rms_scaler=2, burst_edge=0.9,
                 before_peak_s=0.25, after_peak_s=0.5, between_bursts=0.8,
                 backbone_spikes=2, backbone_burst_thr=1, 
                 unit="s"):
        SpikeData.__init__(self, spike_trains, neuron_data=neuron_data)
        """
        rms_scaler: burst peak threshold = fr_rms * rms_scalar
        burst_edge: the percent drop to the peak for detecting burst width
        backbone_spikes: a neuron has to firing at least this number of spikes in a burst
        backbone_burst_thr: a neuron has to fire at least thr*100% of bursts
        """
        self.rms_scaler = rms_scaler
        self.burst_edge = burst_edge
        self.smooth_sigma = smooth_sigma
        self.bin_width = smooth_bin
        self.smooth_win = smooth_win
        self.acc_smooth_win = acc_smooth_win
        self.acc_smooth_sigma = acc_smooth_sigma
        self.before_peak = before_peak_s
        self.after_peak = after_peak_s
        self.between_bursts = between_bursts
        self.unit = unit
        self.backbone_spikes = backbone_spikes
        self.backbone_burst_thr = backbone_burst_thr
        self.num_burst = None
        self.binary_bin_size = 0.001

    def two_step_smooth(self, win=20, sigma=20):
        raster = self.raster(bin_size=self.binary_bin_size)
        raster_sum = np.sum(raster, axis=0)
        smoothed = moving_average(raster_sum, win=win)
        smoothed_gauss = simg.gaussian_filter(smoothed, sigma)
        smoothed_gauss /= self.binary_bin_size
        bins = np.arange(0, len(smoothed_gauss)*self.binary_bin_size, self.binary_bin_size)
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
        rms = np.sqrt(np.mean(pop_fr**2))
        peak_thr = rms * self.rms_scaler
        peak_indices, _ = ssig.find_peaks(pop_fr, height=peak_thr,
                                          distance=self.between_bursts/self.bin_width)  
        if len(peak_indices) == 0:
            self.num_burst = 0
            return [], []
        # check the location of indices, remove the ones at 
        # the beginning and the end that are not complete
        if remove_edge: 
            peak_indices = peak_indices[(peak_indices > self.before_peak/bw) &
                                        (peak_indices < len(bins)-self.after_peak/bw)]
        self.num_burst = len(peak_indices)
        return pop_fr, peak_indices


    def find_peak_loc_acc(self):
        bins, pop_fr = self.two_step_smooth(win=self.acc_smooth_win,
                                            sigma=self.acc_smooth_sigma)
        bw = self.binary_bin_size
        d, values = self.burst_width()
        start_end = np.dstack((values[1], values[2]))
        indices = np.searchsorted(bins, start_end)[0]
        base_indices = indices[:, 0]
        burst_sections = [pop_fr[ind[0]:ind[1]] for ind in indices]
        for i in range(len(burst_sections)):
            sec = burst_sections[i]
            max_ind = np.argmax(sec)
            base_indices[i] += max_ind
        return bins, base_indices
    

    def burst_width(self, remove_edge=True): 
        """
        get burst width using scipy peak_widths function
        This can return a pretty wide burst depending on the smooth window
        """
        pop_fr, peak_indices = self.find_peak_loc(remove_edge=remove_edge)
        peak_widths_tuple = ssig.peak_widths(pop_fr, peak_indices, 
                                       rel_height=self.burst_edge)
        duration = peak_widths_tuple[0]*self.bin_width     # width of (1-burst_edge) peak value (s)
        burst_values = tuple([peak_widths_tuple[1:][0],                 # peak value (Hz)
                              peak_widths_tuple[1:][1]*self.bin_width,  # burst_start (s)
                              peak_widths_tuple[1:][2]*self.bin_width]) # burst_end (s)

        return duration, burst_values
    
    def inter_burst_interval(self):
        _, burst_values = self.burst_width()
        ibi = burst_values[1][1:] - burst_values[2][:-1]
        return ibi


    def burst_raster(self):
        """
        spike raster for bursts. Take the peak as center,
        take spikes that fall in [t_p-t0, t_p+t1] where
        t0, t1 is the start and end time windown for 
        a burst. 
        burst_train[[subtime_train_1], [subtime_train_n]]
        """
        _, burst_values = self.burst_width()
        edges = np.stack([burst_values[1], burst_values[2]], axis=1)
        if self.unit == "ms":
            edges *= 1000
            
        burst_train = []
        for start, end in edges: 
            sd = self.subtime(start=start, end=end)
            burst_train.append(sd.train)
        return burst_train
    
    
    def backbone_units(self):
        burst_train = self.burst_raster()
        backbone_indices = []
        backbone = {}
        for n in range(self.N):
            num_event = 0
            for train in burst_train:
                if len(train[n]) > self.backbone_spikes:
                    num_event += 1
            # print(n, num_event)
            if num_event >= self.backbone_burst_thr*self.num_burst:
                backbone_indices.append(n)
                backbone[n] = [train[n] for train in burst_train]
        backbone_train = []
        for nb in range(self.num_burst):
            bt = []
            for i, train in backbone.items():
                bt.append(train[nb])
            backbone_train.append(bt)
        return backbone_indices, backbone, backbone_train
            
    def backbone_fr(self, bin=0.01):
        _, backbone, _ = self.backbone_units()
        bb_fr = dict.fromkeys(backbone.keys())
        for k, train in backbone.items():
            fr = []
            for t in train:
                if self.unit == "ms":
                    t/=1000                 # keep the firing rate in Hz
                if len(t) > 1:
                    # find the peak time for each burst using insta fr
                    # use the train in ms_brefore and ms_after peak for fr 
                    peak_ind = np.argmax(1/np.diff(t))
                    peak_time = t[peak_ind]
                else:
                    peak_time = 0
                bins = np.arange(peak_time-self.before_peak, 
                                   peak_time+self.after_peak+bin,
                                   bin)
                rate = np.histogram(t, bins)[0] / bin
                rate = np.convolve(rate, np.ones(5), 'same') / 5
                fr.append(rate)
            bb_fr[k] = np.array(fr)
        return bb_fr


    def backbone_inst_fr(self):
        _, backbone, _ = self.backbone_units()
        backbone_fr = dict.fromkeys(backbone.keys())
        for k, train in backbone.items():
            inst_fr = []
            for t in train:
                if self.unit == "ms":
                    t/=1000                 # keep the firing rate in Hz
                inst_fr.append(1/np.diff(t))
            backbone_fr[k] = inst_fr
        return backbone_fr












    
# some smooth functions 
# moving average
# Gaussian kernel
def moving_average(data, win=5):
    """
    Save function to matlab movmean
    """
    data = np.array(data)
    assert data.ndim == 1, "input must be one-dimension"
    step = np.ceil(win/2).astype(int)
    movmean = np.empty(data.shape)
    i = 0
    while i < movmean.shape[0]:
        for s in range(step, win):
            res = np.mean(data[:s])
            movmean[i] = res
            i += 1
        for s in range(data.shape[0]-i):
            res = np.mean(data[s:s+win])
            movmean[i] = res
            i += 1
    return movmean


# def smooth_gaussian(data):







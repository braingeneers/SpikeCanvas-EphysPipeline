import numpy as np
import scipy.ndimage as simg
import io
import zipfile
import pandas as pd
from scipy import signal
from scipy.sparse import csr_array
import logging
# from deprecation import deprecated
import math


def sort_template_amplitude(template):
    """
    sort template by amplitude from the largest to the smallest
    :param template: N x M array template array as N for the length of samples,
                     and M for the length of channels
    :return: sorted template index
    """
    assert template.ndim == 2, "Input should be a 2D array; use sort_templates() for higher dimensional data"
    amp = np.max(template, axis=0) - np.min(template, axis=0)
    sorted_idx = np.argsort(amp)[::-1]
    return sorted_idx


def get_best_channel(channels, template):
    assert len(channels) == template.shape[1], "The number of channels does not match to template"
    idx = sort_template_amplitude(template)
    return channels[idx[0]]


def get_best_channel_cluster(clusters, channels, templates):
    """
    find the best channel by sorting templates by amplitude.
    :param clusters:
    :param channels:
    :param templates:
    :return:
    """
    assert len(clusters) == len(templates), "The number of clusters not equal to the number of templates"
    best_channel = dict.fromkeys(clusters)
    for i in range(len(clusters)):
        clst = clusters[i]
        temp = templates[i]
        best_channel[clst] = get_best_channel(channels, temp)
    return best_channel


def get_best_channel_position(channel_position, template):
    idx = sort_template_amplitude(template)
    return channel_position[idx]


def sort_channel_distance(channel_positions, best_channel_position):
    """
    sort channel location by distance to the best channel
    """
    x0, y0 = best_channel_position[0], best_channel_position[1]
    distance = np.empty(len(channel_positions))
    for i in range(len(channel_positions)):
        pos = channel_positions[i]
        distance[i] = (pos[0] - x0) ** 2 + (pos[1] - y0) ** 2
    return np.argsort(distance)


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


def get_population_fr(trains: list, bin_size=0.05, w=5, gaussian=True, sigma=5, average=False):
    N = len(trains)
    if N == 0:
        logging.info("Input train is empty")
        return [], []
    trains = np.hstack(trains)
    rec_length = np.max(trains)
    bin_num = int(rec_length // bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    fr = np.histogram(trains, bins)[0] / bin_size
    if gaussian:
        pop_fr = simg.gaussian_filter1d(fr, sigma=sigma)
    else:
        pop_fr = np.convolve(fr, np.ones(w), 'same') / w
    if average:
        pop_fr /= N
    return bins, pop_fr


def remove_single_channel_unit(spike_data: dict, nelec=2, pitch=17.5):
    min_dist = np.round(np.sqrt(2 * (nelec * pitch) ** 2), 4)
    trains_dict = spike_data["train"]
    N = len(trains_dict)
    trains = [t for _, t in trains_dict.items()]
    neuron_data = spike_data["neuron_data"]
    to_remove = []
    for i, data in neuron_data.items():
        nb_pos = data["neighbor_positions"]
        distance = np.array([np.round(abs(
            np.linalg.norm(np.array(pos) - np.array(nb_pos[0]))), 4) for pos in nb_pos])
        if np.sum(distance <= min_dist) == 1:
            to_remove.append(i)
    to_keep = np.setdiff1d(np.arange(N), to_remove)
    if len(to_keep) == 0:
        logging.info("No unit left after running remove_single_channel_unit")
        return [], {}
    cleaned_train = {k: trains[k] for k in to_keep}
    cleaned_data = {i: neuron_data[to_keep[i]] for i in range(len(to_keep))}
    logging.info(f"There are {len(cleaned_data)} units passed the single channel unit test")
    cleaned_spike_data = {}
    for k, v in spike_data.items():
        if k == "train":
            cleaned_spike_data["train"] = cleaned_train
        elif k == "neuron_data":
            cleaned_spike_data["neuron_data"] = cleaned_data
        else:
            cleaned_spike_data[k] = v
    return cleaned_spike_data


def sparse_train(spike_train: list, bin_size=0.001):
    """
    create a sparse matrix for the input spike trains
    with a given bin size
    """
    num = len(spike_train)
    length = np.max([t[-1] for t in spike_train])
    logging.info(f"recording length {length}")
    indices = np.hstack([np.ceil(ts / bin_size) - 1
                         for ts in spike_train]).astype(int)
    units = np.hstack([0] + [len(ts) for ts in spike_train])
    indptr = np.cumsum(units)
    values = np.ones_like(indices)
    length = int(np.ceil(length / bin_size))
    np.clip(indices, 0, length - 1, out=indices)
    st = csr_array((values, indices, indptr),
                   shape=(num, length)).toarray()
    return st


def ccg(bt1, bt2, ccg_win=[-10, 10], t_lags_shift=0):
    left_edge, right_edge = np.subtract(ccg_win, t_lags_shift)
    lags = np.arange(ccg_win[0], ccg_win[1] + 1)
    pad_width = min(max(-left_edge, 0), max(right_edge, 0))
    bt2_pad = np.pad(bt2, pad_width=pad_width, mode='constant')
    cross_corr = signal.fftconvolve(bt2_pad, bt1[::-1], mode="valid")
    return np.round(cross_corr), lags

def p_fast(n, lambda_):
    """
    A poisson estimation of the probability of observing n or more events
    """
    ## take log to make sure the factorial does not overflow
    # add poisson_var when x = 0, 1, take log after calculation to avoid log(0)
    if n > 1:
        poisson_01 = [np.exp(-lambda_)*lambda_**x/math.factorial(x) for x in [0, 1]]
        poisson_res = [np.exp(-lambda_ + x*math.log(lambda_) - math.log(math.factorial(x))) for x in range(2, n)]
        poisson_var = poisson_01 + poisson_res
    else:
        poisson_var = [np.exp(-lambda_)*lambda_**x/math.factorial(x) for x in range(n)]
    continuity_correction = np.exp((math.log(0.5) - lambda_ + n*math.log(lambda_)) - math.log(math.factorial(n)))
    return 1 - np.sum(poisson_var) - continuity_correction

def hollow_gaussian_round(sigma=10, truncate=4, kerlen=11, hf=0.6):
    """
    create a hollow gaussian by multiplying a gaussian with a triangle
    """

    sd = float(sigma)
    sigma2 = sigma * sigma
    lw = int(truncate * sd + 0.5)
    radius = lw
    x = np.arange(-radius, radius+1)

    phi_x = np.exp(-0.5 / sigma2 * x ** 2)
    phi_x = phi_x / phi_x.sum()

    # generate a triangle
    triangle_center = (1 - (1-hf) * signal.triang(kerlen)) 
    triangle = np.concatenate((np.ones(len(x)//2 - kerlen//2), 
                               triangle_center, 
                               np.ones(len(x)//2 - kerlen//2))) 
    return phi_x * triangle

def hollow_gaussian_filter(counts, sigma=10):
    return np.convolve(counts, hollow_gaussian_round(sigma=sigma), mode="same")

def spike_time_tiling(tA, tB, delt=0.02, length=None):
    """
    Calculate the spike time tiling coefficient [1] between two spike trains.
    STTC is a metric for correlation between spike trains with some improved
    intuitive properties compared to the Pearson correlation coefficient.
    Spike trains are lists of spike times sorted in ascending order.

    [1] Cutts & Eglen. Detecting pairwise correlations in spike trains:
        An objective comparison of methods and application to the study of
        retinal waves. J Neurosci 34:43, 14288–14303 (2014).
    """
    if length is None:
        length = max(tA[-1], tB[-1])

    if len(tA) == 0 or len(tB) == 0:
        return 0.0

    TA = _sttc_ta(tA, delt, length) / length
    TB = _sttc_ta(tB, delt, length) / length
    return _spike_time_tiling(tA, tB, TA, TB, delt)

def _spike_time_tiling(tA, tB, TA, TB, delt):
    "Internal helper method for the second half of STTC calculation."
    PA = _sttc_na(tA, tB, delt) / len(tA)
    PB = _sttc_na(tB, tA, delt) / len(tB)

    aa = (PA - TB) / (1 - PA * TB) if PA * TB != 1 else 0
    bb = (PB - TA) / (1 - PB * TA) if PB * TA != 1 else 0
    return (aa + bb) / 2

def _sttc_ta(tA, delt, tmax):
    '''
    Helper function for spike time tiling coefficients: calculate the
    total amount of time within a range delt of spikes within the
    given sorted list of spike times tA.
    '''
    if len(tA) == 0:
        return 0

    base = min(delt, tA[0]) + min(delt, tmax - tA[-1])
    return base + np.minimum(np.diff(tA), 2 * delt).sum()

def _sttc_na(tA, tB, delt):
    '''
    Helper function for spike time tiling coefficients: given two
    sorted lists of spike times, calculate the number of spikes in
    spike train A within delt of any spike in spike train B.
    '''
    if len(tB) == 0:
        return 0
    tA, tB = np.asarray(tA), np.asarray(tB)

    # Find the closest spike in B after spikes in A.
    iB = np.searchsorted(tB, tA)

    # Clip to ensure legal indexing, then check the spike at that
    # index and its predecessor to see which is closer.
    np.clip(iB, 1, len(tB) - 1, out=iB)
    dt_left = np.abs(tB[iB] - tA)
    dt_right = np.abs(tB[iB - 1] - tA)

    # Return how many of those spikes are actually within delt.
    return (np.minimum(dt_left, dt_right) <= delt).sum()

# def latency(train_1, train_2, threshold=0.02):
#     """
#     Find latency of train_2 to train_1 by labeling the two spike trains.
#     If the latency is greater than the threshold, move to the next spike time.
#     The threshold can be the sttc window size.
#     ref: https://github.com/SpikeInterface/spikeinterface/blob/d269898d1404815dbc96b555687a2ab053acd9e8/src/spikeinterface/comparison/comparisontools.py#L8
#     :return: a list of latencies
#     """
#     labels = np.concatenate((np.zeros(train_1.shape), np.ones(train_2.shape)))
#     times = np.concatenate((train_1, train_2))
#     sort_idx = np.argsort(times)
#     labels = labels[sort_idx]
#     times = times[sort_idx]
#     label_diff = np.diff(labels)   
#     # 0 0  1 0 1  0 1  1 
#     # 0 1 -1 1 -1 1 0  -1
#     lat_idx = np.where(label_diff != 0)[0]


    # lat = []
    # i, diff, thr = 0, 0, threshold
    # label = train_inter[0][0]
    # coef = 1 if label == label_1[0] else -1
    # while i < len(train_inter) - 1:
    #     if train_inter[i][0] != train_inter[i + 1][0]:
    #         diff = train_inter[i + 1][1] - train_inter[i][1]
    #         if diff > thr:
    #             i += 1
    #         else:
    #             if train_inter[i][0] == label:
    #                 lat.append(diff * coef)
    #             else:
    #                 lat.append(-diff * coef)
    #             i += 2
    #     else:
    #         i += 1
    # return lat



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
    if not path.endswith('.zip'):
        return None
    with zipfile.ZipFile(path, 'r') as f_zip:
        assert 'params.py' in f_zip.namelist(), "Wrong spike sorting output."
        with io.TextIOWrapper(f_zip.open('params.py'), encoding='utf-8') as params:
            for line in params:
                if "sample_rate" in line:
                    fs = float(line.split()[-1])
        clusters = np.load(f_zip.open('spike_clusters.npy')).squeeze()
        templates_w = np.load(f_zip.open('templates.npy'))  # (cluster_id, samples, channel_id)
        wmi = np.load(f_zip.open('whitening_mat_inv.npy'))
        channels = np.load(f_zip.open('channel_map.npy')).squeeze()
        spike_templates = np.load(f_zip.open('spike_templates.npy')).squeeze()
        spike_times = np.load(f_zip.open('spike_times.npy')).squeeze() / fs   # in second * 1e3  # in ms
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

    # unwhite the templates before finding the best channel!
    templates = np.dot(templates_w, wmi)

    df = pd.DataFrame({"clusters": clusters, "spikeTimes": spike_times, "amplitudes": amplitudes})
    cluster_agg = df.groupby("clusters").agg({"spikeTimes": lambda x: list(x),
                                              "amplitudes": lambda x: list(x)})
    cluster_agg = cluster_agg[cluster_agg.index.isin(labeled_clusters)]

    cls_temp = dict(zip(clusters, spike_templates))
    neuron_dict = dict.fromkeys(np.arange(len(labeled_clusters)), None)

    for i in range(len(labeled_clusters)):
        c = labeled_clusters[i]
        temp = templates[cls_temp[c]]
        amp = np.max(temp, axis=0) - np.min(temp, axis=0)
        sorted_idx = np.argsort(amp)[::-1]
        nbgh_chan_idx = sorted_idx[:12]
        nbgh_temps = temp.transpose()[nbgh_chan_idx]
        best_chan_temp = nbgh_temps[0]
        nbgh_channels = channels[nbgh_chan_idx]
        nbgh_postions = [tuple(positions[idx]) for idx in nbgh_chan_idx]
        best_channel = nbgh_channels[0]
        best_position = nbgh_postions[0]
        cls_amp = cluster_agg["amplitudes"][c]
        neuron_dict[i] = {"cluster_id": c, "channel": best_channel, "position": best_position,
                          "amplitudes": cls_amp, "template": best_chan_temp,
                          "neighbor_channels": nbgh_channels, "neighbor_positions": nbgh_postions,
                          "neighbor_templates": nbgh_temps}
    config_dict = dict(zip(channels, positions))
    neuron_data = {0: neuron_dict}
    metadata = {0: config_dict}
    spike_train = list(cluster_agg["spikeTimes"])
    return fs, spike_train, neuron_dict

def load_curation(qm_path):
    with zipfile.ZipFile(qm_path, 'r') as f_zip:
        qm = f_zip.open("qm.npz")
        data = np.load(qm, allow_pickle=True)
        spike_times = data["train"].item()
        fs = data["fs"]
        train = [times / fs for _, times in spike_times.items()]
        if "config" in data:
            config = data["config"].item()
        else:
            config = None
        neuron_data = data["neuron_data"].item()
    return train, neuron_data, config, fs
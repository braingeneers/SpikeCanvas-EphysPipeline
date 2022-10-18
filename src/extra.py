import numpy as np
from scipy.ndimage import gaussian_filter1d

def smoothed_fr_rate(spike_times_all, rec_length, bin_size=100, sigma=0.7):
    bin_num = int(rec_length // bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    fr_rate, _ = np.histogram(spike_times_all, bins)
    fr_rate = fr_rate / bin_size * 1000  # hz
    smoothed_fr = gaussian_filter1d(fr_rate, sigma)
    return bins, smoothed_fr

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
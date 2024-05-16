import zipfile
import re
import copy
import posixpath
import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
import braingeneers.analysis as analysis
import numpy as np
import os
from scipy import stats
import itertools
from deprecated import deprecated
import logging
from scipy.sparse import csr_array
from scipy import signal

def binarize_train(trains: list, bin_size=0.001):
    rec_start = 0
    rec_length = np.max(np.hstack(trains))
    bin_num = int(rec_length// bin_size) + 1
    bins = np.linspace(rec_start, rec_length, bin_num)
    binned = [np.histogram(t, bins)[0] for t in trains]
    return binned


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

def p_test_ks(data_1, data_2):
    assert isinstance(data_1, type(data_2)), \
        "Input must be the same type"

    if isinstance(data_1, dict) and isinstance(data_2, dict):
        assert len(data_1) == len(data_2), \
            "Input data must have the same length!"
        p_dict = {d: None for d in data_1.keys()}
        for d in data_1.keys():
            _, p = stats.ks_2samp(data_1[d], data_2[d])
            p_dict[d] = p
        return p_dict
    elif isinstance(data_1, (list, np.ndarray)) \
            and isinstance(data_2, (list, np.ndarray)):
        return stats.ks_2samp(data_1, data_2)[1]

def merge_lists(lsts):
    """
    Merge lists if they share any same value
    """
    sets = [set(l) for l in lsts if l]
    merged = True
    while merged:
        merged = False
        results = []
        while sets:
            common, rest = sets[0], sets[1:]
            sets = []
            for x in rest:
                if x.isdisjoint(common):
                    sets.append(x)
                else:
                    merged = True
                    common |= x
            results.append(common)
        sets = results
    return sets

def get_population_fr(trains: list, bin_size=0.1, w=5, average=False):
    N = len(trains)
    trains = np.hstack(trains)
    rec_length = np.max(trains)
    bin_num = int(rec_length// bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    fr = np.histogram(trains, bins)[0] / bin_size
    fr_avg = np.convolve(fr, np.ones(w), 'same') / w
    if average:
        fr_avg /= N
    return bins, fr_avg

def fano_factor(trains: list, bin_size=0.1):
    rec_length = np.max(np.hstack(trains))
    bins = np.arange(0, rec_length+bin_size, bin_size)
    factors = []
    for t in trains:
        fr = np.histogram(t, bins)
        fano = np.var(fr) / np.mean(fr)
        factors.append(fano)
    return factors

def get_group_data(grp_dict, clt, group):
    days = ["d21", "d28", "d35", "d42", "d49", "d56", "d63"]
    group_data = []
    for g in group:
        day_dict = grp_dict[clt][g]
        data_day_dict = {d: None for d in days}
        for d, dt in day_dict.items():
            data_day_dict[d] = list(itertools.chain(*dt.values()))
        group_data.append(data_day_dict)
    return group_data


def read_train(qm_path):
    with smart_open.open(qm_path, 'rb') as f:
        with zipfile.ZipFile(f, 'r') as f_zip:
            qm = f_zip.open("qm.npz")
            data = np.load(qm, allow_pickle=True)
            spike_times = data["train"].item()
            fs = data["fs"]
            train = [times / fs for __, times in spike_times.items()]
    return train


def load_curation(qm_path):
    with smart_open.open(qm_path, 'rb') as f:
        with zipfile.ZipFile(f, 'r') as f_zip:
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


def read_train_dict(train_dict_npz):
    train_data = np.load(train_dict_npz, allow_pickle=True)
    train_dict = train_data["train_dict"].item()
    return train_dict


def get_mean_fr(train: list):
    rec_length = np.max(np.hstack(train))
    mean_fr = [len(t) / rec_length for t in train]
    return mean_fr


def get_isi(train: list):
    return [np.diff(t) for t in train]


def get_isi_cv(train: list):
    cv = []
    for t in train:
        isi = np.diff(t)
        std = np.std(isi)
        m = np.mean(isi)
        cv.append(std / m)
    return cv


def get_inst_fr_cv(train: list):
    cv = []
    for t in train:
        inst_fr = np.reciprocal(np.diff(t))
        std = np.std(inst_fr)
        m = np.mean(inst_fr)
        cv.append(std / m)
    return cv


def generate_rate_from_train(train_dict: dict):
    rate_dict = copy.deepcopy(train_dict)
    for C, culture in train_dict.items():
        for g, day_value in culture.items():
            for d, trains in day_value.items():
                for chip, train in trains.items():
                    if len(train) > 0:
                        rate_dict[C][g][d][chip] = get_mean_fr(train)
                    else:
                        rate_dict[C][g][d][chip] = []
    return rate_dict


def get_mean_fr_path(qm_path):
    with smart_open.open(qm_path, 'rb') as f:
        with zipfile.ZipFile(f, 'r') as f_zip:
            qm = f_zip.open("qm.npz")
            data = np.load(qm, allow_pickle=True)
            spike_times = data["train"].item()
            fs = data["fs"]
            train = [times / fs for __, times in spike_times.items()]
            mean_fr = get_mean_fr(train)
    return mean_fr


def load_curation_from_local(subfolders: list, base_folder: str, verbose=True):
    """
    return a dictionary of SpikeData object for each recording
    """
    cultures = ["Tri", "Ngn"]
    days = ["d21", "d28", "d35", "d42", "d49", "d56", "d63"]
    groups = {"patient": [], "control": []}
    spike_dict = {cultures[0]: {}, cultures[1]: {}}

    for sub in subfolders:
        full_path = posixpath.join(base_folder, sub)
        files = sorted(os.listdir(full_path))
        for f in files:
            keys = sorted(f[:-10].split("_"))
            if verbose:
                print(f"Loading data from {keys}")
            if len(keys) > 4:
                for k in keys:
                    if k == "2":
                        break
                    elif k[0] not in ["1", "C", "N", "d"] and len(k) != 4:
                        keys.remove(k)
            if len(keys) > 4:
                if verbose:
                    print(f"Bypass recording {keys} because it's a duplicate or misnomer")
                continue
            chip, g, c, d = keys
            if d == "d27":
                d = "d28"
            if c == "Ngn2":
                c = "Ngn"
            if g.isdigit():
                g = "P" + str(g)
            chip = "c" + str(chip)

            if g not in spike_dict[c]:
                spike_dict[c][g] = {d: {} for d in days}
                if g[0] == "C":
                    groups["control"].append(g)
                else:
                    groups["patient"].append(g)

            train, neuron_data, config = load_curation(posixpath.join(full_path, f))
            if len(train) > 0:
                spike_dict[c][g][d][chip] = analysis.SpikeData(
                    train, neuron_data={0: neuron_data}, metadata={0: config})
                if verbose:
                    print(f"Loaded {len(train)} units to {c}-{g}-{d}-{chip}")
            else:
                if verbose:
                    print(f"Not loaded {c}-{g}-{d}-{chip} because no data available")
    return spike_dict, groups


@deprecated(reason="Use load_curation_from_local() instead")
def load_trains_from_local(subfolders: list, base_folder: str, verbose=True):
    cultures = ["Tri", "Ngn"]
    days = ["d21", "d28", "d35", "d42", "d49", "d56", "d63"]
    groups = {"patient": [], "control": []}
    train_dict = {cultures[0]: {}, cultures[1]: {}}

    for sub in subfolders:
        full_path = posixpath.join(base_folder, sub)
        files = sorted(os.listdir(full_path))
        for f in files:
            keys = sorted(f[:-10].split("_"))
            if verbose:
                print(f"Loading data from {keys}")
            if len(keys) > 4:
                for k in keys:
                    if k == "2":
                        break
                    elif k[0] not in ["1", "C", "N", "d"] and len(k) != 4:
                        keys.remove(k)
            if len(keys) > 4:
                if verbose:
                    print(f"Bypass recording {keys} because it's a duplicate or misnomer")
                continue
            chip, g, c, d = keys
            if d == "d27":
                d = "d28"
            if c == "Ngn2":
                c = "Ngn"
            if g.isdigit():
                g = "P" + str(g)
            chip = "c" + str(chip)

            if g not in train_dict[c]:
                train_dict[c][g] = {d: {} for d in days}
                if g[0] == "C":
                    groups["control"].append(g)
                else:
                    groups["patient"].append(g)

            train_dict[c][g][d][chip] = read_train(posixpath.join(full_path, f))
            if verbose:
                print(f"Loaded {len(train_dict[c][g][d][chip])} units to {c}-{g}-{d}-{chip}")

    return train_dict, groups


def sort_curated_from_uuids(uuids, s3_dir):
    # from collections import defaultdict
    cultures = ["Tri", "Ngn"]
    days = ["d21", "d28", "d35", "d42", "d49", "d56", "d63"]
    file_dict = {cultures[0]: {}, cultures[1]: {}}

    groups = {"patient": [], "control": []}
    for uuid in uuids:
        print(uuid)
        original_dir = posixpath.join(s3_dir, uuid, "original/data/")
        curated_dir = posixpath.join(s3_dir, uuid, "derived/kilosort2/")
        recordings = sorted(wr.list_objects(original_dir))
        for rec in recordings:
            f = rec.split(original_dir)[1]
            keys = sorted(f[:-3].split("_"))
            print(keys)
            corr_file = posixpath.join(curated_dir, f + "_qm.zip")
            if len(keys) > 4:
                for k in keys:
                    if k == "2":
                        break
                    elif k[0] not in ["1", "C", "N", "d"] and len(k) != 4:
                        keys.remove(k)
            if len(keys) > 4:
                continue
            chip, g, c, d = keys
            if d == "d27":
                d = "d28"
            if c == "Ngn2":
                c = "Ngn"

            if g in file_dict[c]:
                # print(file_dict[c])
                file_dict[c][g][d][chip] = corr_file
            else:
                file_dict[c][g] = {d: {} for d in days}
                # print(file_dict[c])
                if g[0] == "C":
                    groups["control"].append(g)
                else:
                    groups["patient"].append(g)
    return file_dict, groups


def sort_files(uuid, s3_dir, days, group, culture):
    original_dir = posixpath.join(s3_dir, uuid, "original/data/")
    curated_dir = posixpath.join(s3_dir, uuid, "derived/kilosort2/")

    files_dict = {c: {g: {d: [] for d in days} for g in group} for c in culture}
    # firing_rate = copy.deepcopy(sorted_files)
    # print(sorted_files)

    pair = sorted(wr.list_objects(original_dir))
    files = [file.split(original_dir)[1] for file in pair]
    print("Total number of files for " + uuid + ": ", len(files))
    for f in files:
        day = re.findall("\Bd\d\d", f)[0]
        if day == "d27":  # added for a special naming case
            day = "d28"
        splitted = f[:-3].split("_")
        # print(day, splitted)
        corr_file = posixpath.join(curated_dir, f + "_qm.zip")
        if "Tri" in splitted:
            for g in group:
                if g in splitted:
                    files_dict["Tri"][g][day].append(corr_file)
        elif "Ngn" or "Ngn2" in splitted:
            for g in group:
                if g in splitted:
                    files_dict["Ngn"][g][day].append(corr_file)
        else:
            print(f)
    return files_dict


# def create_dict(days, group, culture, chip):
#     {c: {g: {d: [] for d in days} for g in group} for c in culture}


def sort_files_fr(uuid, s3_dir, days, group, culture):
    original_dir = posixpath.join(s3_dir, uuid, "original/data/")
    curated_dir = posixpath.join(s3_dir, uuid, "derived/kilosort2/")

    files_dict = {c: {g: {d: [] for d in days} for g in group} for c in culture}
    rates_dict = copy.deepcopy(files_dict)

    pair = sorted(wr.list_objects(original_dir))
    files = [file.split(original_dir)[1] for file in pair]
    print("Total number of files for " + uuid + ": ", len(files))
    for f in files:
        day = re.findall("\Bd\d\d", f)[0]
        if day == "d27":  # added for a special naming case
            day = "d28"
        splitted = f[:-3].split("_")
        # print(day, splitted)
        corr_file = posixpath.join(curated_dir, f + "_qm.zip")
        try:
            mean_fr = get_mean_fr_path(corr_file)
        except:
            mean_fr = []
        if "Tri" in splitted:
            for g in group:
                if g in splitted:
                    files_dict["Tri"][g][day].append(corr_file)
                    rates_dict["Tri"][g][day].append(mean_fr)
        elif "Ngn" or "Ngn2" in splitted:
            for g in group:
                if g in splitted:
                    files_dict["Ngn"][g][day].append(corr_file)
                    rates_dict["Ngn"][g][day].append(mean_fr)
        else:
            print(f"Does not belong to any group {f}")

    return files_dict, rates_dict


def sort_files_train_fr(uuid, s3_dir, days, group, culture):
    original_dir = posixpath.join(s3_dir, uuid, "original/data/")
    curated_dir = posixpath.join(s3_dir, uuid, "derived/kilosort2/")

    files_dict = {c: {g: {d: [] for d in days} for g in group} for c in culture}
    train_dict = copy.deepcopy(files_dict)
    rates_dict = copy.deepcopy(files_dict)

    pair = sorted(wr.list_objects(original_dir))
    files = [file.split(original_dir)[1] for file in pair]
    print("Total number of files for " + uuid + ": ", len(files))
    for f in files:
        day = re.findall("\Bd\d\d", f)[0]
        if day == "d27":  # added for a special naming case
            day = "d28"
        splitted = f[:-3].split("_")
        # print(day, splitted)
        corr_file = posixpath.join(curated_dir, f + "_qm.zip")
        try:
            train = read_train(corr_file)
        except:
            train = []
        if len(train) > 0:
            mean_fr = get_mean_fr_path(corr_file)
        if "Tri" in splitted:
            for g in group:
                if g in splitted:
                    files_dict["Tri"][g][day].append(corr_file)
                    train_dict["Tri"][g][day].append(train)
                    rates_dict["Tri"][g][day].append(mean_fr)
        elif "Ngn" or "Ngn2" in splitted:
            for g in group:
                if g in splitted:
                    files_dict["Ngn"][g][day].append(corr_file)
                    train_dict["Ngn"][g][day].append(train)
                    rates_dict["Ngn"][g][day].append(mean_fr)
        else:
            print(f"Does not belong to any group {f}")

    return files_dict, train_dict, rates_dict


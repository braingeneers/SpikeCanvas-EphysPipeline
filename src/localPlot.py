import matplotlib.pyplot as plt
import seaborn
import numpy as np
import matplotlib as mpl
import time


# plot functions
# def plot_hist()

def plot_matrix(square_matrix, s):
    mask = np.triu(np.ones_like(square_matrix, dtype=bool))
    figure, axs = plt.subplots(1, 1, figsize=(8, 8))
    cmap = seaborn.diverging_palette(230, 20, as_cmap=True)
    plt.title("{}".format(s))
    # Draw the heatmap with the mask and correct aspect ratio
    seaborn.heatmap(square_matrix, mask=mask, cmap=cmap, vmax=1.0, center=0,
                    square=True, linewidths=.5, cbar_kws={"shrink": .5})
    plt.show(block=False)
    # plt.show()


def plot_scatter(y_data, s, save=True):
    x = np.arange(len(y_data))
    figure, axs = plt.subplots(1, 1, figsize=(8, 8))
    axs.plot(x, y_data, 'o-', alpha=0.7)
    plt.title("Latencies between ch {}".format(s), fontsize=16)
    if save:
        plt.savefig("lat_{}".format(s))
    plt.show(block=False)


def plot_raster_all(chn_pos, spike_times, s, save=True):
    st_left = []
    st_right = []
    left_ind = set()
    for i in range(len(chn_pos)):
        if chn_pos[i][0] <= 2000:
            st_left.append(spike_times[i])
            st_right.append([])
            left_ind.add(i)
    st_right.append([])
    for i in range(len(chn_pos)):
        if i not in left_ind and chn_pos[i][0] > 2000:
            st_right.append(spike_times[i])

    fig, axs = plt.subplots(1, 1, figsize=(24, 8))
    axs.eventplot(st_left, linelengths=1, linewidth=2, color='blue', alpha=0.4)
    axs.eventplot(st_right, linelengths=1, linewidth=2, color='blueviolet', alpha=0.4)
    axs.set_xlabel("Time (ms)", fontsize=16)
    axs.set_ylabel("Units", fontsize=16)
    axs.xaxis.set_tick_params(labelsize=18)
    axs.yaxis.set_tick_params(labelsize=18)

    if save:
        plt.savefig("spike_raster_{}".format(s))
    plt.show(block=False)


def plot_raster_fr(spike_times, fr_rate, time_ms, s, extra=None, save=True):
    if len(spike_times) > 2:
        raise ValueError("spike_times need to be a list of spike times lists.")
    if len(spike_times) != len(fr_rate):
        raise ValueError("spike_times and fr_rate are not the same length.")
    if len(spike_times) == 2:
        n = 2
        gridspec_kw = {'height_ratios': [3, 1, 1]}
        r_color = ['blue', 'orangered']
        f_color = ['orangered', 'blue']
        label = ['right', 'left']
    else:
        n = 1
        gridspec_kw = {'height_ratios': [3, 1]}
        r_color = ['k']
        f_color = ['red']
        label = ['firing rate']
    fig, axs = plt.subplots(n+1, 1, figsize=(12, 6), sharex=True, gridspec_kw=gridspec_kw)
    for i in range(n):
        axs[0].eventplot(spike_times[i], linelengths=0.8,
                         linewidth=1, alpha=0.4, color=r_color[i])
    if extra:
        for i in extra:
            axs[0].axvspan(i[0], i[1], color='#00C0FF', alpha=0.2)    # blue led color
    axs[0].set_ylabel("Units", fontsize=16)
    axs[0].get_xaxis().set_visible(False)
    axs[0].yaxis.set_tick_params(labelsize=16)
    axs[0].set_title("Raster of recording {}".format(s), fontsize=16)
    for i in range(n):
        xx = np.linspace(0, time_ms, len(fr_rate[i]))
        axs[i+1].plot(xx, fr_rate[i], color=f_color[i], label=label[i])
        axs[i+1].yaxis.set_tick_params(labelsize=16)
        axs[i+1].set_ylabel("Hz", fontsize=16)
        axs[i+1].get_xaxis().set_visible(False)
        axs[i+1].legend(loc="upper right", fontsize=12)
    # xx_s = np.linspace(0, time_ms/1000, 10, dtype='int')
    # axs[n].xaxis.set_ticklabels(xx_s)
    axs[n].set_xlabel("Time (ms)", fontsize=16)
    axs[n].xaxis.set_tick_params(labelsize=16)
    axs[n].get_xaxis().set_visible(True)

    plt.tight_layout()
    if save:
        plt.savefig("spike_raster_{}".format(s))
    plt.show(block=False)


def plot_bar(lat, s, distance, mean, save=True):
    num_bins = 10
    fig, axs = plt.subplots(1, 1, figsize=(6, 8))
    n, bins, patches = axs.hist(lat, bins=num_bins, rwidth=0.9, facecolor='g')
    axs.set_xlim([-20, 20])
    axs.set_xlabel('latency (ms)', fontsize=16)
    textStr = str(np.round(distance, 3))+'um'+'\n'+str(np.round(mean, 3))+'ms'
    plt.text(0.1, 0.9, textStr, size=12, transform=plt.gca().transAxes)
    if save:
        plt.savefig("bar_{}".format(s))
    plt.show(block=False)


def plot_simple_bar(data, bins, label, s, save=True):
    fig = plt.figure(figsize=(6, 4))
    n, bins, patches = plt.hist(data, bins, label=label)
    plt.legend(loc='upper right')
    plt.xlabel("{}".format(s[0]), fontsize=16)
    plt.ylabel("{}".format(s[1]), fontsize=16)
    plt.title("{} Distribution".format(s[2]))
    if save:
        plt.savefig("bar_{}".format(s[2]))
    plt.show(block=False)


def plot_fr_freq(fr_hz, bins):  # add y ticks
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    plt.pcolormesh(fr_hz, cmap='viridis')
    plt.show(block=False)


def plot_channel_map(spike_times, elec_map, chn_pos, tilings, PDMS, s):
    fig, axs = plt.subplots(figsize=(12, 9))
    plt.title("{} Electrode Map".format(s))
    if elec_map is None or len(elec_map) == 0:
        elec_xy = np.asarray([(x, y) for x in np.arange(0, 3850, 17.5)
                              for y in np.arange(0, 2100, 17.5)])
        plt.scatter(elec_xy[:, 0], elec_xy[:, 1], s=0.1, color='b', alpha=0.3)
    else:
        plt.scatter(elec_map[:, 0], elec_map[:, 1], s=0.1, color='b', alpha=0.3)

    if PDMS == True:
        circle_1 = (750, 1350)
        circle_2 = (3100, 750)
        a_1, a_2 = (1496, 1431), (2484, 1178)
        b_1, b_2 = (1366, 922), (2354, 669)
        radius = 750
        plt.plot([a_1[0], a_2[0]], [a_1[1], a_2[1]], color='k', alpha=0.7)
        plt.plot([b_1[0], b_2[0]], [b_1[1], b_2[1]], color='k', alpha=0.7)
        cir_1 = plt.Circle(circle_1, radius, color='k', fill=False, alpha=0.7)
        cir_2 = plt.Circle(circle_2, radius, color='k', fill=False, alpha=0.7)
        axs.set_aspect('equal', adjustable='datalim')
        axs.add_patch(cir_1)
        axs.add_patch(cir_2)
    for i in range(len(spike_times)):
        plt.scatter(chn_pos[i][0], chn_pos[i][1], s=len(spike_times[i]) / 20, color='green')
        # plt.text(chn_pos[i][0], chn_pos[i][1], str(i), color="blue", fontsize=10)
        if tilings is None or len(tilings) == 0:
            continue
        else:
            for t in range(i+1, len(tilings[i])):
                if tilings[i][t] > 0.35:
                    plt.plot([chn_pos[i][0], chn_pos[t][0]], [chn_pos[i][1], chn_pos[t][1]],
                             linewidth=5*tilings[i][t], color='red', alpha=tilings[i][t]*0.3)
    # axs.xaxis.set_visible(False)
    # axs.yaxis.set_visible(False)
    axs.set_xticks([0, 3850])
    axs.set_yticks([0, 2100])
    axs.set_xlim(0, 3850)
    axs.set_ylim(0, 2100)
    plt.gca().invert_yaxis()
    # plt.show(block=False)
    return axs


def plot_functional_map(spike_times, elec_map, chn_pos, paired_direction, PDMS, s):
    fig, axs = plt.subplots(figsize=(16, 10))
    # draw electrodes
    if elec_map is None or len(elec_map) == 0:
        elec_xy = np.asarray([(x, y) for x in np.arange(0, 3850, 17.5)
                              for y in np.arange(0, 2100, 17.5)])
        plt.scatter(elec_xy[:, 0], elec_xy[:, 1], s=0.2, color='b', alpha=0.3)
    else:
        plt.scatter(elec_map[:, 0], elec_map[:, 1], s=0.2, color='b', alpha=0.3)

    if PDMS == True:
        circle_1 = (750, 1350)
        circle_2 = (3100, 750)
        a_1, a_2 = (1496, 1431), (2484, 1178)
        b_1, b_2 = (1366, 922), (2354, 669)
        radius = 750
        plt.plot([a_1[0], a_2[0]], [a_1[1], a_2[1]], color='k', alpha=0.7)
        plt.plot([b_1[0], b_2[0]], [b_1[1], b_2[1]], color='k', alpha=0.7)
        cir_1 = plt.Circle(circle_1, radius, color='k', fill=False, alpha=0.7)
        cir_2 = plt.Circle(circle_2, radius, color='k', fill=False, alpha=0.7)
        axs.set_aspect('equal', adjustable='datalim')
        axs.add_patch(cir_1)
        axs.add_patch(cir_2)

    # find reference firing rate, take the lowest length of spike_times
    ref_fr = len(spike_times[0])
    for i in range(len(spike_times)):
        ref_fr = min(ref_fr, len(spike_times[i]))

    for i in range(len(spike_times)):
        plt.scatter(chn_pos[i][0], chn_pos[i][1], s=len(spike_times[i])/ref_fr*5, color='green')
        # plt.text(chn_pos[i][0], chn_pos[i][1], str(i), color="blue", fontsize=10)
    if len(paired_direction) > 0:
        sender = set()
        receiver = set()
        for p in paired_direction:
            ## p = [i, j, chn_pos[i], chn_pos[j], sttc[i][j], np.mean(lat)]
            plt.scatter(p[2][0], p[2][1], s=len(spike_times[p[0]]) / 20, color='r')
            plt.scatter(p[3][0], p[3][1], s=len(spike_times[p[1]]) / 20, color='b')
            plt.plot([p[2][0], p[3][0]], [p[2][1], p[3][1]],
                     linewidth=3 * p[4], color='darkgrey', alpha=0.7)
            axs.annotate('', xytext=(p[2][0], p[2][1]), xy=((p[2][0]+p[3][0])/2, (p[2][1]+p[3][1])/2),
                         arrowprops=dict(arrowstyle="->", color='darkgrey'), size=18)
            sender.add((p[0], p[2][0], p[2][1]))
            receiver.add((p[1], p[3][0], p[3][1]))
        broker = sender.intersection(receiver)
        for b in broker:
            plt.scatter(b[1], b[2], s=len(spike_times[b[0]]) / 20, color='w')
            plt.scatter(b[1], b[2], s=len(spike_times[b[0]]) / 20, color='gray')
        p = paired_direction[-1]
        b = list(broker)[-1]
        plt.scatter(p[2][0], p[2][1], s=len(spike_times[p[0]]) / 20, color='r', label='Sender')
        plt.scatter(p[3][0], p[3][1], s=len(spike_times[p[1]]) / 20, color='b', label='Receiver')
        plt.scatter(b[1], b[2], s=len(spike_times[b[0]]) / 20, color='gray', label='Broker')
        plt.scatter(-1, -1, s=60, color='green', label='Other Unit')
    plt.legend(loc="upper right", fontsize=12)

    axs.xaxis.set_visible(False)
    axs.yaxis.set_visible(False)
    axs.set_xticks([0, 3850])
    axs.set_yticks([0, 2100])
    plt.xlim(0, 3850)
    plt.ylim(0, 2100)
    ##### for temporary figures
    # axs.set_xticks([2900, 3800])
    # axs.set_yticks([400, 1300])
    # plt.xlim(2900, 3800)
    # plt.ylim(400, 1300)
    ############################
    plt.xlabel(u"\u03bcm", fontsize=16)
    plt.ylabel(u"\u03bcm", fontsize=16)
    plt.gca().invert_yaxis()
    plt.title("{} Functional Connectivity Map".format(s))
    plt.show(block=False)
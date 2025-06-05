import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import seaborn as sns
import ephysplus.utils as utils
import pandas as pd
import os
import plotly.graph_objects as go

fs = 20000.0
plt.style.use('default')


def plot_fr_days(c_mean, c_error, p_mean, p_error, group, days):
    fig, axs = plt.subplots(1, 1, figsize=(5, 5), constrained_layout=True)
    axs.set_title("Fr of {}".format(group), fontsize=16)
    offset = 0  # 0.15
    (_, caps, _) =  axs.errorbar(np.arange(len(days))-offset, c_mean, yerr=c_error, 
                                marker='o', linewidth=2, markersize=8, capsize=4, color='b',
                                label="Control")
    for cap in caps:
        cap.set_markeredgewidth(1)
    (_, caps, _) =  axs.errorbar(np.arange(len(days))+offset, p_mean, yerr=p_error, 
                                marker='D', linewidth=2, markersize=8, capsize=4, color='r', 
                                label="Patient")
    for cap in caps:
        cap.set_markeredgewidth(1)
    axs.legend(loc="upper right", fontsize=12)
    axs.set_xlabel('days', fontsize=16)
    axs.set_ylabel('Fr (Hz)', fontsize=16)
    axs.set_xticks(np.arange(len(days)))
    axs.set_xticklabels(days)
    axs.xaxis.set_tick_params(labelsize=16)
    axs.yaxis.set_tick_params(labelsize=16)
    # axs.set_ylim([0, max(max(c_mean), max(p_mean))+1.5])
    axs.set_ylim(0, 5.5)
    plt.savefig("Fr_for_{}.png".format(group), dpi=300)


def plot_num_units(cp_data, days, group):
    fig, axs = plt.subplots(1, 1, figsize=(5, 5), constrained_layout=True)
    axs.set_title("Num Units, {}".format(group), fontsize=16)
    xx = np.arange(len(days))
    yy_c = [len(times) for times in cp_data["control"]]
    yy_p = [len(times) for times in cp_data["patient"]]
    axs.plot(xx, yy_c, color='b', alpha=0.8, marker="o", linewidth=2, markersize=8, label="Control")
    for i, txt in enumerate(yy_c):
        axs.annotate(txt, (xx[i], yy_c[i]), fontsize=12)
    axs.plot(xx, yy_p, color='r', alpha=0.8, marker="D", linewidth=2, markersize=8, label="Patient")
    for i, txt in enumerate(yy_p):
        axs.annotate(txt, (xx[i], yy_p[i]), fontsize=12)
    axs.legend(loc="upper right", fontsize=12)
    axs.set_xlabel('days', fontsize=16)
    axs.set_ylabel('Counts', fontsize=16)
    axs.set_xticks(np.arange(len(days)))
    axs.set_xticklabels(days)
    axs.xaxis.set_tick_params(labelsize=16)
    axs.yaxis.set_tick_params(labelsize=16)
    plt.savefig("Num_Units_{}.png".format(group, dpi=300)) 

def plot_violin(cp_data, days, file_name):
    import seaborn as sns
    import pandas as pd
    data = dict(zip(days, cp_data['control']))
    control = pd.DataFrame.from_dict(data, orient='index').transpose()
    patient = pd.DataFrame.from_dict(dict(zip(days, cp_data['patient'])), orient='index').transpose()
    df = pd.DataFrame([[label, val, 'control'] for label, values in control.items() for val in values]
                    + [[label, val, 'patient'] for label, values in patient.items() for val in values],
                    columns=['label', 'value', 'source'])

    fig, ax = plt.subplots(2, 1, figsize = (7, 4*2), constrained_layout=True)
    ax[0].set_title("Fr {}".format(file_name), fontsize=16)
    axs = ax[0]
    axs1 = ax[1]
    axs = sns.violinplot(data=df, x='label', y='value', hue='source', inner="box",
                        palette=['cornflowerblue', 'indianred'], ax=axs)
    sns.stripplot(data=df, x='label', y='value', hue='source', dodge=True, jitter=True, linewidth=0.4, size=3, 
                palette=['cornflowerblue', 'indianred'], ax=axs)

    sns.violinplot(data=df, x='label', y='value', hue='source', palette=['cornflowerblue', 'indianred'], saturation=0.5,
                inner="quartile", split=True, ax=axs1)
    sns.pointplot(data=df, x='label', y='value', hue='source', linestyles="", dodge=True, 
                estimator='mean', markers=["o", "D"], palette=['blue', 'red'], ax=axs1)
    for l in axs1.lines[1::3]:
        l.set_linestyle('-')
        l.set_linewidth(2)
        l.set_color('black')
        l.set_alpha(0.8)

    for a in ax:    
        a.set_ylabel("Firing Rate (Hz)", fontsize=16)
        a.set_xlabel("", fontsize=16)
        a.xaxis.set_tick_params(labelsize=16)
        a.yaxis.set_tick_params(labelsize=16)
        a.legend(loc="upper right", fontsize=12)
        a.set_ylim(-4, 30)

    plt.savefig("violin_fr_{}.png".format(file_name), dpi=300)

def plot_raster_with_fr(train:list, title:str, bin_size=0.1, w=5, avg=False, axs=None):
    bins, fr_avg = utils.get_population_fr(trains=train, bin_size=bin_size, w=w, average=avg)
    if axs is None:
        fig, axs = plt.subplots(1, 1, figsize=(16, 6))
    axs.set_title(f"raster_{title}", fontsize=12)

    y = 0
    for vv in train:
        axs.scatter(vv, [y]*len(vv), marker="|", c='k', s=6, alpha=0.7)
        y += 1
    axs.set_xlabel("Time (s)", fontsize=16)
    axs.set_ylabel("Unit", fontsize=16)
    axs.xaxis.set_tick_params(labelsize=16)
    axs.yaxis.set_tick_params(labelsize=16)
    
    axs1 = axs.twinx()
    axs1.yaxis.set_label_position("right") 
    axs1.spines['right'].set_color('r')
    axs1.spines['right'].set_linewidth(3)
    axs1.plot(bins[1:], fr_avg, color='r', linewidth=2, alpha=0.5)
    axs1.set_ylabel("Population Firing Rate (Hz)", fontsize=16, color='r')
    axs1.set_xlabel("Time (s)", fontsize=16)
    axs1.yaxis.set_tick_params(labelsize=16)
    axs1.spines['top'].set_visible(False)
    axs1.get_xaxis().set_visible(False)
    axs1.tick_params(left=False, right=True, labelleft=False, labelright=True,
                    bottom=False, labelbottom=True)
    axs1.tick_params(axis='y', colors='r')
    # plt.savefig(f"raster_{words}.png", dpi=300)

    return axs, axs1



def plotly_raster_with_fr(train:list, title:list, bin_size=0.1, w=5, avg=False):
    bins, fr_avg = utils.get_population_fr(trains=train, bin_size=bin_size, w=w, average=avg)

    fig = go.Figure()

    y = 0
    for vv in train:
        fig.add_trace(go.Scatter(x=vv, y=[y]*len(vv), mode='markers', marker=dict(symbol='line-ns-open', size=4, color='black', opacity=0.7)))
        y += 1

    fig.update_layout(title=f"raster_{title}", title_font_size=12, xaxis_title="Time (s)", yaxis_title="Unit", font=dict(size=16))

    fig.update_xaxes(tickfont=dict(size=16))
    fig.update_yaxes(tickfont=dict(size=16))

    fig.update_layout(yaxis2=dict(overlaying='y', side='right', title='Population Firing Rate (Hz)', title_font=dict(size=16), tickfont=dict(size=16)))
    fig.add_trace(go.Scatter(x=bins[1:], y=fr_avg, mode='lines', line=dict(color='red', width=3, opacity=0.5), yaxis='y2'))

    fig.show()


def plot_raster_for_chip(train_dict: dict, words: list):
    for chip, days in train_dict.items():
        rows = len(days)
        all_days = list(days.keys())
        fig, axs = plt.subplots(rows, 1, figsize=(16, 6*rows), tight_layout=True)
        plt.suptitle(f"raster_of_chip{chip}_{words}", fontsize=12)
        for d, train in days.items():
            i = all_days.index(d)
            plot_raster_with_fr(train=train, words=[], axs=axs[i], use_axs=True)
        plt.savefig(f"raster_of_chip{chip}_{words}.png", dpi=300)


def plot_distribution(data_dict, func=utils.get_group_data, type="violin", p_test=True, title="distribution", 
                      ylim=[0, 9], ylabel="LABEL", save=False, verbose=False):
    for clt, culture in data_dict.items():
        all_grp = list(culture.keys())
        for n in range(0, len(all_grp), 2):    
            if all_grp[n][0] != "C":
                grp = all_grp[n+1], all_grp[n]
            else:
                grp = all_grp[n], all_grp[n+1]
            
            if verbose:
                print(f"Culture {clt}, Group {grp}")

            fig, axs = plt.subplots(1, 1, figsize=(7, 5), constrained_layout=True)
            axs.set_title(f"{title} of {clt}, {grp}", fontsize=16)

            cv_pairs = func(data_dict, clt, grp)

            control, patient = cv_pairs
            control_mean = [np.mean(value) for d, value in control.items()]
            patient_mean = [np.mean(value) for d, value in patient.items()]
            df = pd.DataFrame([[label, val, grp[0]] for label, values in control.items() for val in values]
                        + [[label, val, grp[1]] for label, values in patient.items() for val in values],
                        columns=['days', 'value', 'source'])

            if type == "violin":
                axs = sns.violinplot(data=df, x='days', y='value', hue='source', inner="box",
                                    
                            palette=['cornflowerblue', 'indianred'], ax=axs)
            else:
                axs = sns.boxplot(data=df, x='days', y='value', hue='source', showfliers=False,
                            palette=['cornflowerblue', 'indianred'], ax=axs)
            # draw the mean
            axs.plot(np.arange(len(control_mean)), control_mean, "-x", color='b', linewidth=3, alpha=0.7)
            axs.plot(np.arange(len(patient_mean)), patient_mean, "-o", color='r', linewidth=3, alpha=0.7)

            # ks test for each day, print p value
            if p_test:
                p_values = utils.p_test_ks(control, patient)
                axs1 = axs.twinx()
                for i, k in enumerate(p_values):
                    p = p_values[k] 
                    if p <= 0.001:
                        axs1.text(i, 0.8, "***", fontsize=16)
                    elif 0.001 < p <= 0.01:
                        axs1.text(i, 0.8, "**", fontsize=16)
                    elif 0.01 < p <= 0.05:
                        axs1.text(i, 0.8, "*", fontsize=16)
                    else:
                        axs1.text(i, 0.8, "NS", fontsize=16)
                axs1.get_yaxis().set_visible(False)
                    
            axs.set_ylim(ylim)
            axs.set_ylabel(ylabel, fontsize=16)
            axs.set_xlabel("", fontsize=16)
            axs.xaxis.set_tick_params(labelsize=16)
            axs.yaxis.set_tick_params(labelsize=16)
            axs.legend(loc="upper right", fontsize=12)
            if save:
                plt.savefig(f"{title}_{clt}_{grp}.png", dpi=300)
            plt.show(block=False)

def plot_activity_map(qm_path=None, sd=None, title="", axs=None):
    """
    plot units as dots on the electrode map. 
    Size of the dot indicate the firing rate
    """
    if axs is None:
        fig, axs = plt.subplots(figsize=(11, 6))
    axs.set_title(f"Electrode Map {title}")

    if qm_path is not None:
        train, neuron_data, config, fs = utils.load_curation(qm_path)
        assert len(train) > 0, "No unit found"
        assert len(train) == len(neuron_data), \
        "Incorrect number of units for spike train and neuron data"
    elif sd is not None:
        train = sd.train
        neuron_data = sd.neuron_data[0]
        config = sd.metadata[0]
    else:
        print("To plot, assgin a file path or SpikeData object.")
        return axs

    if isinstance(config, dict):
        pos_x = np.asarray(config["pos_x"])
        pos_y = np.asarray(config["pos_y"])
        axs.scatter(pos_x, pos_y, s=0.2, color='b', alpha=0.3)
    else:
        elec_xy = np.asarray([(x, y) for x in np.arange(0, 3850, 17.5)
                              for y in np.arange(0, 2100, 17.5)])
        axs.scatter(elec_xy[:, 0], elec_xy[:, 1], s=0.2, color='b', alpha=0.3)
        

    rec_len = max([max(t) for t in train])
    for k, data in neuron_data.items():
        scale = len(train[k]) / rec_len
        x, y = data["position"][0], data["position"][1]
        axs.scatter(x, y, s=10*scale, color="g", alpha=0.8)

    axs.scatter(None, None, s=10, color='g', label="1 Hz")
    axs.scatter(None, None, s=50, color='g', label="5 Hz")
    axs.scatter(None, None, s=100, color='g', label="10 Hz")
    axs.legend(loc="upper right", fontsize=12)

    axs.set_xlim(0, 3850)
    axs.set_ylim(0, 2100)
    axs.set_xticks([0, 3850])
    axs.set_yticks([0, 2100])
    axs.xaxis.set_tick_params(labelsize=12)
    axs.yaxis.set_tick_params(labelsize=12)
    axs.set_xlabel(u"\u03bcm", fontsize=16)
    axs.set_ylabel(u"\u03bcm", fontsize=16)
    plt.gca().invert_yaxis()

    return axs

def plot_inset(axs, temp_pos, templates, nelec=2, ylim_margin=0, pitch=17.5):
    assert len(temp_pos) == len(templates), "Input length must be the same!"
    # find the max template
    if isinstance(templates, list):
        templates = np.asarray(templates)
    amp = np.max(templates, axis=1) - np.min(templates, axis=1)
    max_amp_index = np.argmax(amp)
    position = temp_pos[max_amp_index]
    axs.scatter(position[0], position[1], linewidth=10, alpha=0.2, color='grey')
    axs.text(position[0], position[1], str(position), color="g", fontsize=12)
    # set same scaling to the insets
    ylim_min = min(templates[max_amp_index])
    ylim_max = max(templates[max_amp_index])
    # choose channels that are close to the center channel
    for i in range(len(temp_pos)):
        chn_pos = temp_pos[i]
        if position[0] - nelec * pitch <= chn_pos[0] <= position[0] + nelec * pitch \
                and position[1] - nelec * pitch <= chn_pos[1] <= position[1] + nelec * pitch:
            axin = axs.inset_axes([chn_pos[0]-5, chn_pos[1]-5, 15, 20], transform=axs.transData)
            axin.plot(templates[i], color='k', linewidth=2, alpha=0.7)
            axin.set_ylim([ylim_min - ylim_margin, ylim_max + ylim_margin])
            axin.set_axis_off()
    axs.set_xlim(position[0]-1.5*nelec*pitch, position[0]+1.5*nelec*pitch)
    axs.set_ylim(position[1]-1.5*nelec*pitch, position[1]+1.5*nelec*pitch)
    axs.invert_yaxis()
    return axs


def plot_unit_footprint(qm_path, title="", save_to=None):
    """
    plot footprints for all units in one figure
    """
    _, neuron_data, _ = utils.load_curation(qm_path)

    for k, data in neuron_data.items():
        cluster = data["cluster_id"]
        npos = data["neighbor_positions"]
        ntemp = data["neighbor_templates"]

        fig, axs = plt.subplots(figsize=(4, 4))
        axs = plot_inset(axs=axs, temp_pos=npos, templates=ntemp)
        axs.set_title(f"{title} Unit {cluster} ")
        if save_to is not None:
            plt.savefig(f"{save_to}/footprint_{title}_unit_{cluster}.png", dpi=300)
            plt.close()
                



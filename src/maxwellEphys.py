# class of maxwell ephys data for displaying on the dashbaord
from braingeneers import analysis
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.validators.scatter.marker import SymbolValidator
import plotly.express as px
from plotly.subplots import make_subplots


class MaxWellEphys():
    def __init__(self, phy_path, fr_coef, sttc_delta, sttc_thr, fs=20000):
        """
        load spike sorted data from s3 using analysis.read_phy_files()
        :param phy_path: a s3 path
        :return: a list of spike_times as [spike_times] and neuron_data
        dictionary structured as {new_cluster_id:
        [channel_id, (chan_pos_x, chan_pos_y), [chan_template], {channel_id:cluster_templates}]}
        Generate dataframe for plotting functions
        """
        ephys_data = analysis.read_phy_files(phy_path)
        # TODO: Show these as metadata on the dashboard
        self.rec_length = ephys_data.length
        self.spike_times = ephys_data.train
        self.neuron_data = ephys_data.neuron_data[0]

        chn_pos = np.asarray(list(self.neuron_data.values()), dtype=object)[:, 1]
        chn_pos = np.concatenate(chn_pos).reshape(len(chn_pos), 2)

        self.fs = fs
        ##----- Create channel map -----##
        cluster_num = np.arange(1, len(self.spike_times) + 1)
        fire_rate = ephys_data.rates(unit='Hz') * fr_coef
        chn_map = {"cluster_number": cluster_num,
                   "pos_x": chn_pos[:, 0],
                   "pos_y": chn_pos[:, 1],
                   "fire_rate": fire_rate}
        self.chn_map_df = pd.DataFrame(data=chn_map)
        self.sttc = ephys_data.spike_time_tilings(delt=sttc_delta)

        ##----- Create functional pairs -----##
        paired_direction = {"start_cls": [], "end_cls": [],
                            "start_pos": [], "end_pos": [],
                            "sttc": [], "latency": []}
        for i in range(len(self.spike_times) - 1):  # i, j are the indices to spike_times
            for j in range(i + 1, len(self.spike_times)):
                if self.sttc[i][j] >= sttc_thr:
                    lat = latency(self.spike_times[i], self.spike_times[j], threshold=sttc_delta)
                    pos_count = len(list(filter(lambda x: (x >= 0), lat)))
                    if abs(pos_count - (len(lat) - pos_count)) > 0.8 * len(lat):
                        if np.mean(lat) > 0:
                            pair = [i, j, chn_pos[i], chn_pos[j], self.sttc[i][j], np.mean(lat)]
                        else:
                            pair = [j, i, chn_pos[j], chn_pos[i], self.sttc[i][j], abs(np.mean(lat))]
                        for ind, k in enumerate(paired_direction.keys()):
                            paired_direction[k].append(pair[ind])
        self.paired_dir_df = pd.DataFrame(data=paired_direction)

        ##----- Create raster data -----##
        self.raster_x = []
        self.raster_y = []

        for i in range(len(cluster_num)):
            self.raster_x.extend(self.spike_times[i])
            self.raster_y.extend([cluster_num[i]] * len(self.spike_times[i]))

        ##----- Others -----##
        self.colors = {'background': 'white', 'borderline': 'black'}

    def print_ephys(self):
        print("Recording length: {} minutes".format(self.rec_length / 1000 / 60))
        print("Number of neurons: ", len(self.spike_times))

    def plot_raster(self):
        """
        :return: The raster plot figure and the df that the raster plot is created by, in order to change color later
        """
        fr_bins, firing_rate = moving_fr_rate(self.spike_times)
        # fig_raster = go.Figure()
        raw_symbols = SymbolValidator().values
        fig_raster = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                                   row_width=[0.2, 0.7])

        fig_raster.add_trace(go.Scattergl(
            # x=self.raster_df['spike_times'],
            # y=self.raster_df['cluster_number'],
            x=self.raster_x,
            y=self.raster_y,
            mode='markers',
            marker=dict(size=4, color='black', symbol='line-ns'),
            # labels={'y': "Unit"}
        ), row=1, col=1)

        fig_raster.add_trace(go.Scattergl(
            x=fr_bins[:-1], y=firing_rate,
            mode='lines',
            # labels={'x': "Time (ms)", 'y': "Rate (Hz)"}
        ), row=2, col=1)

        fig_raster.update_xaxes(showticklabels=False)
        fig_raster.update_xaxes(showticklabels=True, row=2, col=1)

        fig_raster.update_xaxes(showline=True, linewidth=1, linecolor=self.colors['borderline'], mirror=True)
        fig_raster.update_yaxes(showline=True, linewidth=1, linecolor=self.colors['borderline'], mirror=True)
        fig_raster.update_layout(showlegend=False,
                                 font=dict(size=16),
                                 margin=dict(b=55, l=70, r=0, t=0),
                                 plot_bgcolor=self.colors['background'],
                                 paper_bgcolor=self.colors['background'])

        return fig_raster

    def plot_map(self):
        """
        # TODO: allow option of showing functional network
        plot electrode map
        :return: a figure of the map
        """
        circle_colors = ['#000000'] * self.chn_map_df['pos_x'].size
        # circle_colors[-1] = '#a3a7e4'
        elec_xy = np.asarray([(x, y) for x in np.arange(0, 3850, 17.5)
                              for y in np.arange(0, 2100, 17.5)])
        fig1 = px.scatter(x=elec_xy[:, 0], y=elec_xy[:, 1])
        fig1.update_traces(marker=dict(size=1, color=["blue"] * len(elec_xy)))
        fig1.update_layout(hovermode=False)
        fig2 = px.scatter(self.chn_map_df, x="pos_x", y="pos_y", hover_name="cluster_number",
                          size="fire_rate",
                          labels={"pos_x": u"\u03BC" + "m", "pos_y": u"\u03BC" + "m"})
        fig2.update_traces(marker=dict(color=circle_colors))
        fig_map = go.Figure(data=fig1.data + fig2.data)

        fig_map.update_yaxes(range=[0, 2100], tickvals=[0, 2100], autorange="reversed", showline=True, linewidth=1,
                             linecolor=self.colors['borderline'],
                             mirror=True)
        fig_map.update_xaxes(range=[0, 3850], tickvals=[0, 3850], showline=True, linewidth=1, linecolor=self.colors['borderline'],
                             mirror=True)
        fig_map.update_layout(xaxis_title=u"\u03BC" + "m", yaxis_title=u"\u03BC" + "m",
                              font=dict(size=16),
                              width=770, height=420, autosize=True,
                              margin=dict(b=0, l=0, r=0, t=0),
                              plot_bgcolor=self.colors['background'],
                              paper_bgcolor=self.colors['background'])

        return fig_map, circle_colors

    def plot_template(self, n):
        """
        Plot a spike template and its neighbors for a chosen unit from the electrode map.
        :param n: index to the neurons, range [0, cluster_number]
        :return: a template figure object
        """
        template = self.neuron_data[n][2]
        xx = np.arange(0, len(template) / self.fs, 1 / self.fs) * 1000  # unit is ms
        fig_temp = px.line(x=xx, y=template, labels={'x': "Time (ms)"})
        fig_temp.update_yaxes(visible=False, showticklabels=False)
        fig_temp.update_layout(font=dict(size=16),
                               margin=dict(b=0, l=0, r=0, t=0),
                               plot_bgcolor=self.colors['background'],
                               paper_bgcolor=self.colors['background']
                               )
        return fig_temp

    def plot_isi(self, n):
        """
        Plot interspike interval distribution for a chosen unit from the electrode map.
        :param n: index to the neurons, range [0, cluster_number]
        :return: a template figure object
        """
        isi = np.diff(self.spike_times[n])
        fig_isi = px.histogram(isi, nbins=round(max(isi)))
        fig_isi.update_layout(xaxis_title="Time (ms)", yaxis_title="Count", font=dict(size=16))
        fig_isi.update_layout(xaxis_range=[0, 100])
        fig_isi.update_layout(showlegend=False,
                              margin=dict(b=0, l=0, r=0, t=0),
                              plot_bgcolor=self.colors['background'],
                              paper_bgcolor=self.colors['background']
                              )
        return fig_isi


def moving_fr_rate(spike_times: list, rec_length=None, bin_size=100):
    spike_times_all = np.sort(np.hstack(spike_times))
    if rec_length is None:
        rec_length = spike_times_all[-1]
    bin_num = int(rec_length // bin_size) + 1
    bins = np.linspace(0, rec_length, bin_num)
    moving = [np.histogram(spike_times_all, bins + i)[0] for i in range(bin_size)]
    moving_fr = np.mean(moving, axis=0) / bin_size * 1000  # hz
    return bins, moving_fr


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

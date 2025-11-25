# make dashboard plots
from maxwellEphys import MaxWellEphys
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# TODO: add stats for firing rate, isi, burst distribution
class PlotEphys(MaxWellEphys):
    def __init__(self, phy_path, fr_coef, sttc_delta, sttc_thr):
        super().__init__(phy_path, fr_coef, sttc_delta, sttc_thr, fs=20000.0)
        self.colors = {'background': 'white', 'borderline': 'black'}
        print(self.colors)

    def plot_raster(self):
        """
        :return: The raster plot figure and the df that the raster plot is created by,
        in order to change color later
        """
        raster_x, raster_y, fr_bins, firing_rate = self.raster()
        # fig_raster = go.Figure()
        fig_raster = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                                   row_width=[0.2, 0.7])

        fig_raster.add_trace(go.Scattergl(
            # x=self.raster_df['spike_times'],
            # y=self.raster_df['cluster_number'],
            x=raster_x,
            y=raster_y,
            mode='markers',
            marker=dict(size=4, color='black', symbol='line-ns'),
            # labels={'y': "Unit"}
            yaxis="y1"
        ), row=1, col=1)

        fig_raster.add_trace(go.Scattergl(
            x=fr_bins[:-1], y=firing_rate / len(self.spike_times),
            mode='lines',
            # labels={'x': "Time (s)", 'y': "Rate (Hz)"}
            xaxis="x2",
            yaxis="y2"
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
        fig_raster.update_layout(yaxis=dict(title="Unit"), yaxis2=dict(title="Rate (Hz)"),
                                 xaxis2=dict(title="Time (s)"))

        return fig_raster

    def plot_raster_fr(self):
        bins, fr_avg = self.two_step_smooth()

        fig = go.Figure()
        y = 0
        for vv in self.spike_times:
            fig.add_trace(go.Scatter(x=vv, y=[y] * len(vv), mode='markers',
                                     marker=dict(symbol='line-ns-open', size=3, color='black', opacity=0.7),
                                     showlegend=False))
            y += 1

        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Population Firing Rate (Hz)', title_font=dict(size=16),
                        tickfont=dict(size=16)))
        fig.add_trace(
            go.Scatter(x=bins[1:], y=fr_avg, mode='lines', line=dict(color='rgba(255, 0, 0, 0.5)', width=3), yaxis='y2',
                       showlegend=False))

        fig.update_xaxes(tickfont=dict(size=16))
        fig.update_yaxes(tickfont=dict(size=16))

        fig.update_layout(title_font_size=18,
                          xaxis_title="Time (s)",
                          yaxis_title="Unit",
                          font=dict(size=16),
                          xaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
                          yaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
                          yaxis2=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
                          plot_bgcolor='white'
                          )
        return fig

    def plot_raster_fr_burst(self):
        bins, fr_avg = self.two_step_smooth()
        pop_fr, peak_indices = self.find_peak_loc()
        duration, burst_values = self.burst_width()
        rms = np.sqrt(np.mean(pop_fr ** 2))
        peak_thr = rms * self.rms_scaler
        bins = bins[1:]
        fig = go.Figure()
        y = 0
        for vv in self.spike_times:
            fig.add_trace(go.Scatter(x=vv, y=[y] * len(vv), mode='markers',
                                     marker=dict(symbol='line-ns-open', size=3, color='black', opacity=0.7),
                                     showlegend=False))
        y += 1

        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Population Firing Rate (Hz)', title_font=dict(size=16),
                        tickfont=dict(size=16)))
        fig.add_trace(
            go.Scatter(x=bins[1:], y=fr_avg, mode='lines', line=dict(color='rgba(255, 0, 0, 0.5)', width=3), yaxis='y2',
                       showlegend=False))
        fig.add_trace(
            go.Scatter(x=bins[peak_indices], y=fr_avg[peak_indices],
                       mode='markers', marker=dict(symbol='x', size=10, color='red'),
                       name='Burst Peaks', showlegend=False))
        # widths = [burst_values[1:][0], burst_values[1:][1], burst_values[1:][2]]
        fig.add_trace(go.Scatter(x=[bins[burst_values[1][0]], bins[burst_values[1:][1]]],
                                 y=[burst_values[1:][2], burst_values[1][1]], mode='lines',
                                 line=dict(color='red', width=3), name='Width'))

        fig.add_trace(go.Scatter(x=bins, y=np.full_like(pop_fr, peak_thr), mode='lines',
                                 line=dict(color='magenta', width=3), name='Peak Threshold'))

        fig.update_xaxes(tickfont=dict(size=16))
        fig.update_yaxes(tickfont=dict(size=16))

        fig.update_layout(title_font_size=18,
                          xaxis_title="Time (s)",
                          yaxis_title="Unit",
                          font=dict(size=16),
                          xaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
                          yaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
                          yaxis2=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
                          plot_bgcolor='white'
                          )
        return fig


    def plot_map(self):
        """
        TODO: allow option of showing functional network
        TODO: add configuration
        plot electrode map
        :return: a figure of the map
        """
        config, chn_map_df, _ = self.channel_map()
        print("Config from plot_map:", config)
        circle_colors = ['#000000'] * chn_map_df['pos_x'].size
        # circle_colors[-1] = '#a3a7e4'
        elec_xy = np.asarray([(x, y) for x in np.arange(0, 3850, 17.5)
                              for y in np.arange(0, 2100, 17.5)])
        fig1 = px.scatter(x=elec_xy[:, 0], y=elec_xy[:, 1])
        fig1.update_traces(marker=dict(size=1, color=["blue"] * len(elec_xy)))
        fig1.update_layout(hovermode=False)
        fig2 = px.scatter(chn_map_df, x="pos_x", y="pos_y", hover_name="cluster_number",
                          size="fire_rate",
                          labels={"pos_x": u"\u03BC" + "m", "pos_y": u"\u03BC" + "m"})
        fig2.update_traces(marker=dict(color=circle_colors))
        fig_map = go.Figure(data=fig1.data + fig2.data)

        fig_map.update_yaxes(range=[0, 2100], tickvals=[0, 2100], autorange="reversed", showline=True, linewidth=1,
                             linecolor=self.colors['borderline'],
                             mirror=True)
        fig_map.update_xaxes(range=[0, 3850], tickvals=[0, 3850], showline=True, linewidth=1,
                             linecolor=self.colors['borderline'],
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
        template = self.neuron_dict[n]['template']
        xx = np.arange(0, len(template) / self.fs, 1 / self.fs)  # unit is ms
        fig_temp = px.line(x=xx, y=template, labels={'x': "Time (ms)"})
        fig_temp.update_yaxes(visible=False, showticklabels=False)
        fig_temp.update_layout(font=dict(size=16),
                               margin=dict(b=0, l=0, r=0, t=0),
                               plot_bgcolor=self.colors['background'],
                               paper_bgcolor=self.colors['background']
                               )
        return fig_temp

    # TODO: plot footprint instead of a single template
    def plot_footprint(self, n, pitch=17.5, nelec=2):
        """
        plot the footprint for each selected units
        (1, 1)  (1, 2)  (1, 3)  (1, 4)  (1, 5)
        (2, 1)  (2, 2)  (2, 3)  (2, 4)  (2, 5)
        (3, 1)
        (4, 1)
        (5, 1)
        :return:
        """
        ch, pos, temp_chs, temp_pos, templates = self.get_data_dict(n)
        match_temp = dict(zip(temp_chs, templates))
        selected_channels, selected_positions = self.select_neighbor_channels(n)
        selected_templates = [match_temp[c] for c in selected_channels]
        xx = np.arange(0, len(templates[0]) / self.fs, 1 / self.fs)  # unit is ms
        # make pos as center, get the subplot's location
        rows, cols = int(nelec * 2 + 1), int(nelec * 2 + 1)
        row_c, col_c = int(nelec + 1), int(nelec + 1)
        fig_fp = make_subplots(rows=rows, cols=cols, shared_xaxes="all",
                               shared_yaxes="all")
        neighbor_num = len(selected_channels)
        for i in range(neighbor_num):
            temp_pos = selected_positions[i]
            if temp_pos == pos:
                line_color = 'blue'
            else:
                line_color = 'black'
            r = int(row_c + (temp_pos[1] - pos[1]) // pitch)
            c = int(col_c + (temp_pos[0] - pos[0]) // pitch)
            # print(i, pos, temp_pos, r, c)
            fig_fp.add_trace(go.Scatter(x=xx, y=selected_templates[i], line=dict(color=line_color)),
                             row=r, col=c)
            # same scaling, no background, no grid, no ticks
            fig_fp.update_xaxes(showticklabels=False)
            fig_fp.update_yaxes(showticklabels=False)
            fig_fp.update_layout(showlegend=False,
                                 # margin=dict(b=0, l=0, r=0, t=0),
                                 plot_bgcolor=self.colors['background'],
                                 paper_bgcolor=self.colors['background']
                                 )
        return fig_fp

    def plot_isi(self, n):
        """
        Plot interspike interval distribution for a chosen unit from the electrode map.
        :param n: index to the neurons, range [0, cluster_number]
        :return: a template figure object
        """
        print(len(self.spike_times))
        isi = np.diff(self.spike_times[n])
        fig_isi = px.histogram(isi, nbins=round(max(isi)))
        fig_isi.update_layout(xaxis_title="Time (ms)", yaxis_title="Count", font=dict(size=16))
        fig_isi.update_layout(xaxis_range=[0, 20])
        fig_isi.update_layout(showlegend=False,
                              margin=dict(b=0, l=0, r=0, t=0),
                              plot_bgcolor=self.colors['background'],
                              paper_bgcolor=self.colors['background']
                              )
        return fig_isi

    def plot_amplitudes(self, n):
        """
        plot amplitude distribution
        :param n:
        :return:
        """
        ch, amps = self.get_amplitudes(n)

        fig_amp = make_subplots(rows=1, cols=2, shared_yaxes="all",
                                column_widths=[0.8, 0.2], horizontal_spacing=0)
        fig_amp.add_trace(go.Scatter(x=self.spike_times[n], y=amps, mode='markers'),
                          row=1, col=1)
        fig_amp.add_trace(go.Histogram(y=amps),
                          row=1, col=2)

        fig_amp.update_layout(showlegend=False,
                              plot_bgcolor=self.colors['background'],
                              paper_bgcolor=self.colors['background'])
        fig_amp.update_xaxes(showline=True, linewidth=1, linecolor='black',
                             title="Time (s)", mirror=True, row=1, col=1)
        fig_amp.update_yaxes(showline=True, linewidth=2, linecolor='black',
                             title="Voltage(" + u"\u03BC" + "V)", mirror=True, row=1, col=1)
        fig_amp.update_xaxes(showline=True, linewidth=1, linecolor='black', mirror=True, row=1, col=2)
        fig_amp.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True, row=1, col=2)

        return fig_amp

    def plot_ccg(self, n, bin_size=0.001):
        """
        plot cross-correlogram with lag in [-50, 50]ms with 1ms resolution
        :param n:
        :return:
        """
        orginal = self.spike_times[n]

    def plot_footprint_overall(self):
        """
        plot footprints on electrode map for all units
        Returns:

        """

        pass

    def plot_sttc_heatmap(self):
        coef = self.ephys_data.spike_time_tilings()
        fig_sttc = px.imshow(coef, text_auto=True, aspect="auto")
        fig_sttc.update_layout(xaxis_title="Unit", yaxis_title="Unit", font=dict(size=16))
        return fig_sttc

    def plot_fr_distribution(self):
        fr = self.ephys_data.rates(unit='kHz')  # 'kHz' is actually Hz because input data is second based
        fig_fr = px.histogram(fr, nbins=round(max(fr)))
        fig_fr.update_layout(xaxis_title="Firing Rate (Hz)", yaxis_title="Count", font=dict(size=16))
        fig_fr.update_layout(xaxis_range=[0, 10])
        fig_fr.update_layout(showlegend=False,
                             margin=dict(b=0, l=0, r=0, t=0),
                             plot_bgcolor=self.colors['background'],
                             paper_bgcolor=self.colors['background']
                             )
        return fig_fr

    def plot_ibi(self):
        """
        plot inter burst interval if there is any burst
        Returns:

        """

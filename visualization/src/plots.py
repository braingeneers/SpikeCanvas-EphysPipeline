import numpy as np
import plotly.graph_objects as go
from plotly.validators.scatter.marker import SymbolValidator
import plotly.express as px
from plotly.subplots import make_subplots
import utils
from burst import Network
import plotly.subplots as sp
import logging


class PlotlyEphys:
    def __init__(self, spike_data, bin_size=0.05, win=5, avg=False,
                 win_tiling=0.02,
                 gaussian=True, sigma=5, burst_rms_thr=3, title=None):
        self.fs = spike_data["fs"]
        if isinstance(spike_data["train"], dict):
            self.train = [t/self.fs for _, t in spike_data["train"].items()]
        elif isinstance(spike_data["train"], list):
            self.train = [t/self.fs for t in spike_data["train"]]
        else:
            raise ValueError("spike_data['train'] should be a list or dict")
        logging.info(f"Plotting for {len(self.train)} units")

        self.rec_len = np.max([t[-1] for t in self.train])
        print(f"Recording length: {self.rec_len}")

        self.neuron_data = spike_data["neuron_data"]

        if "config" in spike_data:
            self.config = spike_data["config"]
        else:
            self.config = None

        # parameters for burst detection
        self.bin_size = bin_size
        self.win = win
        self.avg = avg
        self.gaussian = gaussian
        self.sigma = sigma
        self.win_tiling = win_tiling
        self.title = title

        pb = Network(spike_data={"train": self.train,
                                 "neuron_data": self.neuron_data,
                                 "config": self.config,
                                 "fs": self.fs}, 
                                 rms_scaler=burst_rms_thr)
        self.fr, bins, self.peak_indices = pb.find_peak_loc()
        logging.info(f"Found {len(self.peak_indices)} peaks")
        self.duration, self.peak_widths = pb.burst_width()
        logging.info(f"Peak duration {self.duration}")
        self.bins = bins[1:]
        self.peak_thr = pb.peak_thr
        self.sttc = pb.spike_time_tilings(delt=self.win_tiling)

        # parameters for plotting
        self.tick_size = 12
        self.axis_title_size = 14
        self.bg_color = "white"
        self.standoff = 2
        self.edge_lw = 1

    def plot_html_page(self):
        """
        generate one html page that summarize the data
        plot grid:
        [(1, 1) x, y] [(1, 2) x2, y2, y3]
        [(2, 1) x3, y4] [(2, 2) x4, y5, y6]
        :return:
        """
        fig = sp.make_subplots(rows=4, cols=4,
                               column_widths=[0.25, 0.25, 0.25, 0.25],  # Adjust the width ratio as needed
                               horizontal_spacing=0.05,
                               vertical_spacing=0.1,
                               subplot_titles = ["Activity Map", "Raster", "ISI/unit",
                                                 "Footprint", "Raster with Burst", "Spike Time Tiling Coefficient",
                                                 "Firing Rate", "Amplitude", "Minimum ISI", "Template Overlay",
                                                 "Burst Duration", "Inter-Burst Interval", "Burst Peak Freq", "Burstiness"],
                               specs=[[{}, {"colspan": 2}, None, {}],
                                      [{}, {"colspan": 2, "secondary_y": True}, None, {}],
                                      [{}, {}, {}, {}],
                                      [{}, {}, {}, {}]])
        # start plotting each subplot
        ### 1. 
        logging.info("Plotting activity map ...")
        fig11 = self.activity_map()
        for trace in fig11.data:
            fig.add_trace(trace, row=1, col=1)
        fig.update_xaxes(range=[0, 3850], tickvals=[0, 3850],
                         tickfont=dict(size=self.tick_size), title_text=u"\u03bcm",
                         title_font=dict(size=self.axis_title_size),
                         title_standoff=self.standoff,
                         row=1, col=1)
        fig.update_yaxes(range=[2100, 0], tickvals=[0, 2100],
                         tickfont=dict(size=self.tick_size), title_text=u"\u03bcm",
                         title_font=dict(size=self.axis_title_size),
                         title_standoff=self.standoff,
                         row=1, col=1)
        # fig.update_layout(legend=dict(yanchor='bottom', xanchor='center', y=-0.45, x=0.5, orientation='h'))
        
        ### 2.
        logging.info("Plotting raster ...")
        fig12 = self.raster_with_fr()
        for trace in fig12.data:
            if trace.yaxis == 'y2':
                continue
            else:
                fig.add_trace(trace, row=1, col=2)

        ### 3.
        logging.info("Plotting isi of unit ...")
        fig14 = self.isi_single_unit()
        for trace in fig14.data:
            fig.add_trace(trace, row=1, col=4)
        # fig.update_xaxes(range=[0, 1000], 
        #                  tickvals=[0, 200, 400, 600, 800, 1000], 
        #                  row=1, col=4)

        ### 4.
        logging.info("Plotting footprint ...")
        fig21 = self.footprint_map()
        for trace in fig21.data:
            fig.add_trace(trace, row=2, col=1)
        fig.update_xaxes(range=[0, 3850], tickvals=[0, 3850],
                         tickfont=dict(size=self.tick_size), title_text=u"\u03bcm",
                         title_font=dict(size=self.axis_title_size),
                         title_standoff=self.standoff,
                         row=2, col=1)
        fig.update_yaxes(range=[2100, 0], tickvals=[0, 2100],
                         tickfont=dict(size=self.tick_size), title_text=u"\u03bcm",
                         title_font=dict(size=self.axis_title_size),
                         title_standoff=self.standoff,
                         row=2, col=1)

        ### 5.
        logging.info("Plotting raster with burst detection ...")
        fig22 = self.raster_with_burst()
        for trace in fig22.data:
            if trace.yaxis == 'y2':
                # print(trace)
                fig.add_trace(trace, row=2, col=2, secondary_y=True)
            else:
                fig.add_trace(trace, row=2, col=2, secondary_y=False)
        # fig.add_shape(go.layout.Shape(type='line', x0=0, y0=self.peak_thr,
        #                               x1=self.bins[-1], y1=self.peak_thr,
        #                               line=dict(color='magenta', width=3, dash='dash'),
        #                               yref='y2'
        #                               ), row=2, col=2, secondary_y=True)

        ### 6.
        logging.info("Plotting sttc heatmap ...")
        fig24 = self.sttc_heatmap()
        for trace in fig24.data:
            fig.add_trace(trace, row=2, col=4)

        ### 7.
        logging.info("Plotting firing distribution ...")
        fig31 = self.firing_distribution()
        for trace in fig31.data:
            fig.add_trace(trace, row=3, col=1)
        fig.update_xaxes(range=[0, 8], tickvals=[0, 2, 4, 6, 8], row=3, col=1)

        ### 8.
        logging.info("Plotting amplitude distribution ...")
        fig32 = self.amplitude_distribution()
        for trace in fig32.data:
            fig.add_trace(trace, row=3, col=2)
        fig.update_xaxes(range=[0, 100], tickvals=np.arange(0, 100, 10), row=3, col=2)
        
        ### 9.
        logging.info("Plotting minimum ISI duration ...")
        fig33 = self.minimum_isi_distribution()
        for trace in fig33.data:
            fig.add_trace(trace, row=3, col=3)
        fig.update_xaxes(range=[0, 50], tickvals=np.arange(0, 50, 10), row=3, col=3)

        ### 10.
        logging.info("Plotting spike waveform for all neurons ...")
        fig34 = self.waveform_overlay()
        for trace in fig34.data:
            fig.add_trace(trace, row=3, col=4)

        ### 11.
        logging.info("Plotting burst duration ...")
        fig41 = self.burst_duration_distribution()
        for trace in fig41.data:
            fig.add_trace(trace, row=4, col=1)
        fig.update_xaxes(showticklabels=False, row=4, col=1)

        ### 12.
        logging.info("Plotting inter-burst interval ...")
        fig42 = self.burst_interval_distribution()
        for trace in fig42.data:
            fig.add_trace(trace, row=4, col=2)
        fig.update_xaxes(showticklabels=False, row=4, col=2)

        ### 13.
        logging.info("Plotting firing rate for burst peaks ...")
        fig43 = self.burst_peak_freq()
        for trace in fig43.data:
            fig.add_trace(trace, row=4, col=3)
        fig.update_xaxes(showticklabels=False, row=4, col=3)

        ### 14.
        logging.info("Plotting burstiness ...")
        fig44 = self.burstiness()
        for trace in fig44.data:
            fig.add_trace(trace, row=4, col=4)
        fig.update_xaxes(showticklabels=False, row=4, col=4)

        ### layout
        def set_axis(title:str):
            return dict(title=title,
                        title_font=dict(size=self.axis_title_size),
                        title_standoff=self.standoff,
                        tickfont=dict(size=self.tick_size),
                        mirror=False,
                        linecolor='black',
                        linewidth=self.edge_lw)
        fig.update_layout(# 1. activity map
                          xaxis1=set_axis(""),
                          yaxis1=set_axis(""),
                          # 2. raster 
                          xaxis2=set_axis("Time (s)"),
                          yaxis2=set_axis("Unit"),
                          # 3. isi of unit
                          xaxis3=set_axis("Interspike Interval (ms)"),
                          yaxis3=set_axis(title="Unit"),
                          # 4. footprint map
                          xaxis4=dict(mirror=False, 
                                      linecolor='black', 
                                      linewidth=self.edge_lw, 
                                      matches='x1'),
                          yaxis4=set_axis(""),
                          # 5. raster with fr
                          xaxis5=set_axis("Time (s)"),
                          yaxis5=set_axis("Unit"),
                          ## no xaxis for yaxis6 because it is shared with xaxis3
                          yaxis6=dict(side='right',
                                      title='Population Firing Rate (Hz)',
                                      title_font=dict(size=self.axis_title_size),
                                      title_standoff=self.standoff,
                                      tickfont=dict(size=self.tick_size),
                                      linecolor='black',
                                      linewidth=self.edge_lw),
                          # 6. sttc heatmap
                          xaxis6=set_axis("Unit"),
                          yaxis7=set_axis("Unit"),
                          # 7. firing distribution
                          xaxis7=set_axis("Firing Rate (Hz)"),
                          yaxis8=set_axis("Percent"),
                          # 8. amplitude distribution
                          xaxis8=set_axis("Amplitude (uV)"),
                          yaxis9=set_axis("Percent"),
                          # 9. minimum isi distribution
                          xaxis9=set_axis("Minimum ISI (ms)"),
                          yaxis10=set_axis("Percent"),
                          # 10. template for all units
                          xaxis10=set_axis("Time (ms)"),
                          yaxis11=set_axis("Voltage (uV)"),
                          # 11. burst duration
                          xaxis11=set_axis(""),
                          yaxis12=set_axis("Burst Duration (s)"),
                          # 12. inter-burst interval
                          xaxis12=set_axis(""),
                          yaxis13=set_axis("Inter-Burst Interval (s)"),
                          # 13. burst peak freq
                          xaxis13=set_axis(""),
                          yaxis14=set_axis("Population Firing Rate (Hz)"),
                          # 14. burstiness
                          xaxis14=set_axis(""),
                          yaxis15=set_axis("Burstiness"),
                        )
        fig.update_layout(title=f'{self.title} overview', 
                          title_font=dict(size=20),
                          autosize=False,
                          height=1200, width=1680 )
        fig.update_layout(plot_bgcolor=self.bg_color)
        return fig

    def raster(self):
        fig = go.Figure()
        y = 0
        for vv in self.train:
            fig.add_trace(go.Scatter(x=vv, y=[y] * len(vv), mode='markers',
                                     marker=dict(symbol='line-ns-open', size=1.5, color='black', opacity=0.7),
                                     showlegend=False))
            y += 1
   
        fig.update_xaxes(tickfont=dict(size=16))
        fig.update_yaxes(tickfont=dict(size=16))
        fig.update_layout(
            title=f"raster of {self.title}",
            title_font_size=18,
            xaxis_title="Time (s)",
            yaxis_title="Unit",
            font=dict(size=16),
            xaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            plot_bgcolor=self.bg_color
        )

        return fig

    def raster_with_fr(self):
        fig = go.Figure()
        y = 0
        for vv in self.train:
            fig.add_trace(go.Scatter(x=vv, y=[y] * len(vv), mode='markers',
                                     marker=dict(symbol='line-ns-open', size=1.5, color='black', opacity=0.7),
                                     showlegend=False))
            y += 1

        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Population Firing Rate (Hz)', title_font=dict(size=16),
                        tickfont=dict(size=16)))
        fig.add_trace(
            go.Scatter(x=self.bins, y=self.fr, mode='lines', line=dict(color='rgba(255, 0, 0, 0.5)', width=3),
                       yaxis='y2',
                       showlegend=False))

        fig.update_xaxes(tickfont=dict(size=16))
        fig.update_yaxes(tickfont=dict(size=16))
        fig.update_layout(
            title=f"raster of {self.title}",
            title_font_size=18,
            xaxis_title="Time (s)",
            yaxis_title="Unit",
            font=dict(size=16),
            xaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis2=dict(showgrid=True, gridcolor='lightgray', linecolor='red', linewidth=3,
                        range=[0, 1.5 * max(self.fr)]),
            plot_bgcolor=self.bg_color
        )

        return fig

    def raster_with_burst(self):
        """
        raster plot with burst detection. Also plot burst summary on another subplot
        """

        fig = go.Figure()
        # Create the population fr trace
        y = 0
        for vv in self.train:
            fig.add_trace(go.Scatter(x=vv, y=[y] * len(vv), mode='markers',
                                     marker=dict(symbol='line-ns-open', size=1.5, color='black', opacity=0.7),
                                     showlegend=False))
            y += 1

        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right', title='Population Firing Rate (Hz)', title_font=dict(size=16),
                        tickfont=dict(size=16)))
        fig.add_trace(
            go.Scatter(x=self.bins, y=self.fr, mode='lines',
                       line=dict(color='rgba(255, 0, 0, 0.5)', width=3), yaxis='y2',
                       showlegend=False))

        # Add horizontal line for peak threshold
        fig.add_shape(go.layout.Shape(type='line', x0=0, y0=self.peak_thr,
                                      x1=self.bins[-1], y1=self.peak_thr,
                                      line=dict(color='magenta', width=3, dash='dash'),
                                      yref='y2'
                                      ))
        # fig.add_hline(y=self.peak_thr, line_width=3, line_dash="dash", line_color="magenta", yaxis='y2')

        if len(self.peak_indices) > 0:
            # Add peaks as markers on the population fr trace
            fig.add_trace(go.Scatter(x=self.bins[self.peak_indices], y=self.fr[self.peak_indices], mode='markers',
                                     marker=dict(size=10, symbol='x', color='red'),
                                     yaxis='y2', name='Burst Peak', showlegend=False))

            # Add widths as horizontal lines
            y_value = self.peak_widths[0]
            burst_start = self.peak_widths[1]
            burst_end = self.peak_widths[2]
            burst_num = len(burst_start)
            for n in range(burst_num):
                fig.add_shape(go.layout.Shape(type='line', x0=burst_start[n], y0=y_value[n],
                                              x1=burst_end[n], y1=y_value[n],
                                              line=dict(color='red', width=3),
                                              yref='y2'))

        fig.update_layout(
            title=f"burst of {self.title}",
            title_font_size=18,
            xaxis_title="Time (s)",
            yaxis_title="Unit",
            font=dict(size=16),
            xaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis2=dict(showgrid=True, gridcolor='lightgray', linecolor='red', linewidth=3,
                        range=[0, 1.5 * max(self.fr)]),
            plot_bgcolor=self.bg_color,
        )

        return fig

    def activity_map(self):
        """
        plot units as dots on the electrode map.
        Size of the dot indicate the firing rate
        """
        fig = go.Figure()
        elec_size = 0.5
        init_size = 1
        fig.update_layout(title=f"Electrode Map of {self.title}")

        # plot configuration
        if isinstance(self.config, dict):
            pos_x = np.asarray(self.config["pos_x"])
            pos_y = np.asarray(self.config["pos_y"])
            fig.add_trace(go.Scatter(x=pos_x, y=pos_y, mode='markers', marker=dict(size=elec_size, color='blue', opacity=0.3),
                                     showlegend=False))
        else:
            elec_xy = np.asarray([(x, y) for x in np.arange(0, 3850, 17.5) for y in np.arange(0, 2100, 17.5)])
            fig.add_trace(go.Scatter(x=elec_xy[:, 0], y=elec_xy[:, 1], mode='markers',
                                     marker=dict(size=elec_size, color='blue', opacity=0.3), showlegend=False))

        rec_len = max([max(t) for t in self.train])
        # print(f"recording length: {rec_len}")

        for k, data in self.neuron_data.items():
            scale = len(self.train[k]) / rec_len
            # print(scale)
            x, y = data["position"][0], data["position"][1]
            fig.add_trace(
                go.Scatter(x=[x], y=[y], mode='markers', marker=dict(size=init_size * scale, color='green', opacity=0.8),
                           showlegend=False))

        # Adding legend traces (hidden)
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=init_size, color='green'), name="1 Hz"))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=5*init_size, color='green'), name="5 Hz"))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=10*init_size, color='green'), name="10 Hz"))

        fig.update_xaxes(range=[0, 3850], tickvals=[0, 3850], tickfont=dict(size=12), title_text=u"\u03bcm")
        fig.update_yaxes(range=[0, 2100], tickvals=[0, 2100], tickfont=dict(size=12), title_text=u"\u03bcm",
                         autorange='reversed')

        return fig

    def footprint_map(self, nelec=2, pitch=17.5, show_location=False):
        """
        all_temp_pos: list of 2d array, each array is the grouped position of the template
        all_templates: list of 2d array, each array is the grouped template
        """
        all_temp_pos = [data["neighbor_positions"] for k, data in self.neuron_data.items()]
        all_templates = [data["neighbor_templates"] for k, data in self.neuron_data.items()]

        templates = np.vstack(all_templates)
        ylim_max = np.max(np.max(templates, axis=1))
        num_unit = len(all_temp_pos)

        # generate a list of colors, use it in a circular way for each unit
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
        colors = colors * (num_unit // len(colors) + 1)

        # Create scatter plot for the max template
        fig = go.Figure()

        for j in range(num_unit):
            temp_pos = all_temp_pos[j]
            templates = all_templates[j]
            position = temp_pos[0]

            fig.add_trace(go.Scatter(x=[position[0]], y=[position[1]], mode='markers',
                                     marker=dict(size=16, opacity=0.4, color='grey'),
                                     showlegend=False))
            if show_location:
                fig.add_trace(go.Scatter(x=[position[0]], y=[position[1]], mode='text',
                                         text=[str(position)], textposition="top center",
                                         textfont=dict(color="green", size=12),
                                         showlegend=False))
            # choose channels that are close to the center channel
            for i in range(len(temp_pos)):
                chn_pos = temp_pos[i]
                temp = templates[i]
                if position[0] - nelec * pitch <= chn_pos[0] <= position[0] + nelec * pitch \
                        and position[1] - nelec * pitch <= chn_pos[1] <= position[1] + nelec * pitch:
                    fig.add_trace(go.Scatter(x=np.arange(len(temp)) / len(temp) * 16 + chn_pos[0],
                                             y=-temp / abs(ylim_max) * 8.7 + chn_pos[1],
                                             line=dict(color=colors[j], width=3),
                                             opacity=0.8,
                                             showlegend=False))

        fig.update_xaxes(range=[0, 3850], tickvals=[0, 3850], tickfont=dict(size=16))
        fig.update_yaxes(range=[0, 2100], tickvals=[0, 2100], tickfont=dict(size=16),
                         autorange="reversed")

        fig.update_layout(xaxis=dict(title=u"\u03BC" + "m", showgrid=False, mirror=True,
                                     showline=True, ticks='outside', zeroline=True,
                                     linecolor='black', linewidth=2),
                          yaxis=dict(title=u"\u03BC" + "m", showgrid=False, mirror=True,
                                     showline=True, ticks='outside', zeroline=True,
                                     linecolor='black', linewidth=2),
                          font=dict(size=16),
                          width=770, height=420, autosize=True,
                          margin=dict(b=10, l=10, r=10, t=10),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color,
                          )
        return fig

    # def connectivity_map(self):
    #     """
    #     map with functional connections (latency between units)
    #     ccg needs to run longer time than sttc. Make this plot 
    #     using sttc or optimize the ccg function    
    # """


    def isi_single_unit(self):
        fig = go.Figure()
        for i, t in enumerate(self.train, start=0):
            isi = np.diff(t)*1000   # unit in ms
            fig.add_trace(go.Box(x=isi, 
                                 name=str(i), 
                                 boxpoints=False, 
                                 orientation='h',
                                 showlegend=False))
        
        # for y, vv in enumerate(self.train):
        #     isi = np.diff(vv)*1000   # unit in ms
        #     isi_filtered = isi[isi < 1000]
        #     fig.add_trace(go.Scatter(x=isi_filtered, y=[y]*len(isi_filtered), mode='markers',
        #                              marker=dict(symbol='line-ns-open', 
        #                                          size=1.5, 
        #                                          color='blue',
        #                                          opacity=0.7),
        #                              showlegend=False))
        
        fig.update_layout(
            title=f"isi of single units",
            title_font_size=18,
            xaxis_title="Time (ms)",
            yaxis_title="Unit",
            font=dict(size=16),
            xaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis=dict(showgrid=True, gridcolor='lightgray', linecolor='black', linewidth=3),
            yaxis2=dict(showgrid=True, gridcolor='lightgray', linecolor='red', linewidth=3,
                        range=[0, 1.5 * max(self.fr)]),
            plot_bgcolor=self.bg_color,
        )

        return fig

    def sttc_heatmap(self):
        maxtrix_size = self.sttc.shape[0]
        fig = go.Figure(data=go.Heatmap(z=self.sttc,
                                        x=np.arange(maxtrix_size),
                                        y=np.arange(maxtrix_size),
                                        colorscale='Viridis',
                                        showscale=True,
                                        colorbar=dict(title="STTC"),
                                        colorbar_x=0.95,
                                        colorbar_y=0.65,
                                        colorbar_len=0.2,
                                        colorbar_thickness=20))
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            title=f"STTC heatmap",
            title_font_size=18,
            height=500, width=500,
            showlegend=False
        )
        return fig

    def sttc_heatmap_hist(self):
        sttc_tri = self.sttc.copy()
        maxtrix_size = sttc_tri.shape[0]
        sttc_tri[np.triu_indices(maxtrix_size, 1)] = np.nan
        fig = go.Figure(data=go.Heatmap(z=sttc_tri,
                                        x=np.arange(maxtrix_size),
                                        y=np.arange(maxtrix_size),
                                        colorscale='Viridis',
                                        showscale=True,
                                        colorbar=dict(title="STTC"),
                                        colorbar_x=1))
        fig.update_yaxes(autorange="reversed")
        fig.add_trace(go.Histogram(x=sttc_tri.flatten(), 
                                   nbinsx=20, 
                                   histnorm='probability density',
                                   marker_color='rgba(0,0,0,0.3)', 
                                   xaxis='x2', 
                                   yaxis='y2',
                                   showlegend=False))
        
        fig.update_layout(
            title=f"STTC heatmap",
            title_font_size=18,
            height=500, width=500,
            xaxis2=dict(domain=[0.65, 1], anchor='y2'),
            yaxis2=dict(domain=[0.5, 1], anchor='x2'),
            showlegend=False
        )
        return fig

    def firing_distribution(self):
        fr = [len(t)/self.rec_len for t in self.train]
        fig = go.Figure(data=[go.Histogram(x=fr, nbinsx=20, 
                                           histnorm='probability', showlegend=False)])
        fig.update_layout(title=f'Firing Rate Distribution', height=500, width=500)
        fig.update_layout(xaxis_title="Firing Rate (Hz)", 
                          yaxis_title="Percent", 
                          font=dict(size=16))
        fig.update_layout(xaxis_range=[0, 10])
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig
    
    def amplitude_distribution(self):
        """
        Amplitude distribution of each unit's average waveform
        amplitude defined as the difference between max and min
        """
        templates = [d["template"] for _, d in self.neuron_data.items()]
        amp = [np.max(t) - np.min(t) for t in templates]
        fig = go.Figure(data=[go.Histogram(x=amp, nbinsx=100,
                                           histnorm='probability', showlegend=False)])
        fig.update_layout(title=f'Amplitude (ptp) Distribution', height=500, width=500)
        fig.update_layout(xaxis_title="Voltage (uV))", 
                          yaxis_title="Percent", 
                          font=dict(size=16))
        # fig.update_layout(xaxis_range=[0, 10])
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig
                              
    

    def minimum_isi_distribution(self):
        min_isi = [np.min(np.diff(t))*1000 for t in self.train]    # unit in ms
        fig = go.Figure(data=[go.Histogram(x=min_isi, nbinsx=int(np.max(min_isi)+1),
                                           histnorm='probability', showlegend=False)])
        fig.update_layout(title=f'Minimum ISI Distribution', height=500, width=500)
        fig.update_layout(xaxis_title="ISI (ms))", 
                          yaxis_title="Percent", 
                          font=dict(size=16))
        fig.update_layout(xaxis_range=[0, 50])
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig
    
    def waveform_overlay(self):
        # TODO: cut waveform shorter and align to peak
        templates = np.array([d["template"] for _, d in self.neuron_data.items()])
        xx = np.arange(templates.shape[1])/self.fs*1000   # unit in ms
        fig = go.Figure()
        for temp in templates:
            fig.add_trace(go.Scatter(x=xx, 
                                     y=temp, 
                                     mode='lines', 
                                     line=dict(color='black', width=1),
                                             opacity=0.3,
                                     showlegend=False))
        fig.update_layout(title=f'All Units Action Potential', height=500, width=500)
        fig.update_layout(xaxis_title="Time (ms)", 
                          yaxis_title="Voltage (uV)", 
                          font=dict(size=16))
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig
             

    def burst_duration_distribution(self):
        fig = go.Figure()
        fig.add_trace(go.Violin(y=self.duration, 
                                box_visible=True, 
                                line_color='black', 
                                meanline_visible=True, 
                                fillcolor='lightseagreen', 
                                opacity=0.6,
                                showlegend=False))
        fig.data[0].update(span=[np.min(self.duration), 
                                 np.max(self.duration)], 
                                 spanmode='manual')
        fig.update_layout(title=f'Burst Duration', height=500, width=500)
        fig.update_layout(xaxis_title="", 
                          yaxis_title="Burst Duration (s)", 
                          font=dict(size=16))
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig
        

    def burst_interval_distribution(self):
        """
        Burst interval defined as peak to peak interval
        """
        ibi = np.diff(self.bins[self.peak_indices]) 
        fig = go.Figure()
        fig.add_trace(go.Violin(y=ibi, 
                                box_visible=True, 
                                line_color='black', 
                                meanline_visible=True, 
                                fillcolor='darkturquoise', 
                                opacity=0.6,
                                showlegend=False))
        fig.data[0].update(span=[np.min(ibi), np.max(ibi)], spanmode='manual')
        fig.update_layout(title=f'Inter-Burst Interval', height=500, width=500)
        fig.update_layout(xaxis_title="", 
                          yaxis_title="Inter-Burst Interval (s)", 
                          font=dict(size=16))
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig
        

    def burstiness(self):
        """
        Burstiness defined as number of spikes in burst / total number of spikes, for each unit
        """
        burst_start = self.peak_widths[1]
        burst_end = self.peak_widths[2]
        burst_num = len(burst_start)
        burstiness = []
        burst_spikes = []
        for i, t in enumerate(self.train):
            for n in range(burst_num):
                # print(n, t[(t > burst_start[n]) & (t < burst_end[n])])
                burstiness.append(len(t[(t > burst_start[n]) & (t < burst_end[n])])/len(t))
                burst_spikes.append(len(t[(t > burst_start[n]) & (t < burst_end[n])]))

        burstiness_overall = np.sum(burst_spikes)/np.sum([len(t) for t in self.train])

        fig = go.Figure()
        fig.add_trace(go.Violin(y=burstiness,
                                box_visible=True,
                                line_color='black',
                                meanline_visible=True,
                                fillcolor='cadetblue',
                                opacity=0.6,
                                showlegend=False))
        fig.data[0].update(span=[np.min(burstiness), 
                                 np.max(burstiness)], 
                                 spanmode='manual')
        fig.update_layout(title=f'Burstiness', height=500, width=500)
        fig.update_layout(xaxis_title="",
                            yaxis_title="Burstiness",
                            font=dict(size=16))
        fig.update_layout(showlegend=False,
                            margin=dict(b=0, l=0, r=0, t=0),
                            plot_bgcolor=self.bg_color,
                            paper_bgcolor=self.bg_color
                            )
        return fig

            


    def burst_peak_freq(self):
        burst_freq = self.fr[self.peak_indices]
        fig = go.Figure()
        fig.add_trace(go.Violin(y=burst_freq, 
                                box_visible=True, 
                                line_color='black', 
                                meanline_visible=True, 
                                fillcolor='dodgerblue', 
                                opacity=0.6,
                                showlegend=False))
        fig.data[0].update(span=[np.min(burst_freq),
                                 np.max(burst_freq)], 
                                 spanmode='manual')
        fig.update_layout(title=f'Firing Rate of Burst Peaks', height=500, width=500)
        fig.update_layout(xaxis_title="", 
                          yaxis_title="Population Firing Rate (Hz)", 
                          font=dict(size=16))
        fig.update_layout(showlegend=False,
                          margin=dict(b=0, l=0, r=0, t=0),
                          plot_bgcolor=self.bg_color,
                          paper_bgcolor=self.bg_color
                        )
        return fig

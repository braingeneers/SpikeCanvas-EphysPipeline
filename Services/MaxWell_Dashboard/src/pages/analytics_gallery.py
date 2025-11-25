# # analytics page for displaying multiple recordings or many single units from one recording
# # copied from analyics.py
# import dash
# from dash import Dash, html, dcc, Input, Output, ctx, State
# from dash import callback
# import plotly
# import dash_daq as daq
# import dash_bootstrap_components as dbc
# import braingeneers.utils.s3wrangler as wr
# from maxwellEphys import *
# from make_plots import PlotEphys
# import time
# import sys
# import os
# import numpy as np
#
# sys.path.append('..')
# import utils
# from values import *
#
#
# # dash setting
# # dash.register_page(__name__)
#
# fig_map = plotly.subplots.make_subplots(rows=1, cols=1)
# fig_raster = plotly.subplots.make_subplots(rows=1, cols=1)
# isi_plot = plotly.subplots.make_subplots(rows=1, cols=1)
# template_plot = plotly.subplots.make_subplots(rows=1, cols=1)
# fig_sttc = plotly.subplots.make_subplots(rows=1, cols=1)
# fig_fr_dist = plotly.subplots.make_subplots(rows=1, cols=1)
# # ccg, bursts, connectivity
#
# ###### variables #######
# sttc_delta = 20
# sttc_thr = 0.35
# fr_coef = 10
# ########## end ##########
#
# ####----------------------- make page -----------------------####
# # all figures
# electrode = dbc.Card(
#     dcc.Graph(id='electrode_map',
#               figure=fig_map, ))
# raster = dbc.Card(
#     dcc.Graph(id='raster_plot',
#               figure=fig_raster, ))
# template = dbc.Card(
#     dcc.Graph(id='template_plot',
#               figure=template_plot, ))
# sttc_heatmap = dbc.Card(
#     dcc.Graph(id='sttc_heatmap',
#               figure=fig_sttc, ))
# fr_dist = dbc.Card(
#     dcc.Graph(id='firing_rate_distribution',
#               figure=fig_fr_dist, ))
# isi = dbc.Card(
#     dcc.Graph(id='isi_plot',
#               figure=isi_plot, ))
#
# overview_figures_layout = dbc.Row(dbc.Card(
#     dbc.Row([
#         dbc.Col(electrode),
#         dbc.Col([
#             dbc.Row([
#                 dbc.Col(fr_dist),
#                 dbc.Col(sttc_heatmap)]),
#         ]),
#         dbc.Row(raster)
#     ])
# ))
#
# layout = dbc.Container([
#     html.H2("Ephys Visualization"),
#     html.Hr(),
#     # Dropdowns
#     dbc.Row(html.Div(['Dataset (UUID), Filter UUID by Keyword: ',
#                       dcc.Textarea(id='textarea_filter_uuid',
#                                    placeholder="enter you keyword here",
#                                    value='',
#                                    style={'width': '30%', 'height': 25}, ),
#                       dcc.Dropdown(id="dropdown_uuid",
#                                    options=[],
#                                    value="",
#                                    disabled=False),
#                       dcc.Dropdown(id="dropdown_data",
#                                    options=[],
#                                    value="",
#                                    disabled=False),
#                       # dcc.Dropdown(id="dropdown_derived",
#                       #              options=[],
#                       #              value="",
#                       #              disabled=False),
#                       ])),
#
#     html.Br(),
#     # Spike sorting button
#     # html.Div(
#     #     children=[
#     #         dbc.Row([
#     #             dbc.Col(
#     #                 dbc.Card(
#     #                     dbc.CardBody([
#     #                         html.P("This dataset is raw. Run spike sorting?"),
#     #                         dbc.Button("START", id="spike_sorting_btn", outline=True, color="success",
#     #                                    className="me-1"),
#     #                         html.Span(id="container-button", style={"verticalAlign": "middle"})
#     #                     ])
#     #                 ), width=4
#     #             )
#     #         ]),
#     #     ], style={'display': 'none'}, id="show_button"),
#     # html.Br(),
#     # figure layout (using dbc.card)
#     dbc.Row(overview_figures_layout)
#
# ])
#
#
# #######################--------------- callback functions ---------------#######################
# @callback(
#     Output('dropdown_uuid', 'options'),
#     Input('textarea_filter_uuid', 'value'),
# )
# def drop_down(value=None):
#     return utils.filter_dropdown(search_value=value)
#
#
# @callback(
#     Output("dropdown_data", "options"),
#     Input("dropdown_uuid", "value"),
#     prevent_initial_call=True
# )
# def dropdown_data(uuid):
#     data_path = os.path.join(uuid, "original/data")
#     return wr.list_objects(data_path)
#
#
# # add load figure button
#
# # @callback(
# #     Output('container-button', 'children'),
# #     # Output('spike_sorting_btn', 'disabled'),
# #     Input('spike_sorting_btn', 'n_clicks'),
# #     Input('dropdown_data', 'value'),
# # )
# # def spike_sorting_button(n_clicks, sub_plot_value):
# #     prefix = "dash-ss-"
# #     file_name = sub_plot_value.split('original/data/')[1]
# #     if ".raw.h5" in file_name:
# #         file_name = list(file_name.split(".raw.h5")[0])
# #     elif ".h5" in file_name:
# #         file_name = list(file_name.split(".h5")[0])
# #
# #     for i in range(len(file_name)):
# #         if file_name[i] == "_" or file_name[i] == ".":
# #             file_name[i] = "-"
# #         elif file_name[i].isupper():
# #             file_name[i] = file_name[i].lower()
# #     if len(file_name) >= (63 - len(prefix)):
# #         file_name = file_name[-(63 - len(prefix)) + 1:]
# #         if file_name[0] == '-':
# #             file_name[0] = "x"
# #     file_name = "".join(file_name)
# #     job_name = prefix + file_name
# #     if "spike_sorting_btn" == ctx.triggered_id:
# #         sort_current = Kube(job_name, sub_plot_value)
# #         job_response = sort_current.create_job()
# #         print("Button ", n_clicks)
# #         msg = "Spike sorting started!"
# #         # disable the button
# #         return html.Div(msg)
#
# # show summary figures together with map and raster
# # distribution of firing rate
# # heatmap of sttc with 20ms window
# # burst duration, IBI, burst peak firing rate
# @callback(
#     Output('electrode_map', 'figure', allow_duplicate=True),
#     Output('raster_plot', 'figure', allow_duplicate=True),
#     Output('sttc_heatmap', 'figure'),
#     Output('firing_rate_distribution', 'figure'),
#     Input('dropdown_data', 'value'),
#     prevent_initial_call=True
# )
# def plot_initial_figures(s3_data_path):
#     button_id = ctx.triggered_id if not None else 'No clicks yet'
#     if button_id == 'dropdown_data':
#         ephys_dash = PlotEphys(s3_data_path, fr_coef, sttc_delta, sttc_thr)
#         fig_map, circle_colors = ephys_dash.plot_map()
#         fig_raster = ephys_dash.plot_raster()
#         fig_sttc = ephys_dash.plot_sttc_heatmap()
#         fig_fr_dist = ephys_dash.plot_fr_distribution()
#         print("Initial figures are ready!")
#         return fig_map, fig_raster, fig_sttc, fig_fr_dist
#
# # @callback(
# #     Output('electrode_map', 'figure', allow_duplicate=True),
# #     Output('raster_plot', 'figure', allow_duplicate=True),
# #     Output('isi_plot', 'figure'),
# #     Output('template_plot', 'figure'),
# #     State('electrode_map', 'clickData'),
# #     State('raster_plot', 'clickData'),
# #
# #     prevent_initial_call=True
# # )
# # def plot_elec(electrode_click, raster_click):
# #     global ephys_dash
# #     global fig_map, circle_colors
# #     global fig_raster
# #     global isi_plot
# #     global template_plot
# #     global already_clicked
# #     global raster_lines
# #
# #     button_id = ctx.triggered_id if not None else 'No clicks yet'
# #
# #     already_clicked = set()
# #     if raster_click and button_id == 'raster_plot':
# #         raster_number = raster_click['points'][0]['y']
# #         cluster_number = list(np.arange(1, ephys_dash.ephys_data.N + 1, 1)).index(int(raster_number))
# #         if cluster_number in already_clicked:
# #             circle_colors[cluster_number] = '#000000'
# #             fig_map.update_traces(
# #                 marker=dict(
# #                     color=circle_colors
# #                 )
# #             )
# #             temp_shape = dict(type='line',
# #                               x0=0,
# #                               y0=int(raster_number),
# #                               x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
# #                               y1=int(raster_number),
# #                               xref='x',
# #                               yref='y')
# #             # raster_lines.append(temp_shape)
# #             fig_raster.update_shapes(patch=dict(line=dict(color='rgba(255, 255, 255, 0)'), ), selector=temp_shape)
# #             already_clicked.remove(cluster_number)
# #         else:
# #             # temp_shape = dict(type='line',
# #             #                   x0=0,
# #             #                   y0=int(raster_number),
# #             #                   x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
# #             #                   y1=int(raster_number),
# #             #                   line=dict(color='rgba(0, 255, 0, 0.4)'
# #             #                             , width=6),
# #             #                   xref='x',
# #             #                   yref='y',
# #             #                   )
# #             #
# #             # fig_raster.add_shape(temp_shape, editable=True)
# #             # circle_colors[cluster_number] = '#00FF00'
# #             # # print(circle_colors)
# #             # fig_map.update_traces(
# #             #     marker=dict(
# #             #         color=circle_colors
# #             #     )
# #             # )
# #             isi_plot = ephys_dash.plot_isi(int(cluster_number))
# #             # template_plot = ephys_dash.plot_template(int(cluster_number))
# #             template_plot = ephys_dash.plot_footprint(int(cluster_number))
# #             already_clicked.add(cluster_number)
# #             return fig_map, fig_raster, isi_plot, template_plot
# #     # second_time = time.time()
# #     # print('second', second_time)
# #     # print(second_time - first_time)
# #     if electrode_click and (button_id == 'electrode_map'):
# #         cluster_number = int(electrode_click['points'][0]['pointNumber'])
# #         raster_number = int(electrode_click['points'][0]['hovertext'])
# #         print(f"cluster_number, {cluster_number}")
# #         if cluster_number in already_clicked:
# #             circle_colors[cluster_number] = '#000000'
# #             fig_map.update_traces(
# #                 marker=dict(
# #                     color=circle_colors
# #                 )
# #             )
# #             temp_shape = dict(type='line',
# #                               x0=0,
# #                               y0=int(raster_number),
# #                               x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
# #                               y1=int(raster_number),
# #                               xref='x',
# #                               yref='y'
# #                               )
# #             fig_raster.update_shapes(patch=dict(line=dict(color='rgba(255, 255, 255, 0)'), ), selector=temp_shape)
# #             already_clicked.remove(cluster_number)
# #         else:
# #             print("update after click")
# #             circle_colors[cluster_number] = '#FF0000'
# #             fig_map.update_traces(
# #                 marker=dict(
# #                     color=circle_colors
# #                 )
# #             )
# #
# #             fig_raster.add_shape(type='line',
# #                                  x0=0,
# #                                  y0=int(raster_number),
# #                                  x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
# #                                  y1=int(raster_number),
# #                                  line=dict(color='rgba(222, 13, 13, 0.4)'
# #                                            , width=6),
# #                                  xref='x',
# #                                  yref='y'
# #                                  )
# #             print(f"showing isi...")
# #             isi_plot = ephys_dash.plot_isi(int(cluster_number))
# #             # template_plot = ephys_dash.plot_template(int(cluster_number))
# #             template_plot = ephys_dash.plot_footprint(int(cluster_number))
# #             already_clicked.add(cluster_number)
# #             return fig_map, fig_raster, isi_plot, template_plot

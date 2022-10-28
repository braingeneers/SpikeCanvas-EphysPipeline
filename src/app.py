# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
from dash import Dash, html, dcc, Input, Output, ctx
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import dash_daq as daq
from braingeneers import analysis
import numpy as np
from localPlot import *
from extra import *
import pandas as pd
import plotly.graph_objects as go
from plotly.validators.scatter.marker import SymbolValidator
import braingeneers.utils.s3wrangler as wr


def raster_df(spike_times_dict, map_dict, cutoff=2000000):
    temp_spike = spike_times_dict.copy()
    for i in spike_times_dict.keys():
        if len(spike_times_dict[i]) < 3:
            del temp_spike[i]
    df_dict = {'Cluster_number': [],
               'Spike time': [],
               'Pos': []}
    df = pd.DataFrame(df_dict)
    for key in temp_spike.keys():
        # print(key)
        for value in temp_spike[key]:
            if value < cutoff:
                df.loc[len(df.index)] = [str(map_dict[key]), value, 'blue']

    # print(df)
    return df


def raster_plot(spike_data):
    """

    :param spike_data: A SpikeData class instance
    :return: The raster plot figure and the df that the raster plot is created by, in order to change color later
    """
    good_clusters = spike_data.cluster_channel_map()  # {cluster_id: channel_id}
    spike_times_dict = spike_data.cluster_spike_times(good_clusters)  # {cluster_id: spike_times}
    df = raster_df(spike_times_dict, good_clusters)
    fig2 = go.Figure()
    raw_symbols = SymbolValidator().values

    fig2.add_trace(go.Scatter(
        x=df['Spike time'],
        y=df['Cluster_number'],
        mode='markers',
        marker=dict(
            size=6,
        ),
        marker_symbol=raw_symbols[3 * 137 + 2],
    ))

    fig2.update_layout(autosize=False,
                       width=900,
                       height=700,
                       title="Raster Plot",
                       )

    return fig2, df


def electrode_map(spike_data):
    """

    :param spike_data: A SpikeData class instance
    :return: The electrode map plot, circle colors to change color later, channel map df for mapping neurons from raster plot
    """
    good_clusters = spike_data.cluster_channel_map()  # {cluster_id: channel_id}
    spike_times_dict = spike_data.cluster_spike_times(good_clusters)  # {cluster_id: spike_times}
    chn_map_df = spike_data.channel_map(good_clusters, spike_times_dict)
    channel_map = spike_data.channel_map_dict()
    chn_spike_times = dict(zip(list(good_clusters.values()), list(spike_times_dict.values())))
    spike_times = list(spike_times_dict.values())
    channels = list(good_clusters.values())
    # spike_times, channels, chn_spike_times, channel_map, chn_map_df
    colors = {'background': 'white',
              'borderline': 'black'}
    sttc = spike_time_tilings(spike_times, delt=20)
    paired_sttc = []
    sttc_thr = 0.35
    for i in range(len(spike_times) - 1):  # i, j are the indices to spike_times
        for j in range(i + 1, len(spike_times)):
            if sttc[i][j] >= sttc_thr:
                paired_sttc.append((channels[i], channels[j], sttc[i][j]))
    # print(len(paired_sttc), paired_sttc)

    paired_direction = []
    for p in paired_sttc:
        lat = latency(chn_spike_times[p[0]], chn_spike_times[p[1]], threshold=20)
        pos_count = len(list(filter(lambda x: (x >= 0), lat)))
        if abs(pos_count - (len(lat) - pos_count)) > 0.6 * len(lat):
            if np.mean(lat) > 0:
                paired_direction.append([p[0], p[1], p[2], np.mean(lat)])  # signal goes from chn_1 to chn_2
            else:
                paired_direction.append([p[1], p[0], p[2], abs(np.mean(lat))])

    start_x = [channel_map[p[0]][0] for p in paired_direction]
    start_y = [channel_map[p[0]][1] for p in paired_direction]
    end_x = [channel_map[p[1]][0] for p in paired_direction]
    end_y = [channel_map[p[1]][1] for p in paired_direction]
    sttc_xy = [p[2] for p in paired_direction]
    delay = [p[3] for p in paired_direction]

    # -------------------------- plot figure ----------------------#

    circle_colors = ['#000000'] * (chn_map_df['x_coor'].size)
    circle_colors[-1] = '#a3a7e4'

    fig = px.scatter(chn_map_df, x="x_coor", y="y_coor", hover_name="channel",
                     size="fire_rate", width=800, height=600, title="Electrode Map")
    fig.update_traces(
        marker=dict(
            color=circle_colors
        )
    )
    # plot arrows for the paired data
    for i in range(len(start_x)):
        if delay[i] > 1:
            color = 'red'
        else:
            color = 'purple'
        fig.add_annotation(ax=start_x[i], ay=start_y[i], axref='x', ayref='y',
                           x=end_x[i], y=end_y[i], xref='x', yref='y',
                           showarrow=True, arrowhead=1, arrowwidth=sttc_xy[i] * 5, arrowcolor=color,
                           opacity=0.5)
    fig.update_yaxes(autorange="reversed", showline=True, linewidth=1, linecolor=colors['borderline'], mirror=True)
    fig.update_xaxes(showline=True, linewidth=1, linecolor=colors['borderline'], mirror=True)
    fig.update_layout(plot_bgcolor=colors['background'],
                      paper_bgcolor=colors['background'])

    return fig, circle_colors, chn_map_df


# dash setting
app = Dash(__name__)
colors = {'background': 'white',
          'borderline': 'black'}

###### variables #######
sttc_window = 20
sttc_thr = 0.35
fr_coef = 10
# TODO: get the path from dropdown selection and callback functions
path = "s3://braingeneers/ephys/2022-05-18-e-connectoid/original/data/" \
       "Trace_20220518_12_53_35_chip11350.raw.h5"
########## end ##########

ephys_data = analysis.read_phy_files(path)
print("Recording length: {} minutes".format(ephys_data.length / 1000 / 60))
print("Number of neurons: ", len(ephys_data.train))  # TODO: Show these as metadata on the dashboard

spike_times = ephys_data.train
# neuron_data = {new_cluster_id:[channel_id, (chan_pos_x, chan_pos_y), [chan_template], {channel_id:cluster_templates}]}
neuron_data = ephys_data.neuron_data
chn_pos = np.asarray(list(neuron_data.values()))[:, 1]
sttc = ephys_data.spike_time_tilings(delt=sttc_window)

##----- Create channel map -----##
cluster_num = np.arange(1, len(spike_times) + 1)
fire_rate = ephys_data.rates(unit='Hz') * fr_coef
chn_map = {"clusters": cluster_num,
           "x_coor": list(chn_pos[:, 0]),
           "y_coor": list(chn_pos[:, 1]),
           "fire_rate": fire_rate}
chn_map_df = pd.DataFrame(data=chn_map)

##----- Create delay pairs -----##
paired_direction = []
for i in range(len(spike_times) - 1):  # i, j are the indices to spike_times
    for j in range(i + 1, len(spike_times)):
        if sttc[i][j] >= sttc_thr:
            lat = latency(spike_times[i], spike_times[j], threshold=sttc_window)
            pos_count = len(list(filter(lambda x: (x >= 0), lat)))
            if abs(pos_count - (len(lat) - pos_count)) > 0.6 * len(lat):
                if np.mean(lat) > 0:
                    paired_direction.append([i, j, sttc[i][j], np.mean(lat)])  # signal goes from chn_1 to chn_2
                else:
                    paired_direction.append([j, i, sttc[i][j], abs(np.mean(lat))])
print(len(paired_direction))

start_x = [chn_pos[p[0]][0] for p in paired_direction]
start_y = [chn_pos[p[0]][1] for p in paired_direction]
end_x = [chn_pos[p[1]][0] for p in paired_direction]
end_y = [chn_pos[p[1]][1] for p in paired_direction]
sttc_xy = [p[2] for p in paired_direction]
delay = [p[3] for p in paired_direction]

# -------------------------- plot figures ----------------------#
fig = px.scatter(chn_map_df, x="x_coor", y="y_coor", hover_name="cluster",
                 size="fire_rate", width=1100, height=600)  # electrode grid = 220 x 120 (W x H)

# plot arrows for the paired data
for i in range(len(start_x)):
    if delay[i] > 1:
        color = 'red'
    else:
        color = 'purple'
    fig.add_annotation(ax=start_x[i], ay=start_y[i], axref='x', ayref='y',
                       x=end_x[i], y=end_y[i], xref='x', yref='y',
                       showarrow=True, arrowhead=1, arrowwidth=sttc_xy[i] * 5, arrowcolor=color,
                       opacity=0.5)
fig.update_yaxes(autorange="reversed", showline=True, linewidth=1, linecolor=colors['borderline'], mirror=True)
fig.update_xaxes(showline=True, linewidth=1, linecolor=colors['borderline'], mirror=True)
fig.update_layout(plot_bgcolor=colors['background'],
                  paper_bgcolor=colors['background'])

# ------------------------- dash app ---------------------------#
# app.layout = html.Div(style={'backgroundColor': colors['background']},
app.layout = html.Div([
    html.H1("Spike sorted data visualization dashboard"),
    html.Br(),
    html.Div(children=[
        html.Div(children=[
            html.Label('Dataset (UUID)'),
            dcc.Dropdown(options=['id_1', 'id_2', 'id_3'], value='id_1', id="drop_down"),
            dcc.Dropdown(options=['id_1', 'id_2', 'id_3'], value='id_1', id="drop_down_subplot", disabled=True),
            html.Div(id='dd-output-container'),
            html.Br(),
            daq.BooleanSwitch(id='show_network',
                              on=False,
                              label="Show Network",
                              labelPosition="top"),
            dcc.Graph(id='electrode-map'),
        ], style={'padding': 10}),
        html.Div(children=[
            html.Div(children=[
                html.Div(children=[
                    html.P("Spike Template"),
                ], style={'background-color': '#e4e7ed',
                          'margin': '10px',
                          'padding': '15px',
                          'box-shadow': '2px',
                          'width': '200px',
                          'height': '50px',
                          'border-style': 'groove',
                          'text-align': 'center',
                          }),
                html.Div(children=[
                    html.P("ISI"),
                ], style={'background-color': '#e4e7ed',
                          'margin': '10px',
                          'padding': '15px',
                          'box-shadow': '2px',
                          'width': '200px',
                          'height': '50px',
                          'border-style': 'groove',
                          'text-align': 'center',
                          }),

                html.Div(children=[
                    html.P(children="Firing Rate", id="fire_rate"),
                ], style={'background-color': '#e4e7ed',
                          'margin': '10px',
                          'padding': '15px',
                          'box-shadow': '2px',
                          'width': '200px',
                          'height': '50px',
                          'border-style': 'groove',
                          'text-align': 'center', }),

            ], style={'padding': 10, 'display': 'flex', 'flex-direction': 'row'}),

            html.Br(),
            html.Div([
                html.P("Raw trace with highlighted spikes"),
            ], style={
                'background-color': '#e4e7ed',
                'margin': '10px',
                'padding': '15px',
                'box-shadow': '2px',
                'width': '800px',
                'height': '50px',
                'border-style': 'solid',
                'text-align': 'center',
            }),

            html.Br(),
            dcc.Graph(id='raster_plot'),

        ], style={'flex-direction': 'column', 'display': 'flex'}),

    ], style={'display': 'flex', 'flex-direction': 'row'}),

], )


@app.callback(
    Output('drop_down', 'options'),
    Input('drop_down', 'search_value')
)
def drop_down(search_value):
    print(search_value)
    print(type(search_value))
    uuids = wr.list_directories('s3://braingeneers/ephys/')
    return uuids

# These lines are needed when using local data
fs = 20  # ms as the unit
folder_dir = "data/example_phy_data_0518/"
Connectoid_0518 = SpikeData(fs, folder_dir)  # TODO: should change to braingeneers class
fig, circle_colors, chn_map_df = electrode_map(Connectoid_0518)
fig2, df = raster_plot(Connectoid_0518)

# print(chn_map_df)
# print(list(chn_map_df['fire_rate']))

@app.callback(
    Output('electrode-map', 'figure'),
    Output('raster_plot', 'figure'),
    Output('drop_down_subplot', 'disabled'),
    Output('fire_rate', 'children'),
    Output('drop_down_subplot', 'options'),
    Input('drop_down', 'value'),
    Input('electrode-map', 'clickData'),
    Input('raster_plot', 'clickData'),

)
def plot_elec(value, electrode_click, raster_click):
    # print("plot function")
    # print(value)
    # print(type(value))
    original_data = []

    button_id = ctx.triggered_id if not None else 'No clicks yet'
    print(button_id)
    print("click")
    print(electrode_click)
    print("raster click")
    print(raster_click)
    firing_rate = ''
    subfolder_dropdown_disable = True
    if value.startswith('s3'):
        print("+++++++++++++++++++")
        # print(br.datasets_electrophysiology.load_metadata('2022-05-18'))
        # print(br.data.datasets.load_batch(value))
        # print(wr.list_directories(value))
        original_data = wr.list_objects(value + 'original/data/')
        # print(value + 'original/data/')
        print(original_data)

        # TODO: build the figure base on the input data from this callback
        if original_data:
            subfolder_dropdown_disable = False
            pass
        else:
            subfolder_dropdown_disable = True
            # TODO: build the figures when there is no original/data/ path (can we work with such data?)
            pass

    if raster_click and button_id == 'raster_plot':
        raster_number = raster_click['points'][0]['y']
        df.loc[df["Cluster_number"] == raster_number, ["Pos"]] = 'black'
        fig2.update_traces(
            marker=dict(
                color=df['Pos'],
            )
        )
        cluster_number = list(chn_map_df['channel']).index(int(raster_number))
        firing_rate = chn_map_df.loc[chn_map_df['channel'] == int(raster_number)]['fire_rate'].values[0]
        # print("here")
        # print(firing_rate)
        # print(int(raster_number))
        circle_colors[cluster_number] = '#00FF00'
        fig.update_traces(
            marker=dict(
                color=circle_colors
            )
        )
    if electrode_click and (button_id == 'electrode-map'):
        cluster_number = int(electrode_click['points'][0]['pointNumber'])
        circle_colors[cluster_number] = '#a3a7e4'
        fig.update_traces(
            marker=dict(
                color=circle_colors
            )
        )

        raster_number = electrode_click['points'][0]['hovertext']
        firing_rate = chn_map_df.loc[chn_map_df['channel'] == int(raster_number)]['fire_rate'].values[0]
        df.loc[df["Cluster_number"] == str(raster_number), ["Pos"]] = 'red'

        fig2.update_traces(
            marker=dict(
                color=df['Pos'],
            )
        )
    # print(firing_rate)
    # print(type(firing_rate))
    last_electrode_click = electrode_click
    last_raster_click = raster_click
    return fig, fig2, subfolder_dropdown_disable, 'Fire rate ' + str(firing_rate), original_data


if __name__ == '__main__':
    app.run_server(debug=True, port=8050)  # include hot-reloading by default

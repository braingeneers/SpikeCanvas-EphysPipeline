# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
from dash import Dash, html, dcc
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import dash_daq as daq
from braingeneers import analysis
import numpy as np
from localPlot import *
from extra import *
import pandas as pd

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
print("Recording length: {} minutes".format(ephys_data.length/1000/60))
print("Number of neurons: ", len(ephys_data.train))    # TODO: Show these as metadata on the dashboard

spike_times = ephys_data.train
# neuron_data = {new_cluster_id:[channel_id, (chan_pos_x, chan_pos_y), [chan_template], {channel_id:cluster_templates}]}
neuron_data = ephys_data.neuron_data
chn_pos = np.asarray(list(neuron_data.values()))[:, 1]
sttc = ephys_data.spike_time_tilings(delt=sttc_window)

##----- Create channel map -----##
cluster_num = np.arange(1, len(spike_times)+1)
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
    html.Div([
        html.H1('Ephys Analysis Visualizer'), ]),
    html.Div([
        daq.BooleanSwitch(id='show_network',
                          on=False,
                          label="Show Network",
                          labelPosition="top"),
        dcc.Graph(id='electrode-map', figure=fig), ])
])

# @app.callback(
#     Output('boolean-switch-output-1', 'children'),
#     Input('my-boolean-switch', 'on')
# )
# def update_output(on):
#     return 'The switch is {}.'.format(on)

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)  # include hot-reloading by default
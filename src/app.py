# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
from dash import Dash, html, dcc, Input, Output, ctx
import dash_daq as daq
import braingeneers.utils.s3wrangler as wr
from maxwellEphys import *

# dash setting
app = Dash(__name__)
colors = {'background': 'white',
          'borderline': 'black'}

###### variables #######
sttc_delta = 20
sttc_thr = 0.35
fr_coef = 10
# fs = 20000

# TODO: get the path from callback functions of dropdowns
path = "s3://braingeneers/ephys/2022-05-18-e-connectoid/original/data/" \
       "Trace_20220518_12_53_35_chip11350.raw.h5"
phy_path = "s3://braingeneers/ephys/2022-05-18-e-connectoid/derived/kilosort2/" \
           "Trace_20220518_12_53_35_chip11350_curated.zip"
########## end ##########

ephys_dash = MaxWellEphys(phy_path, fr_coef, sttc_delta, sttc_thr)
fig_map, circle_colors = ephys_dash.plot_map()
fig_raster = ephys_dash.plot_raster()




# ##----- Create delay pairs -----##
# paired_direction = []
# for i in range(len(spike_times) - 1):  # i, j are the indices to spike_times
#     for j in range(i + 1, len(spike_times)):
#         if sttc[i][j] >= sttc_thr:
#             lat = latency(spike_times[i], spike_times[j], threshold=sttc_window)
#             pos_count = len(list(filter(lambda x: (x >= 0), lat)))
#             if abs(pos_count - (len(lat) - pos_count)) > 0.6 * len(lat):
#                 if np.mean(lat) > 0:
#                     paired_direction.append([i, j, sttc[i][j], np.mean(lat)])  # signal goes from chn_1 to chn_2
#                 else:
#                     paired_direction.append([j, i, sttc[i][j], abs(np.mean(lat))])
# print(len(paired_direction))
#
# start_x = [chn_pos[p[0]][0] for p in paired_direction]
# start_y = [chn_pos[p[0]][1] for p in paired_direction]
# end_x = [chn_pos[p[1]][0] for p in paired_direction]
# end_y = [chn_pos[p[1]][1] for p in paired_direction]
# sttc_xy = [p[2] for p in paired_direction]
# delay = [p[3] for p in paired_direction]

# # -------------------------- plot figures ----------------------#
# fig = px.scatter(chn_map_df, x="x_coor", y="y_coor", hover_name="cluster",
#                  size="fire_rate", width=1100, height=600)  # electrode grid = 220 x 120 (W x H)
#
# # plot arrows for the paired data
# for i in range(len(start_x)):
#     if delay[i] > 1:
#         color = 'red'
#     else:
#         color = 'purple'
#     fig.add_annotation(ax=start_x[i], ay=start_y[i], axref='x', ayref='y',
#                        x=end_x[i], y=end_y[i], xref='x', yref='y',
#                        showarrow=True, arrowhead=1, arrowwidth=sttc_xy[i] * 5, arrowcolor=color,
#                        opacity=0.5)
# fig.update_yaxes(autorange="reversed", showline=True, linewidth=1, linecolor=colors['borderline'], mirror=True)
# fig.update_xaxes(showline=True, linewidth=1, linecolor=colors['borderline'], mirror=True)
# fig.update_layout(plot_bgcolor=colors['background'],
#                   paper_bgcolor=colors['background'])

# ------------------------- dash app ---------------------------#
# app.layout = html.Div(style={'backgroundColor': colors['background']},
app.layout = html.Div([
    html.H1("MaxWell Electrophysiology dashboard"),
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

# # These lines are needed when using local data
# fs = 20  # ms as the unit
# folder_dir = "data/example_phy_data_0518/"
# Connectoid_0518 = SpikeData(fs, folder_dir)  # TODO: should change to braingeneers class
# fig, circle_colors, chn_map_df = electrode_map(Connectoid_0518)
# fig2, df = raster_plot(Connectoid_0518)

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
        ephys_dash.raster_df.loc[ephys_dash.raster_df["cluster_number"] == raster_number,
                                 ["pos"]] = 'black'
        fig_raster.update_traces(
            marker=dict(
                color=ephys_dash.raster_df['Pos'],
            )
        )
        cluster_number = list(ephys_dash.chn_map_df['channel']).index(int(raster_number))
        firing_rate = ephys_dash.chn_map_df.loc[ephys_dash.chn_map_df['channel'] ==
                                                int(raster_number)]['fire_rate'].values[0]
        # print("here")
        # print(firing_rate)
        # print(int(raster_number))
        circle_colors[cluster_number] = '#00FF00'
        fig_map.update_traces(
            marker=dict(
                color=circle_colors
            )
        )
    if electrode_click and (button_id == 'electrode-map'):
        cluster_number = int(electrode_click['points'][0]['pointNumber'])
        circle_colors[cluster_number] = '#a3a7e4'
        fig_raster.update_traces(
            marker=dict(
                color=circle_colors
            )
        )

        raster_number = electrode_click['points'][0]['hovertext']
        firing_rate = ephys_dash.chn_map_df.loc[ephys_dash.chn_map_df['channel'] ==
                                                int(raster_number)]['fire_rate'].values[0]
        ephys_dash.raster_df.loc[ephys_dash.raster_df["cluster_number"] ==
                                 str(raster_number), ["pos"]] = 'red'

        fig_raster.update_traces(
            marker=dict(
                color=ephys_dash.raster_df['pos'],
            )
        )
    # print(firing_rate)
    # print(type(firing_rate))
    last_electrode_click = electrode_click
    last_raster_click = raster_click
    return fig_map, fig_raster, subfolder_dropdown_disable, 'Fire rate ' + str(firing_rate), original_data


if __name__ == '__main__':
    app.run_server(debug=True, port=8050)  # include hot-reloading by default
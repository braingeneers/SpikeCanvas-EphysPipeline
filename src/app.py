# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import dash
from dash import Dash, html, dcc, Input, Output, ctx
import plotly
import dash_daq as daq
import dash_bootstrap_components as dbc
import braingeneers.utils.s3wrangler as wr
from maxwellEphys import *
from k8s_kilosort2 import Kube
import time
import pickle

# dash setting
# app = Dash(__name__)

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server


# def serve_layout():
    # global original_data
    # global subfolder_dropdown_disable
    # global ephys_dash
    # global fig_map, circle_colors
    # global fig_raster
    # global isi_plot
    # global template_plot
    # global already_clicked
    # global raster_lines

global ephys_dash
global fig_map, circle_colors
global fig_raster
global isi_plot
global template_plot
global already_clicked
global raster_lines

fig_map = plotly.subplots.make_subplots(rows=1, cols=1)
isi_plot = plotly.subplots.make_subplots(rows=1, cols=1)
template_plot = plotly.subplots.make_subplots(rows=1, cols=1)
fig_raster = plotly.subplots.make_subplots(rows=1, cols=1)


main_path = "s3://braingeneers/ephys/2022-05-18-e-connectoid/"
original_path = "s3://braingeneers/ephys/2022-05-18-e-connectoid/original/data/" \
                "Trace_20220518_12_53_35_chip11350.raw.h5"
phy_path = "s3://braingeneers/ephys/2022-05-18-e-connectoid/derived/kilosort2/" \
           "Trace_20220518_12_53_35_chip11350_curated.zip"
initial_dropdown_main = wr.list_objects(main_path)
initial_dropdown_values = wr.list_objects(main_path + 'original/data/')
initial_dropdown_derived = wr.list_objects(main_path + 'derived/kilosort2/')

    # with open('./initial_dictionary', 'rb') as f:
    #     (original_data,
    #      subfolder_dropdown_disable,
    #      ephys_dash,
    #      fig_map, circle_colors,
    #      fig_raster,
    #      isi_plot,
    #      template_plot,
    #      already_clicked,
    #      raster_lines) = pickle.load(f)

# all figures
electrode = dbc.Card(dcc.Graph(id='electrode_map',
                               figure=fig_map,
                               ))
template = dbc.Card(dcc.Graph(id='template_plot',
                              figure=template_plot,
                              ))
isi = dbc.Card(dcc.Graph(id='isi_plot',
                         figure=isi_plot,
                         ))
raster = dbc.Card(dcc.Graph(id='raster_plot',
                            figure=fig_raster,
                            ))

# electrode map with small figures
electrode_layout = dbc.Row([
            dbc.Col(electrode),
            dbc.Col([
                dbc.Row([
                    dbc.Col(template),
                    dbc.Col(isi)]),
                # dbc.Row([
                #     dbc.Col(template),
                #     dbc.Col(isi)])
                ])
           ])



app.layout = dbc.Container([
    html.H1("MaxWell Electrophysiology Dashboard"),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Hr(),
    # Dropdowns
    html.H6('Dataset (UUID)'),
    dbc.Row(dbc.Col(
        dcc.Dropdown(options=initial_dropdown_main, value=main_path, id="drop_down", disabled=False),
    )),
    dbc.Row(dbc.Col(
        dcc.Dropdown(options=initial_dropdown_values, value=original_path, id="drop_down_subplot", disabled=False),
    )),
    dbc.Row(dbc.Col(
        dcc.Dropdown(options=initial_dropdown_derived, value=phy_path, id="drop_down_curated", disabled=False),
    )),
    html.Br(),
    # Spike sorting button
    html.Div(
             children=[
                dbc.Row([
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                    html.P("This dataset is raw. Run spike sorting?"),
                                    dbc.Button("START", id="spike_sorting_btn", outline=True, color="success", className="me-1"),
                                    html.Span(id="container-button", style={"verticalAlign": "middle"})
                                ])
                            ), width=4
                        )
                    ]),
                ], style={'display': 'none'}, id="show_button"),
    html.Br(),
    # figure layout (using dbc.card)
    dbc.Row(dbc.Card(electrode_layout)),
    dbc.Row(raster)

])



###### variables #######
sttc_delta = 20
sttc_thr = 0.35
fr_coef = 10

# with open('./initial_dictionary', 'rb') as f:
#     (original_data,
#      subfolder_dropdown_disable,
#      ephys_dash,
#      fig_map, circle_colors,
#      fig_raster,
#      isi_plot,
#      template_plot,
#      already_clicked,
#      raster_lines) = pickle.load(f)

# print(ephys_dash.raster_df)
########## end ##########


# ------------------------- dash app ---------------------------#

@app.callback(
    Output('drop_down', 'options'),
    Input('drop_down', 'search_value')
)
def drop_down(search_value):
    print("search_value:", search_value)
    # print(type(search_value))
    uuids = wr.list_directories('s3://braingeneers/ephys/')
    return uuids


@app.callback(
    Output('drop_down_subplot', 'disabled'),
    Output('drop_down_subplot', 'options'),
    Output('drop_down_curated', 'options'),
    Output('show_button', 'style'),
    Input('drop_down', 'value'),
    Input('drop_down_subplot', 'value'),
    Input('drop_down_curated', 'value'),
)
def get_data_path(value, sub_plot_value, curated_value):
    button_id = ctx.triggered_id if not None else 'No clicks yet'
    if value.startswith('s3'):
        if button_id == 'drop_down':
            original_data = wr.list_objects(value + 'original/data/')
            print("Original_data: ", original_data)
            if original_data:
                subfolder_dropdown_disable = False
            else:
                subfolder_dropdown_disable = True
            return subfolder_dropdown_disable, original_data, dash.no_update, {'display': 'none'}

    if button_id == 'drop_down_subplot':
        print("sub_plot_value: ", sub_plot_value)
        splitted = sub_plot_value.split("original/data/")
        phy_type = ""
        if splitted[1][-7:] == ".raw.h5":
            phy_type = splitted[0] + "derived/kilosort2/" + splitted[1][:-7]
        elif splitted[1][-3:] == ".h5":
            phy_type = splitted[0] + "derived/kilosort2/" + splitted[1][:-3]

        print("phy_type: ", phy_type)
        phy_plot_value = [s for s in wr.list_objects(value + "derived/kilosort2/") if phy_type in s]
        print(phy_plot_value)
        if len(phy_plot_value) == 0:
            return dash.no_update, dash.no_update, phy_plot_value, {'display': 'block'}
        else:
            return dash.no_update, dash.no_update, phy_plot_value, {'display': 'none'}

    if button_id == 'drop_down_curated':
        print("sub_plot_curated:", curated_value)
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    return sub_plot_value


@app.callback(
    Output('container-button', 'children'),
    # Output('spike_sorting_btn', 'disabled'),
    Input('spike_sorting_btn', 'n_clicks'),
    Input('drop_down_subplot', 'value'),
)
def spike_sorting_button(n_clicks, sub_plot_value):
    prefix = "dash-ss-"
    file_name = sub_plot_value.split('original/data/')[1]
    if ".raw.h5" in file_name:
        file_name = list(file_name.split(".raw.h5")[0])
    elif ".h5" in file_name:
        file_name = list(file_name.split(".h5")[0])

    for i in range(len(file_name)):
        if file_name[i] == "_" or file_name[i] == ".":
            file_name[i] = "-"
        elif file_name[i].isupper():
            file_name[i] = file_name[i].lower()
    if len(file_name) >= (63 - len(prefix)):
        file_name = file_name[-(63 - len(prefix))+1:]
        if file_name[0] == '-':
            file_name[0] = "x"
    file_name = "".join(file_name)
    job_name = prefix + file_name
    if "spike_sorting_btn" == ctx.triggered_id:
        sort_current = Kube(job_name, sub_plot_value)
        job_response = sort_current.create_job()
        print("Button ", n_clicks)
        msg = "Spike sorting started!"  # TODO: add pods name and status
        # disable the button
        return html.Div(msg)


@app.callback(
    Output('electrode_map', 'figure'),
    Output('raster_plot', 'figure'),
    Output('isi_plot', 'figure'),
    Output('template_plot', 'figure'),
    # Output('drop_down_subplot', 'disabled'),
    # # Output('fire_rate', 'children'),
    # Output('drop_down_subplot', 'options'),
    # Output('drop_down_curated', 'options'),
    # Output('container-button', 'children'),
    # Output("loading1", "children"),
    # Input('drop_down', 'value'),
    Input('electrode_map', 'clickData'),
    Input('raster_plot', 'clickData'),
    # Input('drop_down_subplot', 'value'),
    Input('drop_down_curated', 'value'),
)
def plot_elec(electrode_click, raster_click, sub_plot_curated):
    # print("plot function")
    # print(value)
    # print(type(value))
    # global original_data
    # global sort_data
    # global subfolder_dropdown_disable
    global ephys_dash
    global fig_map, circle_colors
    global fig_raster
    global isi_plot
    global template_plot
    global already_clicked
    global raster_lines
    # first_time = time.time()
    button_id = ctx.triggered_id if not None else 'No clicks yet'
    print("plot_elec(), sub_plot_curated:", sub_plot_curated)
    already_clicked = set()

    if button_id == 'drop_down_curated':
        ephys_dash = MaxWellEphys(sub_plot_curated, fr_coef, sttc_delta, sttc_thr)
        ##### tempory figure style and layout test.
        # temp_local_path = '/home/kang/disk/Connectoid/chip11350/Trace_20220503_12_25_42v_chip11350_curated.zip'
        # ephys_dash = MaxWellEphys(temp_local_path, fr_coef, sttc_delta, sttc_thr)
        #####
        fig_map, circle_colors = ephys_dash.plot_map()
        fig_raster = ephys_dash.plot_raster()
        print("Figures are ready!")
        return fig_map, fig_raster, isi_plot, template_plot

    if raster_click and button_id == 'raster_plot':
        raster_number = raster_click['points'][0]['y']
        cluster_number = list(ephys_dash.chn_map_df['cluster_number']).index(int(raster_number))
        if cluster_number in already_clicked:
            circle_colors[cluster_number] = '#000000'
            fig_map.update_traces(
                marker=dict(
                    color=circle_colors
                )
            )
            temp_shape = dict(type='line',
                              x0=0,
                              y0=int(raster_number),
                              x1=max(ephys_dash.spike_times[int(cluster_number)]),
                              y1=int(raster_number),
                              xref='x',
                              yref='y')
            # raster_lines.append(temp_shape)
            fig_raster.update_shapes(patch=dict(line=dict(color='rgba(255, 255, 255, 0)'), ), selector=temp_shape)
            already_clicked.remove(cluster_number)


        else:
            temp_shape = dict(type='line',
                              x0=0,
                              y0=int(raster_number),
                              x1=max(ephys_dash.spike_times[int(cluster_number)]),
                              y1=int(raster_number),
                              line=dict(color='rgba(0, 255, 0, 0.4)'
                                        , width=6),
                              xref='x',
                              yref='y',
                              )

            fig_raster.add_shape(temp_shape, editable=True)
            circle_colors[cluster_number] = '#00FF00'
            # print(circle_colors)
            fig_map.update_traces(
                marker=dict(
                    color=circle_colors
                )
            )
            isi_plot = ephys_dash.plot_isi(int(cluster_number))
            template_plot = ephys_dash.plot_template(int(cluster_number))
            already_clicked.add(cluster_number)
            return fig_map, fig_raster, isi_plot, template_plot
    # second_time = time.time()
    # print('second', second_time)
    # print(second_time - first_time)
    if electrode_click and (button_id == 'electrode_map'):
        cluster_number = int(electrode_click['points'][0]['pointNumber'])
        raster_number = int(electrode_click['points'][0]['hovertext'])
        if cluster_number in already_clicked:
            circle_colors[cluster_number] = '#000000'
            fig_map.update_traces(
                marker=dict(
                    color=circle_colors
                )
            )
            temp_shape = dict(type='line',
                              x0=0,
                              y0=int(raster_number),
                              x1=max(ephys_dash.spike_times[int(cluster_number)]),
                              y1=int(raster_number),
                              xref='x',
                              yref='y'
                              )
            fig_raster.update_shapes(patch=dict(line=dict(color='rgba(255, 255, 255, 0)'), ), selector=temp_shape)
            already_clicked.remove(cluster_number)
        else:
            circle_colors[cluster_number] = '#FF0000'
            fig_map.update_traces(
                marker=dict(
                    color=circle_colors
                )
            )

            fig_raster.add_shape(type='line',
                                 x0=0,
                                 y0=int(raster_number),
                                 x1=max(ephys_dash.spike_times[int(cluster_number)]),
                                 y1=int(raster_number),
                                 line=dict(color='rgba(222, 13, 13, 0.4)'
                                           , width=6),
                                 xref='x',
                                 yref='y'
                                 )
            isi_plot = ephys_dash.plot_isi(int(cluster_number))
            template_plot = ephys_dash.plot_template(int(cluster_number))
            already_clicked.add(cluster_number)
            return fig_map, fig_raster, isi_plot, template_plot
    # return fig_map, fig_raster, isi_plot, template_plot


if __name__ == '__main__':
    app.run_server(debug=True, port=8050, host='0.0.0.0')  # include hot-reloading by default

import dash
from dash import Dash, html, dcc, Input, Output, ctx, State
from dash import callback
import plotly
import dash_daq as daq
import dash_bootstrap_components as dbc
import braingeneers.utils.s3wrangler as wr
from maxwellEphys import *
from make_plots import PlotEphys
import time
import sys
import os
import posixpath
import numpy as np

sys.path.append('..')
import utils
from values import *

# TODO: a list of units using checklist for multiple single units selection
# TODO: burst detection, burst detection, burst detection
# TODO: Show curated results as a default setting --Done
# TODO: Convert old curation files to new format(to speed up loading)
# TODO: Add full electrode footprint
# TODO: keep the sorting function and allow checking status?
# TODO: create a second page for loading multiple recordings


# dash setting
dash.register_page(__name__)

fig_map = plotly.subplots.make_subplots(rows=1, cols=1)
fig_raster = plotly.subplots.make_subplots(rows=1, cols=1)
isi_plot = plotly.subplots.make_subplots(rows=1, cols=1)
template_plot = plotly.subplots.make_subplots(rows=1, cols=1)
fig_sttc = plotly.subplots.make_subplots(rows=1, cols=1)
fig_fr_dist = plotly.subplots.make_subplots(rows=1, cols=1)
# ccg, bursts, connectivity

###### variables #######
sttc_delta = 0.02  # STTC delta in seconds (20ms)
sttc_thr = 0.35    # STTC threshold
fr_coef = 10       # Firing rate coefficient
########## end ##########

####----------------------- make page -----------------------####
# all figures
electrode = dbc.Card(
    dcc.Graph(id='electrode_map',
              figure=fig_map, ))
raster = dbc.Card(
    dcc.Graph(id='raster_plot',
              figure=fig_raster, ))
template = dbc.Card(
    dcc.Graph(id='template_plot',
              figure=template_plot, ))
sttc_heatmap = dbc.Card(
    dcc.Graph(id='sttc_heatmap',
              figure=fig_sttc, ))
fr_dist = dbc.Card(
    dcc.Graph(id='firing_rate_distribution',
              figure=fig_fr_dist, ))
isi = dbc.Card(
    dcc.Graph(id='isi_plot',
              figure=isi_plot, ))

overview_figures_layout = dbc.Row(dbc.Card(
    dbc.Row([
        dbc.Col(electrode),
        dbc.Col([
            dbc.Row([
                dbc.Col(fr_dist),
                dbc.Col(sttc_heatmap)]),
        ]),
        dbc.Row(raster)
    ])
))

layout = dbc.Container([
    html.H2("SpikeCanvas Analytics"),
    html.P("Interactive visualization of processed neural data", 
           style={'color': '#7f8c8d', 'font-style': 'italic'}),
    html.Hr(),
    # Dropdowns
    dbc.Row([
        dbc.Col([
            html.Label("Dataset (UUID) - Filter by Keyword:", style={'font-weight': 'bold'}),
            dcc.Textarea(id='textarea_filter_uuid',
                         placeholder="Enter keyword to filter UUIDs",
                         value='',
                         style={'width': '100%', 'height': 40, 'margin-bottom': '10px'}),
            html.Label("Select Dataset UUID:", style={'font-weight': 'bold'}),
            dcc.Dropdown(id="dropdown_uuid",
                         options=[],
                         value="",
                         placeholder="Choose a dataset UUID...",
                         disabled=False,
                         style={'margin-bottom': '10px'}),
            html.Label("Select Processed Data (Derived Folder):", style={'font-weight': 'bold'}),
            dcc.Dropdown(id="dropdown_data",
                         options=[],
                         value="",
                         placeholder="Choose processed data file...",
                         disabled=False),
        ], width=12)
    ]),

    html.Br(),
    
    # Loading indicator
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Progress(
                    id="loading-progress",
                    value=0,
                    striped=True,
                    animated=True,
                    color="primary",
                    style={'height': '25px', 'margin-bottom': '10px'}
                ),
                html.Div(
                    id="loading-status",
                    children="Ready to load data...",
                    style={
                        'text-align': 'center',
                        'font-weight': 'bold',
                        'color': '#2c3e50',
                        'margin-bottom': '10px'
                    }
                ),
                html.Div(
                    id="loading-details",
                    children="Select a processed data file to begin analysis",
                    style={
                        'text-align': 'center',
                        'font-size': '12px',
                        'color': '#7f8c8d',
                        'margin-bottom': '20px'
                    }
                )
            ], id="loading-container", style={'display': 'none'})
        ], width=12)
    ]),
    
    # Spike sorting button
    # html.Div(
    #     children=[
    #         dbc.Row([
    #             dbc.Col(
    #                 dbc.Card(
    #                     dbc.CardBody([
    #                         html.P("This dataset is raw. Run spike sorting?"),
    #                         dbc.Button("START", id="spike_sorting_btn", outline=True, color="success",
    #                                    className="me-1"),
    #                         html.Span(id="container-button", style={"verticalAlign": "middle"})
    #                     ])
    #                 ), width=4
    #             )
    #         ]),
    #     ], style={'display': 'none'}, id="show_button"),
    # html.Br(),
    # figure layout (using dbc.card)
    dbc.Row(overview_figures_layout)

])


#######################--------------- callback functions ---------------#######################
@callback(
    Output('dropdown_uuid', 'options'),
    Input('textarea_filter_uuid', 'value'),
)
def drop_down(value=None):
    return utils.filter_dropdown(search_value=value)


@callback(
    Output("dropdown_data", "options"),
    Input("dropdown_uuid", "value"),
    prevent_initial_call=True
)
def dropdown_data(uuid):
    if uuid is None or uuid == "":
        return []
    
    processed_files = []
    
    # Check both autocuration and kilosort2 subfolders
    subfolders = ['autocuration', 'kilosort2']
    
    for subfolder in subfolders:
        try:
            # Use forward slashes for S3 path compatibility
            subfolder_path = f"{uuid.rstrip('/')}/derived/{subfolder}"
            print(f"Checking path: {subfolder_path}")
            
            # List all files in the current subfolder
            objects = wr.list_objects(subfolder_path)
            
            # Filter to show only processed files (curated results and phy files)
            for obj in objects:
                if obj.endswith(('_acqm.zip', '_qm_rd.zip', '_qm.zip', '_phy.zip')):
                    # Keep the full derived path for display
                    display_name = obj.replace(f"{uuid.rstrip('/')}/", "")
                    processed_files.append({
                        'label': f"{subfolder}/{display_name.split('/')[-1]}", 
                        'value': display_name
                    })
                    
        except Exception as e:
            print(f"Error listing objects in {subfolder_path}: {e}")
            continue
    
    # Sort files by subfolder and filename for better organization
    processed_files.sort(key=lambda x: (x['label'].split('/')[0], x['label'].split('/')[1]))
    
    return processed_files


# Show loading bar immediately when file is selected
@callback(
    [Output("loading-container", "style"),
     Output("loading-progress", "value"),
     Output("loading-status", "children"),
     Output("loading-details", "children")],
    Input("dropdown_data", "value"),
    prevent_initial_call=True
)
def show_loading_container(data_filename):
    if data_filename is None or data_filename == "":
        return {'display': 'none'}, 0, "Ready to load data...", "Select a processed data file to begin analysis"
    else:
        filename_display = data_filename.split('/')[-1] if data_filename else "file"
        return ({'display': 'block'}, 10, "Loading data...", 
                f"Loading: {filename_display}")

# Hide loading bar when processing is complete
@callback(
    Output("loading-container", "style", allow_duplicate=True),
    [Input("loading-progress", "value")],
    prevent_initial_call=True
)
def hide_loading_when_complete(progress_value):
    if progress_value >= 100:
        return {'display': 'none'}
    else:
        return {'display': 'block'}

# add load figure button

# @callback(
#     Output('container-button', 'children'),
#     # Output('spike_sorting_btn', 'disabled'),
#     Input('spike_sorting_btn', 'n_clicks'),
#     Input('dropdown_data', 'value'),
# )
# def spike_sorting_button(n_clicks, sub_plot_value):
#     prefix = "dash-ss-"
#     file_name = sub_plot_value.split('original/data/')[1]
#     if ".raw.h5" in file_name:
#         file_name = list(file_name.split(".raw.h5")[0])
#     elif ".h5" in file_name:
#         file_name = list(file_name.split(".h5")[0])
#
#     for i in range(len(file_name)):
#         if file_name[i] == "_" or file_name[i] == ".":
#             file_name[i] = "-"
#         elif file_name[i].isupper():
#             file_name[i] = file_name[i].lower()
#     if len(file_name) >= (63 - len(prefix)):
#         file_name = file_name[-(63 - len(prefix)) + 1:]
#         if file_name[0] == '-':
#             file_name[0] = "x"
#     file_name = "".join(file_name)
#     job_name = prefix + file_name
#     if "spike_sorting_btn" == ctx.triggered_id:
#         sort_current = Kube(job_name, sub_plot_value)
#         job_response = sort_current.create_job()
#         print("Button ", n_clicks)
#         msg = "Spike sorting started!"
#         # disable the button
#         return html.Div(msg)

# show summary figures together with map and raster
# distribution of firing rate
# heatmap of sttc with 20ms window
# burst duration, IBI, burst peak firing rate
@callback(
    [Output('electrode_map', 'figure', allow_duplicate=True),
     Output('raster_plot', 'figure', allow_duplicate=True),
     Output('sttc_heatmap', 'figure'),
     Output('firing_rate_distribution', 'figure'),
     Output("loading-progress", "value", allow_duplicate=True),
     Output("loading-status", "children", allow_duplicate=True),
     Output("loading-details", "children", allow_duplicate=True)],
    [Input('dropdown_data', 'value')],
    [State('dropdown_uuid', 'value')],
    prevent_initial_call=True
)
def plot_initial_figures(data_filename, uuid):
    button_id = ctx.triggered_id if not None else 'No clicks yet'
    if button_id == 'dropdown_data':
        # Validate inputs
        if data_filename is None or data_filename == "" or uuid is None or uuid == "":
            print("No data file or UUID selected")
            return fig_map, fig_raster, fig_sttc, fig_fr_dist, 0, "Ready to load data...", "Select a processed data file to begin analysis"
        
        # Construct full S3 path - data_filename now contains the derived path
        s3_data_path = f"{uuid.rstrip('/')}/{data_filename}"

        try:
            print(f"Loading processed data from: {s3_data_path}")
            
            # Since we're already selecting from derived folder, we can use the path directly
            # No need to call parse_derived_path as the file is already a processed result
            if not wr.does_object_exist(s3_data_path):
                print(f"Selected file does not exist: {s3_data_path}")
                return (fig_map, fig_raster, fig_sttc, fig_fr_dist, 0, 
                       "File not found!", f"Could not locate: {data_filename.split('/')[-1]}")
            
            # # Create a mock original path for PlotEphys compatibility
            # # PlotEphys expects an original path and internally converts to derived
            # # Handle both autocuration and kilosort2 subfolders
            # original_filename = data_filename
            # if "derived/autocuration/" in original_filename:
            #     original_filename = original_filename.replace("derived/autocuration/", "original/data/")
            # elif "derived/kilosort2/" in original_filename:
            #     original_filename = original_filename.replace("derived/kilosort2/", "original/data/")
            
            # # Remove the processing suffixes and add back the .raw.h5 extension
            # for suffix in ["_acqm.zip", "_qm_rd.zip", "_qm.zip", "_phy.zip"]:
            #     if original_filename.endswith(suffix):
            #         original_filename = original_filename.replace(suffix, ".raw.h5")
            #         break
            
            # mock_original_path = f"{uuid.rstrip('/')}/{original_filename}"
            # print(f"Using mock original path for PlotEphys: {mock_original_path}")
            
            # Initialize PlotEphys (50% progress)
            print("Initializing data processing...")
            ephys_dash = PlotEphys(s3_data_path, fr_coef, sttc_delta, sttc_thr)
            
            # Generate electrode map (60% progress)
            print("Generating electrode map...")
            new_fig_map, circle_colors = ephys_dash.plot_map()
            
            # Generate raster plot (70% progress)
            print("Generating raster plot...")
            new_fig_raster = ephys_dash.plot_raster_fr()
            
            # Generate STTC heatmap (85% progress)
            print("Generating STTC heatmap...")
            new_fig_sttc = ephys_dash.plot_sttc_heatmap()
            
            # Generate firing rate distribution (95% progress)
            print("Generating firing rate distribution...")
            new_fig_fr_dist = ephys_dash.plot_fr_distribution()
            
            print("All figures generated successfully!")
            return (new_fig_map, new_fig_raster, new_fig_sttc, new_fig_fr_dist, 
                   100, "Figures loaded successfully!", 
                   "All visualizations are ready for analysis")
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            # Return empty figures on error
            return (fig_map, fig_raster, fig_sttc, fig_fr_dist, 
                   0, f"Error loading data: {str(e)}", 
                   "Please check the file format and try again")
    
    # Return current figures if not triggered by dropdown
    return (fig_map, fig_raster, fig_sttc, fig_fr_dist, 
           0, "Ready to load data...", 
           "Select a processed data file to begin analysis")

# @callback(
#     Output('electrode_map', 'figure', allow_duplicate=True),
#     Output('raster_plot', 'figure', allow_duplicate=True),
#     Output('isi_plot', 'figure'),
#     Output('template_plot', 'figure'),
#     State('electrode_map', 'clickData'),
#     State('raster_plot', 'clickData'),
#
#     prevent_initial_call=True
# )
# def plot_elec(electrode_click, raster_click):
#     global ephys_dash
#     global fig_map, circle_colors
#     global fig_raster
#     global isi_plot
#     global template_plot
#     global already_clicked
#     global raster_lines
#
#     button_id = ctx.triggered_id if not None else 'No clicks yet'
#
#     already_clicked = set()
#     if raster_click and button_id == 'raster_plot':
#         raster_number = raster_click['points'][0]['y']
#         cluster_number = list(np.arange(1, ephys_dash.ephys_data.N + 1, 1)).index(int(raster_number))
#         if cluster_number in already_clicked:
#             circle_colors[cluster_number] = '#000000'
#             fig_map.update_traces(
#                 marker=dict(
#                     color=circle_colors
#                 )
#             )
#             temp_shape = dict(type='line',
#                               x0=0,
#                               y0=int(raster_number),
#                               x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
#                               y1=int(raster_number),
#                               xref='x',
#                               yref='y')
#             # raster_lines.append(temp_shape)
#             fig_raster.update_shapes(patch=dict(line=dict(color='rgba(255, 255, 255, 0)'), ), selector=temp_shape)
#             already_clicked.remove(cluster_number)
#         else:
#             # temp_shape = dict(type='line',
#             #                   x0=0,
#             #                   y0=int(raster_number),
#             #                   x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
#             #                   y1=int(raster_number),
#             #                   line=dict(color='rgba(0, 255, 0, 0.4)'
#             #                             , width=6),
#             #                   xref='x',
#             #                   yref='y',
#             #                   )
#             #
#             # fig_raster.add_shape(temp_shape, editable=True)
#             # circle_colors[cluster_number] = '#00FF00'
#             # # print(circle_colors)
#             # fig_map.update_traces(
#             #     marker=dict(
#             #         color=circle_colors
#             #     )
#             # )
#             isi_plot = ephys_dash.plot_isi(int(cluster_number))
#             # template_plot = ephys_dash.plot_template(int(cluster_number))
#             template_plot = ephys_dash.plot_footprint(int(cluster_number))
#             already_clicked.add(cluster_number)
#             return fig_map, fig_raster, isi_plot, template_plot
#     # second_time = time.time()
#     # print('second', second_time)
#     # print(second_time - first_time)
#     if electrode_click and (button_id == 'electrode_map'):
#         cluster_number = int(electrode_click['points'][0]['pointNumber'])
#         raster_number = int(electrode_click['points'][0]['hovertext'])
#         print(f"cluster_number, {cluster_number}")
#         if cluster_number in already_clicked:
#             circle_colors[cluster_number] = '#000000'
#             fig_map.update_traces(
#                 marker=dict(
#                     color=circle_colors
#                 )
#             )
#             temp_shape = dict(type='line',
#                               x0=0,
#                               y0=int(raster_number),
#                               x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
#                               y1=int(raster_number),
#                               xref='x',
#                               yref='y'
#                               )
#             fig_raster.update_shapes(patch=dict(line=dict(color='rgba(255, 255, 255, 0)'), ), selector=temp_shape)
#             already_clicked.remove(cluster_number)
#         else:
#             print("update after click")
#             circle_colors[cluster_number] = '#FF0000'
#             fig_map.update_traces(
#                 marker=dict(
#                     color=circle_colors
#                 )
#             )
#
#             fig_raster.add_shape(type='line',
#                                  x0=0,
#                                  y0=int(raster_number),
#                                  x1=max(ephys_dash.spike_times[int(cluster_number)]) / 1000,
#                                  y1=int(raster_number),
#                                  line=dict(color='rgba(222, 13, 13, 0.4)'
#                                            , width=6),
#                                  xref='x',
#                                  yref='y'
#                                  )
#             print(f"showing isi...")
#             isi_plot = ephys_dash.plot_isi(int(cluster_number))
#             # template_plot = ephys_dash.plot_template(int(cluster_number))
#             template_plot = ephys_dash.plot_footprint(int(cluster_number))
#             already_clicked.add(cluster_number)
#             return fig_map, fig_raster, isi_plot, template_plot

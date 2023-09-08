import dash
from dash import html, dcc, callback, Input, Output, State, ctx
from dash import dash_table
import braingeneers.utils.s3wrangler as wr
import dash_bootstrap_components as dbc
import os
from datetime import datetime
import braingeneers.data.datasets_electrophysiology as de
import braingeneers.utils.smart_open_braingeneers as smart_open
import json
import sys
import time

# TODO: How to deal with inconsistent index when user remove rows?
# TODO: show total number of recordings in a uuid (read metadata) -- Done
# TODO: create datatable for chained jobs
# TODO: functions to check job status in real time (a new page?)
# TODO: Progress bar for process that needs time

dash.register_page(__name__)
sys.path.append('..')
import utils
from values import *

####----------------------- make page -----------------------####
# table layout
table_layout = dash_table.DataTable(
    id="job_table",
    columns=[
        {'id': h, 'name': h} for h in TABLE_HEADERS],
    data=[],
    # editable=True,  # This allows user to change value in each cell. So I disabled it.
    row_deletable=True
)

# page layout
print(f"Getting ready for page layout... ")
layout = dbc.Container([
    html.H2("Data Processing Job Center"),
    # html.Br(),
    html.Hr(),
    dbc.Row(html.Div([
        html.Div(["Dataset (UUID) ",
                  dcc.Dropdown(
                      options=[],
                      value="",
                      id="dropdown",
                      disabled=False),
                  ]),
        html.Div(["Filter UUID by Keyword: ",
                  dcc.Textarea(
                      id='textarea_filter_uuid',
                      placeholder="enter you keyword here",
                      value='',
                      style={'width': '30%', 'height': 30}, )
                  ]),
    ]),
    ),
    html.Br(),
    dbc.Row(html.Div([
        html.Div([dcc.Textarea(
            id='textarea_metadata',
            value='',
            contentEditable=False,
            readOnly=True,
            style={'width': '50%', 'height': 150}, )
        ]),
    ])
    ),
    html.Hr(),
    dbc.Row([dbc.Col([dcc.RadioItems(id="batch_job",
                                     options=[{"label": "Batch Process with Standard Pipeline",
                                               "value": "Batch"},
                                              {"label": "Clear All Selected", "value": "Reset"}],
                                     value="",)
                      ]),
             ]),
    html.Br(),
    dbc.Row([dbc.Col(dbc.Card(["Recording: ",
                               dcc.RadioItems(
                                   id='select_recording',
                                   options=[{'label': 'Select All', 'value': 'Batch'},
                                            {'label': 'Reset', 'value': 'Reset'}],
                                   value="",
                                   labelStyle={'display': 'inline'},
                               ),
                               html.P(""),
                               dcc.Checklist(
                                   id="checklist_recs",
                                   options=[],
                                   value=[],
                               )
                               ], style={"width": "18rem"}), width="auto"),
             html.Br(),
             dbc.Col(dbc.Card(["Select job: ",
                               dcc.Checklist(
                                   id='select_jobs',
                                   options=[{'label': 'Standard Pipeline (Spike Sorting -> Curation -> Figures)',
                                             'value': 0},
                                            {'label': 'Spike Sorting (Kilosort2)', 'value': 1},
                                            {'label': 'Curation (Quality Metrics)', 'value': 2},
                                            {'label': 'Figures (Raster/Electrode Map)', 'value': 3},
                                            {'label': 'Another Analysis Algorithms (To be added...)', 'value': 4}],
                                   value=[],
                                   labelStyle={'display': 'block'},
                               ),
                               html.Br(style={"line-height": "1"}),
                               dbc.Button("Add to Job Table",
                                          id='add_to_table_button',
                                          disabled=False,
                                          outline=True,),
                               html.Div(id="job_message_output")
                               ],), width="auto"),
             ]),
    html.Br(),
    html.Hr(),
    html.Br(),
    dbc.Row(dbc.Card(
        dbc.CardBody([
            dbc.Button("Export and Start Job",
                       id="job_start_btn",
                       disabled=False,
                       outline=True,
                       color="success",
                       className="me-1"),
            # html.Div(id="trigger", children=0, style=dict(display='none')),
            html.Span(id="job_btn_return",
                      style={"verticalAlign": "middle"})
        ]))),
    html.Br(),
    dbc.Row(dbc.Card(table_layout)),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Hr(),
    html.Div([html.P("Braingeneers@UCSC, 2023"),
              html.P("All Rights Reserved")])
])


####---- end of layout ----####


#######################--------------- callback functions ---------------#######################
@callback(
    Output('dropdown', 'options'),
    Input('textarea_filter_uuid', 'value'),
)
def drop_down(search_value=None):
    print("search_value:", search_value)
    uuids = wr.list_directories(DEFAULT_BUCKET)
    if search_value is not None:
        filtered = [id for id in uuids if search_value in id]
        print(f"number of filtered uuids {len(filtered)}")
        return filtered
    else:
        print(f"number of total uuids {len(uuids)}")
        return uuids


@callback(
    Output('job_table', 'data', allow_duplicate=True),
    Input('batch_job', 'value'),
    State("job_table", "data"),
    State("dropdown", "value"),
    prevent_initial_call=True
)
def update_job_table(input_value, rows, uuid):
    print(f"job input {input_value}")
    if input_value == "Reset":
        print("clear data")
        return []
    elif input_value == "Batch":
        print(f"getting recs for {uuid}")
        recs = wr.list_objects(os.path.join(uuid, "original/data"))
        for i, rec in enumerate(recs):
            # count rows dynamically
            job_info = dict.fromkeys(TABLE_HEADERS)
            job_info["index"] = int(len(rows) + 1)
            job_info["status"] = "ready"
            job_info["uuid"] = uuid  # uuid
            job_info["experiment"] = rec.split("original/data/")[1]
            for h, value in DEFAULT_JOBS["batch"].items():
                job_info[h] = value
            rows.append(job_info)
        print(f"{rows}")
    return rows


@callback(
    Output('job_table', 'data', allow_duplicate=True),
    Output('job_message_output', 'children'),
    Input('add_to_table_button', 'n_clicks'),
    State('checklist_recs', 'value'),
    State("select_jobs", 'value'),
    State("dropdown", "value"),
    State("job_table", "data"),
    prevent_initial_call=True
)
def update_job_table_recs(n_clicks, recs, jobs, uuid, rows):
    if "add_to_table_button" == ctx.triggered_id:
        # also need to disable this button after clicking
        if len(jobs) == 0:
            return rows, "Please choose a job"
        if len(recs) == 0:
            return rows, "Please choose a recording"
        jobs = sorted(jobs)
        print(f"Selected jobs {jobs}")
        for rec in recs:
            for j in jobs:
                j_ind = jobs.index(j)
                j = int(j)
                job_info = dict.fromkeys(TABLE_HEADERS)
                job_info["index"] = int(len(rows) + 1)
                job_info["status"] = "ready"
                job_info["uuid"] = uuid
                job_info["experiment"] = rec
                for h, value in DEFAULT_JOBS["chained"][j].items():
                    job_info[h] = value
                    if j_ind < len(jobs)-1:
                        job_info["next_job"] = int(job_info["index"]+1)
                rows.append(job_info)
        return rows, None



@callback(
    Output("checklist_recs", "options"),
    Input("dropdown", "value"),
    prevent_initial_call=True
)
def display_recordings(uuid):
    rec_path = os.path.join(uuid, "original/data")
    recs_list = wr.list_objects(rec_path)
    if len(recs_list) > 0:
        options = [rec.split("data/")[1] for rec in recs_list]
        return options
    else:
        return []


@callback(
    Output("checklist_recs", "value"),
    Input("select_recording", "value"),
    State("checklist_recs", "options"),
    prevent_initial_call=True
)
def select_recs(value, recs):
    print(recs)
    if value == "Batch":
        return recs.copy()
    elif value == "Reset":
        return []


@callback(
    Output("textarea_metadata", "value"),
    Input("dropdown", "value"),
    prevent_initial_call=True
)
def show_uuid_metadata(uuid):
    metadata_path = os.path.join(uuid, "metadata.json")
    if metadata_path in wr.list_objects(uuid):
        with smart_open.open(metadata_path, 'r') as md:
            metadata = json.load(md)
        if metadata is not None:
            summary = utils.parse_dict(metadata)
            return utils.format_dict_textarea(summary)
    else:
        return "Metadata not available"


@callback(
    Output('job_start_btn', 'disabled', allow_duplicate=True),
    Output('batch_job', 'value', allow_duplicate=True),
    Input('dropdown', 'value'),
    prevent_initial_call=True
)
def remove_selected_radioitem(value):
    if "dropdown" == ctx.triggered_id:
        return False, None


@callback(
    Output('job_start_btn', 'disabled'),
    Input('job_start_btn', 'n_clicks'),
    State('job_table', 'data'),
    # State('batch_job', 'value'),
    prevent_initial_call=True
)
def disable_job_button(n_clicks, data):
    if "job_start_btn" == ctx.triggered_id:
        print(n_clicks)
        if len(data) > 0:
            return True
        elif len(data) == 0:
            return False


@callback(
    Output("job_btn_return", "children"),
    Output('batch_job', 'value'),
    Input("job_start_btn", 'n_clicks'),
    State("job_table", "data"),
    prevent_initial_call=True
)
def save_and_start_jobs(n_clicks, data):
    if len(data) == 0:
        msg = "Add job to start"
        return html.Div(msg), None
    if "job_start_btn" == ctx.triggered_id and len(data) > 0:
        now = datetime.now()
        curr_dt_csv = now.strftime("%Y%m%d%H%M%S") + '.csv'
        s3_path = os.path.join(SERVICE_BUCKET, curr_dt_csv)
        msg = utils.upload_to_s3(data, s3_path)
        # time.sleep(10) # simulate network lag
        if msg is not None:
            return html.Div(msg), None
        else:
            job_index = [int(d['index']) for d in data if d['next_job'] == "None"]
            msg = utils.mqtt_start_job(s3_path, job_index)
            if msg is not None:
                return html.Div(msg), None
            else:
                msg = "Finished Uploading, jobs started"
                return html.Div(msg), "Reset"

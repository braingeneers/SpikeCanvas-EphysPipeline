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
# TODO: show total number of recordings in a uuid (read metadata)
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
                      style={'width': '30%', 'height': 20}, )
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
            style={'width': '50%', 'height': 80}, )
        ]),
    ])
    ),
    html.Hr(),
    dbc.Row(html.Div([
        html.Div(["Select a job: ",
                  dcc.RadioItems(
                      options=['Select All', 'Reset'],
                      id='select_job_input'
                  )
                  ]),
        html.Div(id='select_job_output'),
    ])),
    html.Br(),
    html.Hr(),
    html.Br(),
    dbc.Row(dbc.Card(
        dbc.CardBody([
            dbc.Button("Export and Start Jobs",
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
])


####---- callback functions ----####
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
    Output('job_table', 'data'),
    Input('select_job_input', 'value'),
    State("job_table", "data"),
    State("dropdown", "value"),
    prevent_initial_call=True
)
def update_job_table(input_value, rows, uuid):
    # TODO: add job info to the table
    if input_value == "Reset":
        print("clear data")
        return []
    elif input_value == "Select All":
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
    Output("textarea_metadata", "value"),
    Input("dropdown", "value"),
    prevent_initial_call=True
)
def show_uuid_metadata(uuid):
    def convert_length(frames, fs):
        if isinstance(frames, str):
            frames = int(frames)
        if isinstance(fs, str):
            fs = float(fs)
        return time.strftime('%Hhr %Mmin %Ss', time.gmtime(frames/fs))

    metadata_path = os.path.join(uuid, "metadata.json")
    with smart_open.open(metadata_path, 'r') as md:
        metadata = json.load(md)
    if metadata is not None:
        summary = {"Number of Recordings":
                       len(metadata["ephys_experiments"]),
                   "recordings": {}}
        for name, exp in metadata["ephys_experiments"].items():
            summary["recordings"][name] = \
                {"Hardware": exp["hardware"],
                 "Sample Rate": exp["sample_rate"],
                 "Length":
                     convert_length(exp["blocks"][0]["num_frames"],
                                    exp["sample_rate"]),
                 "Time": exp["timestamp"],
                 "Number of Channels": exp["num_channels"]
                 }
        return utils.format_dict_textarea(summary)
    else:
        return "Metadata not available"


@callback(
    Output('job_start_btn', 'disabled', allow_duplicate=True),
    Output('select_job_input', 'value', allow_duplicate=True),
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
    # State('select_job_input', 'value'),
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
    Output('select_job_input', 'value'),
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

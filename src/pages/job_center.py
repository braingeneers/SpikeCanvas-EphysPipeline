import dash
from dash import html, dcc, callback, Input, Output, State, ctx
from dash import dash_table
import pandas as pd
import braingeneers.utils.s3wrangler as wr
import dash_bootstrap_components as dbc
import os
import csv

# TODO: How to deal with inconsistent index when user remove rows?
# TODO: show total number of recordings in a uuid
# TODO: create datatable for chained jobs
# TODO: functions to check job status in real time

dash.register_page(__name__)

# MAIN_PATH = "s3://braingeneers/ephys/2023-07-11-e-umass-Pak_ASD_Pl10-16/"
# UUID_DROPDOWN = wr.list_objects(MAIN_PATH)
# print(f"UUID_DROPDOWN: {UUID_DROPDOWN}")

####---- default parameters ----####
LOCAL_CSV = "jobs.csv"

TABLE_HEADERS = ["index", "status", "uuid", "experiment",
                 "image", "args", "cpu_request",
                 "memory_request", "disk_request",
                 "GPU", "next_job"]

DEFAULT_JOBS = {"batch":
                    {"image": "surygeng/kilosort_docker:latest",
                     "args": "./run.sh",
                     "cpu_request": 12,
                     "memory_request": 32,
                     "disk_request": 400,
                     "GPU": 1,
                     "next_job": "None"
                     },
                "chained": {}
                }
####---- end default parameters ----####

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
    html.Hr(),
    dbc.Row(html.Div([
        html.Div(["Select a job: ",
                  dcc.RadioItems(
                      options=['Select All', 'Reset'],
                      id='analytics-input'
                  )
                  ]),
        html.Div(id='analytics-output'),
    ])),
    html.Br(),
    html.Hr(),
    html.Br(),
    dbc.Row(dbc.Card(
        dbc.CardBody([
            dbc.Button("Export and Start Jobs",
                       id="job_start_btn",
                       outline=True,
                       color="success",
                       className="me-1"),
            html.Span(id="job_btn_return", style={"verticalAlign": "middle"})
        ]))),
    html.Br(),
    dbc.Row(dbc.Card(table_layout)),
])


####---- callback functions ----####
@callback(
    Output('job_table', 'data'),
    Input('analytics-input', 'value'),
    State("job_table", "data"),
    # State("job_table", "columns"),
    State("dropdown", "value")
)
def update_city_selected(input_value, rows, uuid):
    # TODO: add job info to the table
    if input_value == "Select All":
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
    Output('dropdown', 'options'),
    Input('textarea_filter_uuid', 'value')
)
def drop_down(search_value=None):
    print("search_value:", search_value)
    # print(type(search_value))
    uuids = wr.list_directories('s3://braingeneers/ephys/')
    if search_value is not None:
        filtered = [id for id in uuids if search_value in id]
        print(f"number of filtered uuids {len(filtered)}")
        return filtered
    else:
        print(f"number of total uuids {len(uuids)}")
        return uuids


@callback(
    Output("job_btn_return", "children"),
    Input("job_start_btn", 'n_clicks'),
    State("job_table", "data"),
)
def save_and_start_jobs(n_clicks, data):
    if "job_start_btn" == ctx.triggered_id:
        new_f = open(LOCAL_CSV, 'w', newline='')
        writer = csv.DictWriter(new_f, fieldnames=TABLE_HEADERS)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        new_f.close()
        # TODO:
        # 1. disable button and upload csv to s3
        # 2. when file is on s3, send a start message to the listener
        # 3. if uploading failed, retry 4 times
        # 4. if all failed, return network failure message
        # 3. otherwise return job start message
        msg = "jobs.csv saved"
        return html.Div(msg)

import dash
from dash import html, dcc, callback, Input, Output, State, ctx
from dash import dash_table
import dash_bootstrap_components as dbc
import braingeneers.utils.s3wrangler as wr
import json
from kubernetes import client, config
import utils as utils 
from values import *


dash.register_page(__name__)


####----------------------- make page -----------------------####
layout = dbc.Container([
    html.H2("SpikeCanvas Status Monitor"),
    html.P("Real-time tracking of processing jobs on the cloud", 
           style={'color': '#7f8c8d', 'font-style': 'italic'}),
    html.Hr(),
    dbc.Card([
        # html.H5("Refresh to see the latest job status"),
              dbc.Button("Refresh",
                        id="refresh_button",
                        outline=True,
                        color="primary",
                        ),
             dbc.CardBody(id="jobs_status"),
             ]),

    html.Br(),
    html.Br(),
    html.Br(),
    html.Hr(),
    html.Div([html.P("Braingeneers@UCSC"),
              html.P("All Rights Reserved")])
])


####---- end of layout ----####


#######################--------------- callback functions ---------------#######################
@callback(
    Output("jobs_status", "children"),
    Input("refresh_button", "n_clicks"),
    prevent_initial_call=True
)
def show_jobs_status(n_clicks):
    job_status_fields = []
    if "refresh_button" == ctx.triggered_id:
        if n_clicks is not None and n_clicks > 0:
            config.load_kube_config()
            core_v1 = client.CoreV1Api()
            try:
                pod_list = core_v1.list_namespaced_pod(namespace=NAMESPACE)
            except:
                config.load_kube_config()
                core_v1 = client.CoreV1Api()
                pod_list = core_v1.list_namespaced_pod(namespace=NAMESPACE)

            # create checklist for each job and a datatable for status
            for pod in pod_list.items:
                if not pod.metadata.name.startswith(JOB_PREFIX):
                    continue
                pname = pod.metadata.name
                sts = pod.status.phase
                img = pod.spec.containers[0].image
                data_path, params_path = utils.parse_data_path(pod)
                start_ts_str = "Unknown"
                end_ts_str = "Unknown"
                if sts not in ["Pending", "ContainerCreating"]:
                    start_timestamp = pod.status.start_time
                    start_ts_str = utils.convert_time(start_timestamp)
                if sts in FINISH_FLAGS:
                    end_ts_str = utils.get_pod_completion_time(pod)

                job_status_fields.append(
                    dbc.Card([
                    # html.Br(),
                    # dbc.Label(pname, html_for=f"pod_{pname}"),
                    html.H5(pname),
                    dash_table.DataTable(
                                id="status_table",
                                style_cell={'textAlign': 'left'},
                                columns=[
                                    {'id': "info", 'name': ""},
                                    {'id': "output", 'name': ""}],
                                data=[
                                    {"info": "Status", "output": sts},
                                    {"info": "Job", "output": IMG_JOB_LOOPUP[img]},
                                    {"info": "Data", "output": data_path},
                                    {"info": "Parameter", "output": params_path},
                                    {"info": "Start time", "output": start_ts_str},
                                    {"info": "End time", "output": end_ts_str}
                                ],
                                row_deletable=False
                            ),
                    html.Br()
                        ])
                        )
            if job_status_fields == []:
                job_status_fields.append(html.H5("No active jobs"))
    return job_status_fields

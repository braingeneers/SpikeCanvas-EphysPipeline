import dash
from dash import html, dcc, callback, Input, Output
import dash_table
import pandas as pd

dash.register_page(__name__)

layout = html.Div([
    html.H1('Electrophysiology Job Center'),
    html.Div([
        "Select a job: ",
        dcc.RadioItems(
            options=['Select All', 'Montreal', 'San Francisco'],
            value='Montreal',
            id='analytics-input'
        )
    ]),
    html.Br(),
    html.Div(id='analytics-output'),
])

df = pd.DataFrame(
    [
        ["California", 289, 4395, 15.3, 10826],
        ["Arizona", 48, 1078, 22.5, 2550],
        ["Nevada", 11, 238, 21.6, 557],
        ["New Mexico", 33, 261, 7.9, 590],
        ["Colorado", 20, 118, 5.9, 235],
    ],
    columns=["State", "# Solar Plants", "MW", "Mean MW/Plant", "GWh"],
)


table_layout = dash_table.DataTable(
    id="table",
    columns=[
        {'id': "index", 'name': "index"},
        {'id': "status", 'name': "status"},
        {'id': "uuid", 'name': "uuid"},
        {'id': "experiment", 'name': "experiment"},
        {'id': "image", 'name': "image"},
        {'id': "args", 'name': "args"},
        {'id': "cpu_request", 'name': "cpu_request"},
        {'id': "memory_request", 'name': "memory_request"},
        {'id': "disk_request", 'name': "disk_request"},
        {'id': "GPU", 'name': "GPU"},
        {'id': "next_job", 'name': "next_job"},
    ],
    data=[],
)


@callback(
    Output('analytics-output', 'children'),
    Input('analytics-input', 'value')
)
def update_city_selected(input_value):
    return f'You selected: {input_value}'
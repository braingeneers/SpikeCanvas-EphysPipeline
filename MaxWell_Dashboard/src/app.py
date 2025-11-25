# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
from dash import Dash, html, dcc, callback
import dash_bootstrap_components as dbc
import dash_auth
import os

# TODO: set better page titles

# VALID_USERNAME_PASSWORD_PAIRS = [
#     ['organoid', 'electrophysiology']
# ]

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.SIMPLEX])
# app.server.secret_key = os.urandom(24)
# auth = dash_auth.BasicAuth(
#     app,
#     VALID_USERNAME_PASSWORD_PAIRS
# )
server = app.server
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

for page in dash.page_registry.values():
    print(f"Page to load: {page['name']} - {page['path']}, {page['relative_path']}")

app.layout = html.Div([
    # dcc.Store(id="multipage_data", data=str("{}"), storage_type='local'),   # store data for all pages
    html.H1('SpikeCanvas', style={'color': '#2c3e50', 'text-align': 'center', 'margin': '20px 0'}),
    html.H5('Cloud-based Electrophysiology Data Processing & Analysis Platform', 
            style={'color': '#7f8c8d', 'text-align': 'center', 'font-style': 'italic', 'margin-bottom': '30px'}),
    html.Div([
        html.Div([
            dcc.Link(f"{page['name']}", href=page["relative_path"], 
                    style={'text-decoration': 'none', 'color': '#3498db', 'font-weight': 'bold'})
        ], style={'margin': '10px', 'padding': '10px', 'border': '1px solid #ecf0f1', 'border-radius': '5px'}) 
        for page in dash.page_registry.values()
    ], style={'display': 'flex', 'justify-content': 'center', 'flex-wrap': 'wrap', 'margin': '20px 0'}),
    dash.page_container
])


if __name__ == '__main__':
    # app.run_server(debug=True)  # include hot-reloading by default
    app.run_server(debug=True, port=8050, host='0.0.0.0')
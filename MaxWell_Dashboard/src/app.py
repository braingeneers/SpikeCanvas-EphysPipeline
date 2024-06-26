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
    dcc.Store(id="multipage_data", data=str("{}"), storage_type='local'),
    html.H1('Ephys Pipeline Dashboard'),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
    dash.page_container
])


if __name__ == '__main__':
    # app.run_server(debug=True)  # include hot-reloading by default
    app.run_server(debug=True, port=8050, host='0.0.0.0')
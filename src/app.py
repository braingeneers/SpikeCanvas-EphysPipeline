# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
from dash import Dash, html, dcc, callback
import dash_bootstrap_components as dbc

app = Dash(__name__, use_pages=True)  # , external_stylesheets=[dbc.themes.BOOTSTRAP])
# server = app.server
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

for page in dash.page_registry.values():
    print(f"Page to load: {page['name']} - {page['path']}, {page['relative_path']}")

app.layout = html.Div([
    html.H1('Multi-page Dashboard'),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
    dash.page_container
])


if __name__ == '__main__':
    app.run(debug=True)  # include hot-reloading by default
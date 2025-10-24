import dash
from dash import html, dcc
import os

dash.register_page(__name__, path='/')

# Load the usage instructions
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'USAGE_INSTRUCTIONS.md'), 'r') as f:
        usage_content = f.read()
except FileNotFoundError:
    usage_content = """
# MaxWell Ephys Pipeline Dashboard

Welcome to the MaxWell Ephys Pipeline Dashboard!

## Quick Navigation
- **Job Center**: Submit and manage data processing jobs
- **Status**: Monitor job execution and system status  
- **Analytics**: Explore processed data and generate visualizations
- **Analytics Gallery**: Access pre-configured analysis templates

For detailed instructions, please refer to the USAGE_INSTRUCTIONS.md file.
"""

layout = html.Div([
    html.Br(),
    html.H2('MaxWell Ephys Pipeline Dashboard'),
    html.Div('Complete User Guide & Documentation'),
    html.Hr(),
    dcc.Markdown(usage_content, dangerously_allow_html=True),
    html.Hr(),
    html.Div([html.P("Braingeneers@UCSC"),
              html.P("All Rights Reserved")])
])
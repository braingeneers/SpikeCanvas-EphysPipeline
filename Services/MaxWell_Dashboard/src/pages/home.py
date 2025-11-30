import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path='/')

layout = dbc.Container([
    # Quick Start Guide Section
    dbc.Card([
        dbc.CardBody([
            html.H3("Quick Start Guide", className="card-title"),
            html.P("Get started with SpikeCanvas in 5 easy steps:", className="card-text"),
            html.Ol([
                html.Li("Navigate to the Job Center to begin processing your electrophysiology data"),
                html.Li("Select your dataset from the UUID dropdown (search by experiment name or date)"),
                html.Li("Choose the processing pipeline: individual jobs or complete automated workflow"),
                html.Li("Configure parameters for your analysis (optional)"),
                html.Li("Submit jobs and monitor progress in the Status page")
            ])
        ])
    ], style={'margin-bottom': '20px'}),

    # Dashboard Modules Section
    dbc.Card([
        dbc.CardBody([
            html.H3("Dashboard Modules", className="card-title"),
            
            dbc.Row([
                dbc.Col([
                    html.H5("Job Center", style={'color': '#3498db'}),
                    html.P("Central hub for data processing where you can:")
                ], width=12),
            ]),
            
            html.Ul([
                html.Li("Select recordings for analysis"),
                html.Li("Configure processing pipelines with different job types"),
                html.Li("Set custom parameters for the selected algorithm (optional)"),
                html.Li("Submit batch jobs for multiple recordings"),
                # html.Li("Chain multiple processing steps with dependency management")
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.H5("Analytics", style={'color': '#e74c3c'}),
                    html.P("Interactive visualization featuring:")
                ], width=12),
            ]),
            
            html.Ul([
                html.Li("Electrode mapping and spatial visualization for single units"),
                html.Li("Raster plot for spike train analysis across channels"),
                html.Li("STTC (Spike Time Tiling Coefficient) correlation heatmaps"),
                html.Li("Firing rate distribution"),
                html.Li("Interactive plots with zoom, pan, and selection capabilities")
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.H5("Status Monitor", style={'color': '#27ae60'}),
                    html.P("Track your processing jobs with:")
                ], width=12),
            ]),
            
            html.Ul([
                html.Li("Real-time job status updates and completion tracking"),
                # html.Li("Resource utilization monitoring (CPU, memory, disk usage)"),
                # html.Li("Error logs and debugging information"),
                # html.Li("Job history and processing time analytics"),
                # html.Li("Kubernetes cluster health and capacity monitoring")
            ])
        ])
    ], style={'margin-bottom': '20px'}),

    # # Key Features Section
    # dbc.Card([
    #     dbc.CardBody([
    #         html.H3("Key Features", className="card-title"),
            
    #         dbc.Row([
    #             dbc.Col([
    #                 html.H5("Automated Processing"),
    #                 html.Ul([
    #                     html.Li("Complete pipeline from raw recordings to visualization"),
    #                     html.Li("Spike sorting using Kilosort2 algorithm"),
    #                     html.Li("Quality control with automated curation options"),
    #                     html.Li("Batch processing capabilities for large number of datasets")
    #                 ])
    #             ], width=6),
    #             dbc.Col([
    #                 html.H5("Flexible Configuration"),
    #                 html.Ul([
    #                     html.Li("Custom parameter settings for each processing step"),
    #                     html.Li("Support for MaxWell, MEArec, and NWB data formats"),
    #                     html.Li("Scalable from single recordings to multi-experiment analyses"),
    #                     html.Li("Parameter templates and reusable configurations")
    #                 ])
    #             ], width=6)
    #         ]),
            
    #         dbc.Row([
    #             dbc.Col([
    #                 html.H5("Advanced Analytics"),
    #                 html.Ul([
    #                     html.Li("Interactive visualization with real-time parameter adjustment"),
    #                     html.Li("Statistical analysis including connectivity metrics"),
    #                     html.Li("Cross-correlation analysis and network connectivity"),
    #                     html.Li("Export capabilities for figures and processed data")
    #                 ])
    #             ], width=6),
    #             dbc.Col([
    #                 html.H5("Secure & Reliable"),
    #                 html.Ul([
    #                     html.Li("Cloud storage integration with automatic backup"),
    #                     html.Li("Version control and complete processing history"),
    #                     html.Li("Robust error handling and automatic retry mechanisms"),
    #                     html.Li("Kubernetes orchestration for scalable computing resources")
    #                 ])
    #             ], width=6)
    #         ])
    #     ])
    # ], style={'margin-bottom': '20px'}),

    # Processing Workflow Section
    dbc.Card([
        dbc.CardBody([
            html.H3("Processing Workflow", className="card-title"),
            html.P("SpikeCanvas follows a systematic approach to electrophysiology data analysis:"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("1. Data Input", className="card-title"),
                            html.P("Select raw electrophysiology recordings (MaxWell.h5, NWB formats, ...)")
                        ])
                    ], color="primary", outline=True)
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("2. Spike Sorting", className="card-title"),
                            html.P("Automated detection and clustering of neural spikes using Kilosort2 algorithm")
                        ])
                    ], color="info", outline=True)
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("3. Quality Control", className="card-title"),
                            html.P("Automated curation based on SNR, firing rate, and ISI violations")
                        ])
                    ], color="warning", outline=True)
                ], width=4)
            ], style={'margin-bottom': '15px'}),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("4. Analysis", className="card-title"),
                            html.P("Generate functional connectivity metrics, visualizations, and LFP summaries")
                        ])
                    ], color="success", outline=True)
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("5. Visualization", className="card-title"),
                            html.P("Interactive plots, electrode map, firing rate, raster plot, and STTC heatmap")
                        ])
                    ], color="danger", outline=True)
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("6. Export (under construction)", className="card-title"),
                            html.P("Download processed data, figures, and analysis results in standard formats")
                        ])
                    ], color="dark", outline=True)
                ], width=4)
            ])
        ])
    ], style={'margin-bottom': '20px'}),

    # Tips Section
    dbc.Card([
        dbc.CardBody([
            html.H3("Tips for Success", className="card-title"),
            
            dbc.Row([
                dbc.Col([
                    html.H5("Best Practices"),
                    html.Ul([
                        # html.Li("Ensure recording files are properly formatted and accessible"),
                        html.Li("Start with default parameters before customizing settings"),
                        html.Li("Monitor job status regularly, especially for large datasets"),
                        html.Li("Save custom parameter configurations for reuse across experiments"),
                        html.Li("Use descriptive names for datasets to improve organization")
                    ])
                ], width=6),
                dbc.Col([
                    html.H5("Troubleshooting"),
                    html.Ul([
                        # html.Li("Check Status Monitor for detailed error messages and logs"),
                        # html.Li("Verify S3 bucket access and file permissions"),
                        # html.Li("Ensure sufficient computational resources are available"),
                        # html.Li("Review parameter settings if processing fails"),
                        html.Li("Contact support team for persistent technical issues")
                    ])
                ], width=6)
            ]),
            
            html.Hr(),
            html.P([
                "For technical support and questions, contact the ",
                html.A("Braingeneers team at UCSC", href="https://braingeneers.ucsc.edu", target="_blank"),
                ". "
                # "This platform is developed and maintained by the UC Santa Cruz Genomics Institute."
            ], style={'text-align': 'center', 'margin-top': '20px', 'font-style': 'italic'})
        ])
    ]),
    
    html.Hr(style={'margin': '2rem 0'}),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Braingeneers @ UCSC", 
                      className='text-center mb-1',
                      style={'color': '#34495e', 'font-weight': 'bold'}),
                html.P("Advancing Neural Engineering Through Open Science", 
                      className='text-center mb-1',
                      style={'color': '#7f8c8d', 'font-size': '12px'}),
                html.P("All Rights Reserved", 
                      className='text-center mb-0',
                      style={'color': '#95a5a6', 'font-size': '11px'})
            ])
        ], width=12)
    ])
], fluid=True)
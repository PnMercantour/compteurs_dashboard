from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import dash_leaflet as dl

def create_layout(df):
    """
    Creates the Dash application layout based on the loaded dataframe.
    """
    
    # Metadata Extraction
    meta = df.attrs.get('metadata', {})
    site_name = meta.get('site_name', 'COMPTEURS ROUTIERS').upper()
    d1_label = meta.get('direction_1', 'Sens 1')
    d2_label = meta.get('direction_2', 'Sens 2')
    lat = meta.get('latitude', 0)
    lon = meta.get('longitude', 0)

    # Pre-calculate min/max dates for picker default
    if not df.empty:
        min_date = df['Datetime'].min().date()
        max_date = df['Datetime'].max().date()
    else:
        min_date = None
        max_date = None

    layout = dbc.Container([
        # Header
        dbc.Row([
            dbc.Col(html.Img(src="https://media.mercantour.eu/logos/logo_auto-productions_pnm_quadri_txt_vert.png", style={'height': '80px'}), width=2, className="d-flex align-items-center"),
            dbc.Col(html.H2(f"DASHBOARD {site_name}", className="text-center text-uppercase fw-bold mb-0", style={'letterSpace': '2px'}), width=8),
            dbc.Col([
                dbc.Button("📍", id="map-btn", color="primary", outline=True, className="rounded-circle fw-bold shadow-sm me-2", style={"width": "35px", "height": "35px", "padding": "0"}, title="Voir la carte"),
                dbc.Button("?", id="help-btn", color="secondary", className="rounded-circle text-black fw-bold shadow-sm", style={"width": "35px", "height": "35px", "padding": "0"}),
                dbc.Popover([
                    dbc.PopoverHeader("Astuces Zoom & Navigation"),
                    dbc.PopoverBody([
                        html.Div([
                            html.Strong("🔍 Zoomer :"), 
                            html.Span(" Cliquez gauche + glissez sur une zone du graphique.")
                        ], className="mb-2"),
                        html.Div([
                            html.Strong("🔙 Dézoomer :"), 
                            html.Span(" Double-cliquez n'importe où sur le graphique.")
                        ], className="mb-2"),
                    ], className="small")
                ], target="help-btn", trigger="focus", placement="bottom-end")
            ], width=2, className="d-flex justify-content-end align-items-center")
        ], className="mb-4 mt-4 align-items-center"),

        # Date Picker
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Label("PERIODE D'ANALYSE", className="fw-bold me-3 text-muted small"),
                        dcc.DatePickerRange(
                            id='period-picker',
                            min_date_allowed=min_date,
                            max_date_allowed=max_date,
                            initial_visible_month=max_date,
                            start_date=min_date, 
                            end_date=max_date,
                            display_format='DD/MM/YYYY',
                            style={'border': '1px solid #ddd', 'borderRadius': '5px'}
                        )
                    ], className="d-flex align-items-center justify-content-center")
                ], className="mb-4 shadow-sm border-0")
            ], width=12)
        ]),
        
        # Tabs
        dcc.Tabs([
            dcc.Tab(label='SYNTHÈSE GLOBALE', children=[
                dbc.Container([
                     # Table
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("INDICATEURS CLÉS", className="bg-white fw-bold"),
                                dbc.CardBody(html.Div(id='synthesis-table-container'), className="p-0") 
                            ], className="shadow-sm mb-4 border-0")
                        ], width=12)
                    ], className="mt-3"),
                    
                    # Charts
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("PART MODALE (VÉLOS)", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='pie-active-share', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=6),
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("RÉPARTITION MOTORISÉE", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='pie-motorized-split', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=6)
                    ], className="mb-4"),

                    # New Global Pie Chart
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("DISTRIBUTION TOUTES MOBILITÉS", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='pie-all-mobilities', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=12)
                    ], className="mb-4")
                ], fluid=True)
            ]),
            
            dcc.Tab(label='ANALYSE TEMPORELLE', children=[
                dbc.Container([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("FILTRES D'ANALYSE", className="bg-white fw-bold"),
                                dbc.CardBody([
                                    dbc.Row([
                                        dbc.Col([
                                            html.Label("Echelle de Temps", className="text-muted small fw-bold text-uppercase"),
                                            dcc.RadioItems(
                                                id='chart-freq',
                                                options=[
                                                    {'label': 'Horaire', 'value': 'H'},
                                                    {'label': 'Journalier', 'value': 'D'},
                                                    {'label': 'Mensuel', 'value': 'M'}
                                                ],
                                                value='D',
                                                inline=True,
                                                inputStyle={"margin-right": "5px", "margin-left": "10px"}
                                            )
                                        ], width=4),
                                        dbc.Col([
                                            html.Label("Catégories", className="text-muted small fw-bold text-uppercase"),
                                            dcc.Dropdown(
                                                id='chart-cats',
                                                options=[{'label': c, 'value': c} for c in ['Vélos', 'Motos', 'VL', 'PL']],
                                                value=['Vélos', 'Motos', 'VL', 'PL'],
                                                multi=True
                                            )
                                        ], width=4),
                                        dbc.Col([
                                            html.Label("Sens de Circulation", className="text-muted small fw-bold text-uppercase"),
                                            dcc.Checklist(
                                                id='chart-directions',
                                                options=[
                                                    {'label': f' {d1_label}', 'value': '1'},
                                                    {'label': f' {d2_label}', 'value': '2'}
                                                ],
                                                value=['1', '2'],
                                                inline=True,
                                                inputStyle={"margin-right": "5px", "margin-left": "10px"}
                                            )
                                        ], width=4)
                                    ])
                                ])
                            ], className="shadow-sm mb-4 border-0")
                        ], width=12)
                    ], className="mt-3"),
                    
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("EVOLUTION DU TRAFIC", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='timeline-graph', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=12)
                    ], className="mb-4"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("MATRICE D'INTENSITÉ (JOUR/HEURE)", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='heatmap-day-hour', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=12)
                    ])
                ], fluid=True)
            ]),

            dcc.Tab(label='COMPARAISON PLURIANNUELLE', children=[
                dbc.Container([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("FILTRES COMPARATIFS", className="bg-white fw-bold"),
                                dbc.CardBody([
                                    html.Label("CATÉGORIES CIBLES", className="text-muted small fw-bold text-uppercase"),
                                    dcc.Dropdown(
                                        id='comp-cats',
                                        options=[{'label': c, 'value': c} for c in ['Vélos', 'Motos', 'VL', 'PL']],
                                        value=['Vélos', 'Motos', 'VL', 'PL'],
                                        multi=True
                                    )
                                ])
                            ], className="shadow-sm mb-4 border-0")
                        ], width=12)
                    ], className="mt-3"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("VOLUMES ANNUELS (TMJ)", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='annual-evolution-bar', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=12)
                    ], className="mb-4"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("PROFILS SAISONNIERS COMPARÉS", className="bg-white fw-bold"),
                            dbc.CardBody(dcc.Graph(id='annual-seasonality-line', config={'displayModeBar': False}))
                        ], className="shadow-sm border-0"), width=12)
                    ])
                ], fluid=True)
            ])
        ]),

        # Map Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Localisation du Compteur")),
            dbc.ModalBody(
                dl.Map(center=[lat, lon], zoom=13, children=[
                    dl.TileLayer(),
                    dl.Marker(position=[lat, lon]
                    , icon=dict(
                        iconUrl='/assets/pin_red.svg',
                        iconSize=[30, 40],
                        iconAnchor=[15, 35]
                    ))
                ], style={'width': '100%', 'height': '400px'})
            ),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-map-btn", className="ms-auto", n_clicks=0)
            )
        ], id="map-modal", size="lg", is_open=False),
        
    ], fluid=True, className="bg-light", style={'minHeight': '100vh', 'paddingBottom': '2rem'})
    
    return layout

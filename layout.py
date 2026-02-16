from dash import dcc, html
import dash_bootstrap_components as dbc

# --- Shared Components ---

def create_header(site_name, dashboard_type="ROUTIER", help_content=None, map_btn_id=None):
    """
    Creates the standardized header with Logo, Title, and Help/Map buttons.
    """
    
    # Map button (only if ID provided)
    map_section = []
    if map_btn_id:
        map_section.append(
             dbc.Button("📍", id=map_btn_id, color="light", 
                       className="ms-3 rounded-circle shadow-sm border-0 d-flex align-items-center justify-content-center", 
                       style={"width": "40px", "height": "40px", "fontSize": "1.4rem", "backgroundColor": "transparent"}, 
                       title="Voir la carte")
        )

    # Help button
    help_section = []
    if help_content:
        help_btn_id = f"help-btn-{dashboard_type.lower()}"
        help_section = [
            dbc.Button("?", id=help_btn_id, color="secondary", className="rounded-circle text-black fw-bold shadow-sm", 
                      style={"width": "35px", "height": "35px", "padding": "0"}),
            dbc.Popover([
                dbc.PopoverHeader("Aide / Légende"),
                dbc.PopoverBody(help_content, className="small")
            ], target=help_btn_id, trigger="focus", placement="bottom-end")
        ]

    return dbc.Row([
        dbc.Col(html.Img(src="https://media.mercantour.eu/logos/logo_auto-productions_pnm_quadri_txt_vert.png", style={'height': '80px'}), width=2, className="d-flex align-items-center"),
        dbc.Col([
            html.H2(f"DASHBOARD {dashboard_type} - {site_name}", className="mb-0 text-uppercase fw-bold", style={'letterSpacing': '2px'}),
            html.Div(map_section, className="d-inline-block")
        ], width=8, className="d-flex justify-content-center align-items-center"),
        dbc.Col(help_section, width=2, className="d-flex justify-content-end align-items-center")
    ], className="mb-4 mt-4 align-items-center")


def create_breadcrumb(site_name):
    return dbc.Row(dbc.Col(
        html.Div([
            dcc.Link("Accueil", href="/", className="text-decoration-none text-secondary"),
            html.Span(" / ", className="mx-2 text-muted"),
            html.Span(site_name, className="fw-bold")
        ], className="my-3 small")
    ))

def create_controls_check(picker_id, min_date, max_date, export_btn_id=None, prefix="road"):
    """
    Creates the date picker row. Includes Standard/Seasonal toggle.
    """
    export_section = []
    if export_btn_id:
        export_section.append(
             dbc.Button("📥", id=export_btn_id, color="success", outline=True, 
                       className="ms-3 rounded-circle shadow-sm", 
                       style={"width": "38px", "height": "38px", "padding": "0", "display": "flex", "alignItems": "center", "justifyContent": "center"}, 
                       title="Exporter le rapport")
        )
    
    # Season Controls
    months = [
        {'label': 'Janvier', 'value': 1}, {'label': 'Février', 'value': 2}, {'label': 'Mars', 'value': 3},
        {'label': 'Avril', 'value': 4}, {'label': 'Mai', 'value': 5}, {'label': 'Juin', 'value': 6},
        {'label': 'Juillet', 'value': 7}, {'label': 'Août', 'value': 8}, {'label': 'Septembre', 'value': 9},
        {'label': 'Octobre', 'value': 10}, {'label': 'Novembre', 'value': 11}, {'label': 'Décembre', 'value': 12}
    ]
    days = [{'label': str(i), 'value': i} for i in range(1, 32)]
    
    season_controls = dbc.Collapse([
        html.Hr(className="mx-5 my-2"),
        dbc.Row([
            dbc.Col([], width=3),
            dbc.Col([
                html.Span("Du :", className="me-2 fw-bold text-muted small"),
                dcc.Dropdown(id=f'{prefix}-season-start-day', options=days, value=1, clearable=False, style={'width': '60px', 'display': 'inline-block'}),
                dcc.Dropdown(id=f'{prefix}-season-start-month', options=months, value=1, clearable=False, style={'width': '110px', 'display': 'inline-block', 'marginLeft': '5px'}),
            
                html.Span("Au :", className="mx-2 fw-bold text-muted small ms-4"),
                dcc.Dropdown(id=f'{prefix}-season-end-day', options=days, value=31, clearable=False, style={'width': '60px', 'display': 'inline-block'}),
                dcc.Dropdown(id=f'{prefix}-season-end-month', options=months, value=12, clearable=False, style={'width': '110px', 'display': 'inline-block', 'marginLeft': '5px'}),
            ], className="d-flex align-items-center justify-content-center", width=6),
            
            dbc.Col([], width=3)
        ], className="align-items-center justify-content-center mt-2"),
        
        dbc.Row([
            dbc.Col(
                html.Small("⚠️ Le filtre saisonnier s'applique à l'intérieur de la période sélectionnée (intersection).", className="text-secondary fst-italic"),
                width=12, className="text-center mt-1"
            )
        ])
    ], id=f"{prefix}-season-collapse", is_open=False)

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Switch(id=f"{prefix}-season-switch", label="Filtre Saisonnier", value=False, className="d-inline-block align-middle")
                        ], width=3, className="d-flex align-items-center border-end pe-3"),
                        
                        dbc.Col([
                             # Standard Date Picker
                            html.Div([
                                html.Label("PERIODE D'ANALYSE", className="fw-bold me-3 text-muted small"),
                                dcc.DatePickerRange(
                                    id=picker_id,
                                    min_date_allowed=min_date,
                                    max_date_allowed=max_date,
                                    start_date=min_date, 
                                    end_date=max_date,
                                    display_format='DD/MM/YYYY',
                                    style={'border': '1px solid #ddd', 'borderRadius': '5px'},
                                    clearable=True,
                                    minimum_nights=0
                                )
                            ], id=f"{prefix}-standard-controls", className="text-center")
                        ], width=6, className="d-flex align-items-center justify-content-center"),
                        
                        dbc.Col(html.Div(export_section), width=3, className="d-flex align-items-center justify-content-end")
                    ], className="align-items-center"),
                    
                    season_controls
                    
                ], className="p-2")
            ], className="mb-4 shadow-sm border-0")
        ], width=12)
    ])

# --- Unified Layout ---

def create_dashboard_layout(df, dashboard_type="ROUTIER"):
    """
    Unified layout generator for both Road and Pedestrian dashboards.
    """
    import dash_leaflet as dl
    
    # --- 1. Configuration & ID Mapping ---
    is_road = (dashboard_type == "ROUTIER")
    ids = {
        'picker': 'period-picker' if is_road else 'ped-date-picker',
        'export_btn': 'export-btn' if is_road else 'ped-export-btn',
        'tab_synth_val': 'tab-synthese', # Unified
        'tab_temp_val' : 'tab-temporal',
        'tab_ann_val'  : 'tab-annual',
        'tabs_id': 'road-tabs' if is_road else 'ped-tabs',
        
        # Site Store
        'store_id': 'current-site-id' if is_road else 'ped-site-id',
    }
    
    # Metadata
    meta = df.attrs.get('metadata', {})
    site_name = meta.get('site_name', 'COMPTEUR').upper()
    lat = meta.get('latitude', 0)
    lon = meta.get('longitude', 0)
    d1_label = meta.get('direction_1', 'Sens 1')
    d2_label = meta.get('direction_2', 'Sens 2')

    # Date Range
    if not df.empty:
        min_date = df['Datetime'].min().date()
        max_date = df['Datetime'].max().date()
    else:
        min_date = max_date = None

    # Help Content
    if is_road:
        help_content = [
            html.Div([html.Strong("🔍 Zoomer :"), html.Span(" Cliquez gauche + glissez sur une zone du graphique.")], className="mb-2"),
            html.Div([html.Strong("🔙 Dézoomer :"), html.Span(" Double-cliquez n'importe où sur le graphique.")], className="mb-2"),
            html.Hr(),
            html.H6("Lexique", className="fw-bold mb-2"),
            html.Div([html.Strong("TMJ :"), " Trafic Moyen Journalier (Moyenne quotidienne sur la période)."], className="mb-1"),
            html.Div([html.Strong("TMJ JO :"), " Trafic Moyen Journalier des Jours Ouvrés (Lun-Ven)."], className="mb-1"),
            html.Div([html.Strong("TMJ WE :"), " Trafic Moyen Journalier des Week-ends (Sam-Dim)."], className="mb-1"),
            html.Div([html.Strong("VT :"), " Vitesse Moyenne (si disponible)."], className="mb-1"),
            html.Div([html.Strong("VL :"), " Véhicules Légers (Voitures < 3.5t)."], className="mb-1"),
            html.Div([html.Strong("PL :"), " Poids Lourds (> 3.5t)."], className="mb-1"),
        ]
    else:
        help_content = [
            html.Div([html.Strong("🔍 Zoomer :"), html.Span(" Utilisez la molette de la souris, l'échelle s'ajuste dynamiquement.")], className="mb-2"),
            html.Div([html.Strong("FMJ :"), " Fréquentation Moyenne Journalière."], className="mb-1"),
            html.Div([html.Strong("JO :"), " Jours Ouvrés (Lundi-Vendredi)."], className="mb-1"),
            html.Div([html.Strong("WE :"), " Week-end (Samedi-Dimanche)."], className="mb-1"),
        ]

    # --- 2. Build Scaffold ---
    
    header = create_header(site_name, dashboard_type=dashboard_type, help_content=help_content, map_btn_id="map-btn")
    
    prefix = "road" if is_road else "ped"
    controls = create_controls_check(ids['picker'], min_date, max_date, export_btn_id=ids['export_btn'] if is_road else None, prefix=prefix) 
    
    # --- 3. Build Tabs Content ---
    
    # Tab 1: Synthesis
    # Unified Structure: Container > Row > Col > Card > Header + Body
    # Content differs.
    if is_road:
        # Complex Road Synthesis
        synth_content = dbc.Container([
            dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader("INDICATEURS CLÉS", className="bg-white fw-bold"), dbc.CardBody(html.Div(id='synthesis-table-container'), className="p-0")], className="shadow-sm mb-4 border-0"))], className="mt-3"),
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("PART MODALE (VÉLOS)", className="bg-white fw-bold"), dbc.CardBody(dcc.Graph(id='pie-active-share', config={'displayModeBar': False}))], className="shadow-sm border-0"), width=6),
                dbc.Col(dbc.Card([dbc.CardHeader("RÉPARTITION MOTORISÉE", className="bg-white fw-bold"), dbc.CardBody(dcc.Graph(id='pie-motorized-split', config={'displayModeBar': False}))], className="shadow-sm border-0"), width=6)
            ], className="mb-4"),
            dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader("DISTRIBUTION TOUTES MOBILITÉS", className="bg-white fw-bold"), dbc.CardBody(dcc.Graph(id='pie-all-mobilities', config={'displayModeBar': False}))], className="shadow-sm border-0"))])
        ], fluid=True)
    else:
        # Simple Pedestrian Synthesis
        synth_content = html.Div(id="ped-content-synthese", className="p-4")

    # Tab 2: Temporal
    if is_road:
        temporal_content = dbc.Container([
            dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader("FILTRES D'ANALYSE", className="bg-white fw-bold"), dbc.CardBody([
                dbc.Row([
                    dbc.Col([html.Label("Echelle de Temps", className="text-muted small fw-bold text-uppercase"), dcc.RadioItems(id='chart-freq', options=[{'label': 'Horaire', 'value': 'H'}, {'label': 'Journalier', 'value': 'D'}, {'label': 'Mensuel', 'value': 'M'}], value='D', inline=True, inputStyle={"margin-right": "5px", "margin-left": "10px"})], width=4),
                    dbc.Col([html.Label("Catégories", className="text-muted small fw-bold text-uppercase"), dcc.Dropdown(id='chart-cats', options=[{'label': c, 'value': c} for c in ['Vélos', 'Motos', 'VL', 'PL']], value=['Vélos', 'Motos', 'VL', 'PL'], multi=True)], width=4),
                    dbc.Col([html.Label("Sens de Circulation", className="text-muted small fw-bold text-uppercase"), dcc.Checklist(id='chart-directions', options=[{'label': f' {d1_label}', 'value': '1'}, {'label': f' {d2_label}', 'value': '2'}], value=['1', '2'], inline=True, inputStyle={"margin-right": "5px", "margin-left": "10px"})], width=4)
                ])
            ])], className="shadow-sm mb-4 border-0"))], className="mt-3"),
            dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader("EVOLUTION DU TRAFIC", className="bg-white fw-bold"), dbc.CardBody(dcc.Graph(id='timeline-graph'))], className="shadow-sm border-0"))], className="mb-4"),
            dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader("MATRICE D'INTENSITÉ (JOUR/HEURE)", className="bg-white fw-bold"), dbc.CardBody(dcc.Graph(id='heatmap-day-hour'))], className="shadow-sm border-0"))])
        ], fluid=True)
    else:
        temporal_content = dbc.Container([
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("EVOLUTION DE LA FRÉQUENTATION", className="bg-white fw-bold"),
                    dbc.CardBody(dcc.Graph(id='ped-timeline-graph', config={'scrollZoom': True, 'locale': 'fr'}))
                ], className="shadow-sm border-0"), width=12)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("MATRICE D'INTENSITÉ (JOUR/HEURE)", className="bg-white fw-bold"),
                    dbc.CardBody(dcc.Graph(id='ped-heatmap-day-hour', config={'locale': 'fr'}))
                ], className="shadow-sm border-0"), width=12)
            ])
        ], fluid=True, className="p-4")

    # Tab 3: Annual
    if is_road:
        annual_content = dbc.Container([
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
                    dbc.CardBody(dcc.Graph(id='annual-evolution-bar'))
                ], className="shadow-sm border-0"), width=12)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("PROFILS SAISONNIERS COMPARÉS", className="bg-white fw-bold"),
                    dbc.CardBody(dcc.Graph(id='annual-seasonality-line'))
                ], className="shadow-sm border-0"), width=12)
            ])
        ], fluid=True)
    else:
        annual_content = html.Div(id="ped-content-annual", className="p-4")

    # Tabs
    
    tabs = dcc.Tabs([
        dcc.Tab(label="SYNTHÈSE GLOBALE", value="tab-synthese", children=synth_content),
        dcc.Tab(label="ANALYSE TEMPORELLE", value="tab-temporal", children=temporal_content),
        dcc.Tab(label="COMPARAISON PLURIANNUELLE", value="tab-annual", children=annual_content),
    ], id=ids['tabs_id'], value="tab-synthese", colors={"border": "#d6d6d6", "primary": "#16A085", "background": "#f9f9f9"})

    # Map Modal (Only Road)
    map_modal = html.Div()

    map_modal = dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Localisation du Compteur")),
        dbc.ModalBody(dl.Map(center=[lat, lon], zoom=13, children=[dl.TileLayer(), dl.Marker(position=[lat, lon], icon=dict(iconUrl='/assets/pin_red.svg', iconSize=[30, 40], iconAnchor=[15, 35]))], style={'width': '100%', 'height': '400px'})),
        dbc.ModalFooter(dbc.Button("Fermer", id="close-map-btn", className="ms-auto", n_clicks=0))
    ], id="map-modal", size="lg", is_open=False)

    return dbc.Container([
        header, 
        controls, 
        tabs, 
        map_modal, 
        dcc.Download(id="download-report")
    ], fluid=True, className="px-4 py-3 bg-light", style={"minHeight": "100vh"})
                     
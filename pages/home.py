import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from data_loader import DataManager
import numpy as np

dash.register_page(__name__, path='/', title='Accueil - Trafic Mercantour')

def layout():
    dm = DataManager()
    sites = dm.get_sites()
    
    # Map Markers
    markers = []
    centers = []

    icon_routier = { "iconUrl": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-violet.png", "iconSize": [25, 41] } 
    icon_pieton = { "iconUrl": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png", "iconSize": [25, 41] }
    
    for site in sites:
        if site.get('coords'):
            icon = icon_routier if site['type'] == "routier" else icon_pieton
            center = site['coords'] # Center on last site or default
            markers.append(
                dl.Marker(position=site['coords'], icon=icon, children=[
                     dl.Tooltip(f"{site['name']}"),
                     dl.Popup(html.Div([
                         html.H4(site['name']),
                         html.H6(f"Compteur {site['type']}"),
                         dcc.Link("Voir le tableau de bord", href=f"/dashboard/{site['id']}")
                     ]))
                ])
            )
            centers.append(center)
            
    # Cards
    cards = []
    for site in sites:
        card = dbc.Col(dbc.Card([
            # Placeholder image or map snapshot could go here
            dbc.CardBody([
                html.H5(site['name'], className="card-title fw-bold"),
                html.P("Consultation des données historiques de comptage.", className="card-text text-muted"),
                dbc.Button("Accéder au tableau de bord", href=f"/dashboard/{site['id']}", color="primary", className="mt-3")
            ])
        ], className="h-100 shadow-sm border-0"), width=12, md=6, lg=4, className="mb-4")
        cards.append(card)

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Img(src="https://media.mercantour.eu/logos/logo_auto-productions_pnm_quadri_txt_vert.png", style={'height': '100px'}, className="mb-3"),
                html.H1("Observatoire de la Fréquentation", className="display-4 fw-bold text-primary mb-3"),
                html.P("Bienvenue sur le portail d'analyse des compteurs routiers du Parc national du Mercantour.", className="lead text-secondary")
            ], width=12, className="text-center py-5")
        ]),
        
        dbc.Row([
             dbc.Col(
                dl.Map(
                    center=np.array(centers).mean(axis=0).tolist() if centers else [44.1, 6.9],
                    zoom=10,
                    children=[
                        dl.LayersControl([
                            dl.BaseLayer(dl.TileLayer(), name="OSM", checked=True),
                            dl.BaseLayer(
                                dl.TileLayer(
                                    url="https://data.geopf.fr/wmts?" +
                                    "&REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0" +
                                    "&STYLE=normal" +
                                    "&TILEMATRIXSET=PM" +
                                    "&FORMAT=image/jpeg"+
                                    "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS"+
                                "&TILEMATRIX={z}" +
                                    "&TILEROW={y}" +
                                    "&TILECOL={x}",
                                    attribution="IGN-F/Geoportail"
                                ),
                                name="Orthophoto"
                            ),
                        ]),
                        dl.LayerGroup(markers)
                    ],
                    style={'height': '500px', 'width': '100%', 'borderRadius': '15px'},
                    className="shadow mb-5"
                ),
                 width=12
             )
        ]),
        
        dbc.Row([
            dbc.Col(html.H3("Sites disponibles", className="mb-4 text-uppercase fw-bold text-secondary"), width=12)
        ]),
        
        dbc.Row(cards)
    ], fluid=True, className="px-4")

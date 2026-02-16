import pandas as pd
import plotly.io as pio
import plotly.graph_objects as go
from utils import compute_metrics

# Helper for basic metrics

def _generate_table_html(df, theoritical_days=None):
    if df.empty:
        return "<p class='text-muted'>Pas de données pour la table.</p>"
        
    meta = df.attrs.get('metadata', {})
    d1_label = meta.get('direction_1', 'Sens 1')
    d2_label = meta.get('direction_2', 'Sens 2')
    
    # Calculate days stats based on the data present
    if 'Date' not in df.columns:
        df['Date'] = df['Datetime'].dt.date
        
    dates = df['Date'].unique()
    dates_df = pd.DataFrame({'Date': dates})
    dates_df['Date'] = pd.to_datetime(dates_df['Date'])
    dates_df['DayName'] = dates_df['Date'].dt.day_name()
    dates_df['IsWE'] = dates_df['DayName'].isin(['Saturday', 'Sunday'])
    
    if theoritical_days is None: 
        nb_days_total = len(dates_df)
        nb_days_jo = len(dates_df[~dates_df['IsWE']])
        nb_days_we = len(dates_df[dates_df['IsWE']])
    else:
        nb_days_total = theoritical_days['nb_full_days']
        nb_days_jo = theoritical_days['nb_JO_days']
        nb_days_we = theoritical_days['nb_WE_days']
        
    categories = ['Vélos', 'Motos', 'VL', 'PL']
    
    # Build Rows HTML
    rows_html = ""
    
    def make_cells_html(label, filter_cat=None):
        row_str = f"<tr><td style='font-weight:bold;'>{label}</td>"
        for sens_code in ['1', '2']:
            d_data = df[df['Direction'].astype(str).str.contains(sens_code)]
            if filter_cat:
                d_data = d_data[d_data['UnifiedCategory'] == filter_cat]
            m = compute_metrics(d_data, nb_days_total, nb_days_jo, nb_days_we)
            for val in m:
                formatted = val if isinstance(val, str) else f"{val:,}".replace(",", " ")
                css_class = ""
                # Highlight TMJ columns
                if val == m[1]: css_class = "fw-bold"
                row_str += f"<td class='text-end {css_class}'>{formatted}</td>"
        row_str += "</tr>"
        return row_str

    for cat in categories:
        rows_html += make_cells_html(cat, cat)
    rows_html += make_cells_html("Toutes Mobilités", None)
    
    # Full Table HTML with Bootstrap classes
    table_html = f"""
    <div class="table-responsive">
    <table class="table table-bordered table-hover table-sm mb-0">
        <thead class="table-light">
            <tr>
                <th rowspan="2" style="vertical-align: middle;">Catégorie</th>
                <th colspan="5" class="text-center" style="background-color: #e8f0fe;">{d1_label}</th>
                <th colspan="5" class="text-center" style="background-color: #f1f3f4;">{d2_label}</th>
            </tr>
            <tr class="text-center small text-muted">
                <th>TOTAL</th><th>TMJ</th><th>TMJ JO</th><th>TMJ WE</th><th>VT</th>
                <th>TOTAL</th><th>TMJ</th><th>TMJ JO</th><th>TMJ WE</th><th>VT</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    </div>
    """
    return table_html

def generate_html_report(df, figures, label, theoretical_days=None):
    """
    Generates a standalone HTML report with logo, stats table, and figures.
    """
    meta = df.attrs.get('metadata', {})
    site_name = meta.get('site_name', 'Inconnu')
    logo_url = "https://media.mercantour.eu/logos/logo_auto-productions_pnm_quadri_txt_vert.png"
    
    # Generate Table
    table_html = _generate_table_html(df, theoretical_days)
    
    # Generate Charts HTML
    charts_html = ""
    for title, fig in figures.items():
        if fig:
            # Handle dictionary figures (from Dash state)
            if isinstance(fig, dict):
                fig = go.Figure(fig)
            
            # Use responsive Plotly HTML div
            plot_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={'responsive': True})
            charts_html += f"""
            <div class="card mb-5 page-break">
                <div class="card-header bg-white fw-bold border-bottom-0 py-3">{title}</div>
                <div class="card-body p-1">
                    {plot_html}
                </div>
            </div>
            """

    # Assemble Full HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Rapport - {site_name} - {label}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
        <style>
            body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 2rem; background: #f8f9fa; color: #212529; }}
            .header-container {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 2rem; }}
            .logo-img {{ max-height: 80px; width: auto; }}
            .report-title {{ margin: 0; color: #2c3e50; text-transform: uppercase; font-weight: 800; letter-spacing: 1px; font-size: 1.8rem; }}
            .report-subtitle {{ color: #6c757d; margin-top: 0.5rem; font-weight: 500; }}
            .section-title {{ 
                border-left: 5px solid #0d6efd; 
                padding-left: 1rem; 
                margin-bottom: 1.5rem; 
                color: #2c3e50; 
                font-weight: 700; 
                text-transform: uppercase;
                font-size: 1.25rem;
            }}
            .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075); border-radius: 8px; overflow: hidden; }}
            .table th {{ font-weight: 600; text-transform: uppercase; font-size: 0.85rem; }}
            
            @media print {{
                .page-break {{ page-break-inside: avoid; }}
                body {{ padding: 0; background: white; }}
                .header-container {{ box-shadow: none; border-bottom: 1px solid #ddd; border-radius: 0; }}
                .container {{ max-width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header-container d-flex align-items-center justify-content-between">
                <img src="{logo_url}" alt="Logo Mercantour" class="logo-img">
                <div class="text-center flex-grow-1 mx-4">
                     <h1 class="report-title">RAPPORT DE TRAFIC</h1>
                     <h2 class="h5 text-muted text-uppercase mb-2">{site_name}</h2>
                     <p class="report-subtitle mb-0 badge bg-light text-dark border">Période : {label}</p>
                </div>
                <div style="width: 120px;"></div> <!-- Spacer for balance -->
            </div>

            <!-- Stats Section -->
            <section class="mb-5 page-break">
                <h3 class="section-title">Synthèse des Résultats</h3>
                <div class="card">
                    <div class="card-body p-0">
                        {table_html}
                    </div>
                </div>
            </section>

            <!-- Charts Section -->
            <section>
                <h3 class="section-title">Analyse Graphique</h3>
                {charts_html}
            </section>
            
            <!-- Lexique Section -->
            <section class="mt-5 page-break">
                 <h3 class="section-title">Lexique</h3>
                 <div class="card bg-light border-0">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <ul class="list-unstyled mb-0 small">
                                    <li class="mb-2"><strong class="text-primary">TMJ</strong> : Trafic Moyen Journalier (Moyenne quotidienne).</li>
                                    <li class="mb-2"><strong class="text-primary">TMJ JO</strong> : Moyenne des Jours Ouvrés (Lun-Ven).</li>
                                    <li class="mb-2"><strong class="text-primary">TMJ WE</strong> : Moyenne des Week-ends (Sam-Dim).</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <ul class="list-unstyled mb-0 small">
                                    <li class="mb-2"><strong class="text-primary">VL</strong> : Véhicules Légers (Voitures < 3.5t).</li>
                                    <li class="mb-2"><strong class="text-primary">PL</strong> : Poids Lourds (> 3.5t).</li>
                                    <li class="mb-2"><strong class="text-primary">VT</strong> : Vitesse Moyenne (si disponible).</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                 </div>
            </section>
            
            <footer class="text-center text-muted mt-5 small py-3 border-top">
                <p class="mb-0">Document généré automatiquement le {pd.Timestamp.now().strftime('%d/%m/%Y à %H:%M')}</p>
            </footer>
        </div>
    </body>
    </html>
    """
    
    return html_content

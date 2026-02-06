import pandas as pd

# --- Constants ---
# Professional Palette (Flat/Modern)
COLOR_MAP = {
    'VL': '#2980B9',       # Professional Blue
    'Motos': '#F39C12',    # Warning Orange
    'PL': '#C0392B',       # Alert Red
    'Vélos': '#16A085',    # Elegant Teal/Green
    'Motorisé': '#95A5A6', # Neutral Grey
    'Sens 1': '#8E44AD',   # Purple
    'Sens 2': '#2C3E50',   # Dark Blue
}

# Common Layout Style for consistency
COMMON_LAYOUT = dict(
    font=dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", size=12, color="#2c3e50"),
    title_font=dict(size=14, family="Segoe UI Semibold", color="#2c3e50"),
    plot_bgcolor="rgba(0,0,0,0)", # Transparent background
    paper_bgcolor="rgba(0,0,0,0)", # Transparent background
    margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(255,255,255,0.5)",
        bordercolor="#eee",
        borderwidth=1
    ),
    xaxis=dict(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='#eee',
        mirror=True
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='#f0f0f0',
        showline=True,
        linewidth=1,
        linecolor='#eee',
        mirror=True
    )
)

FRENCH_MONTHS_MAP = {
    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin', 
    7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
}

DAYS_ORDER_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

FRENCH_DAYS = {
    'Monday': 'Lundi', 
    'Tuesday': 'Mardi', 
    'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi', 
    'Friday': 'Vendredi', 
    'Saturday': 'Samedi', 
    'Sunday': 'Dimanche'
}

TZ = "Europe/Paris"

# --- Helpers ---

def filter_by_date(df, start_date, end_date):
    """
    Robust date filtering using UTC comparison.
    """
    if not start_date or not end_date:
        return df
    try:
        mask = (df['Datetime'] >= pd.to_datetime(start_date).tz_localize(TZ)) & \
               (df['Datetime'] < (pd.to_datetime(end_date).tz_localize(TZ) + pd.Timedelta(days=1)))
        return df[mask].copy()
    except:
        return df

def compute_metrics(sub_df, days_total, days_jo, days_we):
    """
    Returns [Total, TMJ, TMJ_JO, TMJ_WE, SpeedStr]
    """
    if sub_df.empty:
        return [0, 0, 0, 0, "-"]    
    total = len(sub_df)
    tmj = int(round(total / max(1, days_total)))
    sub_jo = sub_df[sub_df['DayType'] == 'JO']
    tmj_jo = int(round(len(sub_jo) / max(1, days_jo))) if days_jo > 0 else 0
    sub_we = sub_df[sub_df['DayType'] == 'WE']
    tmj_we = int(round(len(sub_we) / max(1, days_we))) if days_we > 0 else 0
    
    if 'Speed' in sub_df.columns:
         vt = sub_df['Speed'].mean()
         vt_str = "-" if pd.isna(vt) else f"{vt:.0f} km/h"
    else:
         vt_str = "-"
    return [total, tmj, tmj_jo, tmj_we, vt_str]

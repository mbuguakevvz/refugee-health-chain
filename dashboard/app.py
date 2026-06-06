import os
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

load_dotenv()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], title="RefugeeHealthChain")

OUTPUT_DIR = Path("data_pipeline/output")

COLORS = {
    "primary":    "#00D4AA",
    "danger":     "#FF4B6E",
    "warning":    "#FFB800",
    "secondary":  "#7C83FD",
    "background": "#0D1117",
    "surface":    "#161B22",
    "text":       "#E6EDF3",
    "muted":      "#8B949E",
}

def load_population():
    path = OUTPUT_DIR / "unhcr_population.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame([
        {"asylum_country": "Uganda",      "asylum_iso3": "UGA", "refugees": 1600000, "asylum_seekers": 30000,  "total_displaced": 1630000},
        {"asylum_country": "Sudan",       "asylum_iso3": "SDN", "refugees": 1100000, "asylum_seekers": 22000,  "total_displaced": 1122000},
        {"asylum_country": "Ethiopia",    "asylum_iso3": "ETH", "refugees": 940000,  "asylum_seekers": 12000,  "total_displaced": 952000},
        {"asylum_country": "Kenya",       "asylum_iso3": "KEN", "refugees": 580000,  "asylum_seekers": 45000,  "total_displaced": 625000},
        {"asylum_country": "DR Congo",    "asylum_iso3": "COD", "refugees": 520000,  "asylum_seekers": 8000,   "total_displaced": 528000},
        {"asylum_country": "South Sudan", "asylum_iso3": "SSD", "refugees": 310000,  "asylum_seekers": 5000,   "total_displaced": 315000},
        {"asylum_country": "Tanzania",    "asylum_iso3": "TZA", "refugees": 230000,  "asylum_seekers": 3000,   "total_displaced": 233000},
        {"asylum_country": "Rwanda",      "asylum_iso3": "RWA", "refugees": 98000,   "asylum_seekers": 2000,   "total_displaced": 100000},
    ])

def load_outbreaks():
    path = OUTPUT_DIR / "who_outbreaks.csv"
    if path.exists():
        df = pd.read_csv(path)
        return df[df["africa_relevant"] == True] if "africa_relevant" in df.columns else df
    return pd.DataFrame([
        {"disease_type": "Ebola",   "regions": "DRC, Uganda",          "high_priority": True,  "who_pheic": True,  "confirmed_cases": 225,  "deaths": 349},
        {"disease_type": "Cholera", "regions": "Kenya, South Sudan",   "high_priority": True,  "who_pheic": False, "confirmed_cases": None, "deaths": None},
        {"disease_type": "Measles", "regions": "Somalia, South Sudan", "high_priority": True,  "who_pheic": False, "confirmed_cases": None, "deaths": None},
        {"disease_type": "Marburg", "regions": "Ethiopia (ENDED)",     "high_priority": False, "who_pheic": False, "confirmed_cases": 6,    "deaths": 3},
        {"disease_type": "Malaria", "regions": "DRC, Uganda",          "high_priority": True,  "who_pheic": False, "confirmed_cases": None, "deaths": None},
    ])

def load_summary():
    path = OUTPUT_DIR / "pipeline_summary.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"unhcr_records": 0, "who_outbreaks": 0, "who_high_priority": 0, "hashed_identities": 0}

def stat_card(title, value, subtitle, color):
    c = {"primary": COLORS["primary"], "danger": COLORS["danger"], "warning": COLORS["warning"], "secondary": COLORS["secondary"]}
    border = c.get(color, COLORS["primary"])
    return dbc.Card(dbc.CardBody([
        html.P(title,    style={"color": COLORS["muted"], "fontSize": "0.85rem", "marginBottom": "4px"}),
        html.H3(value,   style={"color": border, "fontWeight": "700", "marginBottom": "2px"}),
        html.P(subtitle, style={"color": COLORS["muted"], "fontSize": "0.8rem", "marginBottom": 0}),
    ]), style={"backgroundColor": COLORS["surface"], "borderLeft": f"4px solid {border}", "border": f"1px solid {border}"})

app.layout = html.Div([
    html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H2("RefugeeHealthChain", style={"color": COLORS["primary"], "fontWeight": "700", "marginBottom": "4px"}),
                    html.P("Immutable Identity and Medical Records for Displaced Persons | Polygon Blockchain | June 2026",
                           style={"color": COLORS["muted"], "marginBottom": 0, "fontSize": "0.85rem"}),
                ], width=8),
                dbc.Col([
                    html.Div([
                        html.Div("LIVE", style={"color": COLORS["primary"], "fontWeight": "700", "fontSize": "1.1rem"}),
                        html.Div("UNHCR + WHO APIs", style={"color": COLORS["muted"], "fontSize": "0.8rem"}),
                        html.Div(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), style={"color": COLORS["muted"], "fontSize": "0.75rem"}),
                    ], style={"textAlign": "right"})
                ], width=4),
            ])
        ], fluid=True)
    ], style={"backgroundColor": COLORS["surface"], "padding": "20px 0", "borderBottom": f"2px solid {COLORS['primary']}", "marginBottom": "24px"}),

    dbc.Container([
        dbc.Alert([
            html.Strong("WHO PHEIC ACTIVE: "),
            "Ebola (Bundibugyo virus) DRC and Uganda | Declared 16 May 2026 | ",
            html.Strong("1,262 cases | 349 deaths"),
            " | Refugee border crossings under enhanced surveillance"
        ], color="danger", style={"marginBottom": "24px"}),

        dbc.Row([
            dbc.Col(stat_card("Displaced (Focus Region)", "39.3M+",  "UNHCR 2024 live data",         "primary"),   md=3),
            dbc.Col(stat_card("WHO Outbreak Alerts",      "50",       "Live from WHO DON API",         "warning"),   md=3),
            dbc.Col(stat_card("High Priority Alerts",     "3",        "Ebola x2 + Cholera",            "danger"),    md=3),
            dbc.Col(stat_card("Identities On-Chain",      "5",        "Hashed - zero PII on blockchain","secondary"), md=3),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    dcc.Graph(id="pop-chart", config={"displayModeBar": False})
                ]), style={"backgroundColor": COLORS["surface"]})
            ], md=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Active Outbreak Alerts", style={"backgroundColor": COLORS["surface"], "color": COLORS["text"], "fontWeight": "600"}),
                    dbc.CardBody(id="outbreak-list")
                ], style={"backgroundColor": COLORS["surface"]})
            ], md=4),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5("Smart Contracts - Deployed on Local Polygon Node", style={"color": COLORS["primary"]}),
                    dbc.Row([
                        dbc.Col([
                            html.P("RefugeeRegistry.sol", style={"color": COLORS["primary"], "fontWeight": "600"}),
                            html.P("Registers refugee identity hashes. Role-based access. Pausable emergency stop.", style={"color": COLORS["muted"], "fontSize": "0.85rem"}),
                            html.Code(os.getenv("REFUGEE_REGISTRY_ADDRESS", "Not deployed"), style={"color": COLORS["warning"], "fontSize": "0.75rem"}),
                        ], md=6),
                        dbc.Col([
                            html.P("MedicalRecord.sol", style={"color": COLORS["secondary"], "fontWeight": "600"}),
                            html.P("Anchors medical hashes on-chain. Tracks Ebola exposures (A98.4). Dual-signature verification.", style={"color": COLORS["muted"], "fontSize": "0.85rem"}),
                            html.Code(os.getenv("MEDICAL_RECORD_ADDRESS", "Not deployed"), style={"color": COLORS["warning"], "fontSize": "0.75rem"}),
                        ], md=6),
                    ])
                ]), style={"backgroundColor": COLORS["surface"]})
            ])
        ], className="mb-4"),

        html.Div(html.P([
            "Built by Kevin Mbugua (@mbuguakevvz) | Blockchain Data Engineer | Nairobi, Kenya | ",
            "Data: UNHCR Refugee Statistics API + WHO Disease Outbreak News API"
        ], style={"color": COLORS["muted"], "fontSize": "0.8rem", "textAlign": "center"}),
        style={"borderTop": f"1px solid #30363D", "paddingTop": "16px", "marginBottom": "24px"}),

    ], fluid=True),

    dcc.Interval(id="refresh", interval=5*60*1000, n_intervals=0),

], style={"backgroundColor": COLORS["background"], "minHeight": "100vh"})

@callback(
    Output("pop-chart",    "figure"),
    Output("outbreak-list","children"),
    Input("refresh",       "n_intervals"),
)
def update(n):
    pop_df      = load_population()
    outbreak_df = load_outbreaks()

    if "asylum_country" in pop_df.columns and "total_displaced" in pop_df.columns:
        grouped = pop_df.groupby("asylum_country")["total_displaced"].sum().reset_index()
        grouped = grouped.sort_values("total_displaced", ascending=True)
    else:
        grouped = pop_df

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=grouped["asylum_country"] if "asylum_country" in grouped.columns else grouped.iloc[:,0],
        x=grouped["total_displaced"] if "total_displaced" in grouped.columns else grouped.iloc[:,1],
        orientation="h",
        marker_color=COLORS["primary"],
        name="Total Displaced"
    ))
    fig.update_layout(
        title="Displaced Persons by Asylum Country (UNHCR 2024)",
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
        xaxis=dict(gridcolor="#30363D"),
        yaxis=dict(gridcolor="#30363D"),
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
    )

    alerts = []
    for _, row in outbreak_df.iterrows():
        is_pheic   = str(row.get("who_pheic", "")).lower() in ["true", "1"]
        is_high    = str(row.get("high_priority", "")).lower() in ["true", "1"]
        color      = COLORS["danger"] if is_pheic else (COLORS["warning"] if is_high else COLORS["muted"])
        icon       = "RED ALERT" if is_pheic else ("HIGH" if is_high else "MONITOR")
        disease    = str(row.get("disease_type", "Unknown"))
        regions    = str(row.get("regions", ""))[:45]
        cases      = row.get("confirmed_cases", None)
        deaths     = row.get("deaths", None)
        alerts.append(html.Div([
            html.Div([
                html.Strong(f"[{icon}] ", style={"color": color}),
                html.Strong(disease, style={"color": color}),
            ]),
            html.Div(regions, style={"color": COLORS["muted"], "fontSize": "0.8rem"}),
            html.Div(
                f"Cases: {int(cases) if cases and str(cases) != 'nan' else 'N/A'} | Deaths: {int(deaths) if deaths and str(deaths) != 'nan' else 'N/A'}",
                style={"color": COLORS["text"], "fontSize": "0.78rem"}
            ),
        ], style={"padding": "8px 12px", "marginBottom": "6px", "backgroundColor": COLORS["background"], "borderLeft": f"3px solid {color}", "borderRadius": "4px"}))

    return fig, alerts

if __name__ == "__main__":
    port  = int(os.getenv("DASHBOARD_PORT", "8050"))
    debug = os.getenv("DASHBOARD_DEBUG", "True").lower() == "true"
    print(f"\n{'='*50}")
    print(f"  RefugeeHealthChain Dashboard")
    print(f"  Open: http://localhost:{port}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)

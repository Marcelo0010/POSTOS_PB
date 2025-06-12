# app.py
import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
import numpy as np
from dash import Dash, html, dcc, dash_table
import plotly.express as px
import base64
from branca.element import MacroElement
from jinja2 import Template
import dash_bootstrap_components as dbc
from folium.plugins import MarkerCluster
import os

# === Criar pasta 'assets' se ela não existir ===
os.makedirs("assets", exist_ok=True)
# === Função para conversão de coordenadas ===
def dms_to_decimal(dms):
    try:
        if pd.isna(dms):
            return np.nan
        dms = dms.replace(",", ".")
        parts = dms.split(":")
        if len(parts) == 3:
            degrees = float(parts[0])
            minutes = float(parts[1]) / 60
            seconds = float(parts[2]) / 3600
            decimal = abs(degrees) + minutes + seconds
            return -decimal if degrees < 0 else decimal
        return np.nan
    except:
        return np.nan

# === Leitura dos dados ===
df = pd.read_excel("base1.xlsx", sheet_name="Folha1")
df["LATITUDE"] = df["LATITUDE"].apply(dms_to_decimal)
df["LONGITUDE"] = df["LONGITUDE"].apply(dms_to_decimal)
df = df.dropna(subset=["LATITUDE", "LONGITUDE"])
df.rename(columns={"MUNICÍPIO": "Municipio"}, inplace=True)

# === Estatísticas ===
postos_unicos = df.drop_duplicates(subset=["CNPJ"])
total_postos_unicos = len(postos_unicos)
tancagem_total_geral = df["Tancagem (m³)"].sum()
tancagem_por_produto = df.groupby("Produto")["Tancagem (m³)"].sum().reset_index()
tancagem_por_mun_prod = df.groupby(["Municipio", "Produto"])["Tancagem (m³)"].sum().reset_index()

# === Gráficos ===
graf_tancagem_produto = px.bar(tancagem_por_produto, x="Produto", y="Tancagem (m³)", title="Tancagem por Produto")
graf_tancagem_mun = px.bar(tancagem_por_mun_prod, x="Municipio", y="Tancagem (m³)", color="Produto",
                             title="Tancagem por Produto e Município")

# === Tabela lateral ===
tabela_tancagem = dash_table.DataTable(
    columns=[{"name": i, "id": i} for i in tancagem_por_mun_prod.columns],
    data=tancagem_por_mun_prod.to_dict("records"),
    style_table={"overflowX": "auto", "height": "400px", "overflowY": "auto"},
    style_cell={"textAlign": "left"},
)

# === Mapa interativo com camadas ===
m1 = folium.Map(location=[df["LATITUDE"].mean(), df["LONGITUDE"].mean()], zoom_start=8)
cores = ["green","red", "gray", "orange", "purple", "black", "blue", "pink", "cadetblue"]
produtos_unicos = df["Produto"].dropna().unique()
cores_produto = {produto: cores[i % len(cores)] for i, produto in enumerate(produtos_unicos)}

for produto in produtos_unicos:
    camada = folium.FeatureGroup(name=f"Postos - {produto}", show=True)
    df_filtrado = df[df["Produto"] == produto]
    for _, row in df_filtrado.iterrows():
        popup = f"<b>{row['Razão Social']}</b><br>Produto: {produto}<br>Tancagem: {row['Tancagem (m³)']} m³"
        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=max(5, row["Tancagem (m³)"] / 500),
            popup=folium.Popup(popup, max_width=300),
            color=cores_produto[produto],
            fill=True,
            fill_color=cores_produto[produto],
            fill_opacity=0.7,
        ).add_to(camada)
    m1.add_child(camada)

folium.LayerControl(collapsed=False).add_to(m1)
m1.save("assets/mapa_postos_usinas.html")

# === Mapa com clusters ===
m2 = folium.Map(location=[df["LATITUDE"].mean(), df["LONGITUDE"].mean()], zoom_start=8)
cluster = MarkerCluster().add_to(m2)
for _, row in df.iterrows():
    folium.Marker(
        location=[row["LATITUDE"], row["LONGITUDE"]],
        popup=row["Razão Social"],
        icon=folium.Icon(color="blue")
    ).add_to(cluster)
m2.save("assets/mapa_simples.html")

# === App DASH ===
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Painel de Tancagem - Paraíba"

app.layout = html.Div(style={"backgroundColor": "#e0f2e9", "padding": "20px"}, children=[
    html.H1("Painel de Tancagem e Localização de Postos na Paraíba", 
            style={"textAlign": "center", "color": "#004d40", "fontWeight": "bold", "fontSize": "36px"}),

    html.P("Este dashboard interativo mostra a distribuição dos tanques de combustível nos postos do estado da Paraíba, incluindo estatísticas por produto e por município, bem como a localização exata dos estabelecimentos. ",
           style={"textAlign": "center", "fontSize": "18px"}),

    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Total de Postos", className="card-title"),
                html.H2(f"{total_postos_unicos}", style={"color": "#2e7d32"})
            ])
        ], color="success", inverse=True), width=6),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Tancagem Total (m³)", className="card-title"),
                html.H2(f"{int(tancagem_total_geral):,}".replace(",", "."), style={"color": "#2e7d32"})
            ])
        ], color="success", inverse=True), width=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(figure=graf_tancagem_produto), width=6),
        dbc.Col(dcc.Graph(figure=graf_tancagem_mun), width=6),
    ]),

    html.H4("Tabela de Tancagem por Produto e Município", style={"marginTop": "30px", "color": "#004d40"}),
    tabela_tancagem,

    html.Hr(),
    html.H4("Mapa Interativo por Produto (com Camadas)", style={"marginTop": "20px", "color": "#004d40"}),
    html.Iframe(src="/assets/mapa_postos_usinas.html", width="100%", height="500"),

    html.H4("Mapa com Cluster de Postos", style={"marginTop": "30px", "color": "#004d40"}),
    html.Iframe(src="/assets/mapa_simples.html", width="100%", height="500"),
])

if __name__ == "__main__":
    app.run(debug=True)

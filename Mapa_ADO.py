import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

st.set_page_config(page_title="Mapa de ADO por Cidade", page_icon="⭐", layout="wide")

st.title("⭐ Mapa de ADO por Cidade (Rápido)")
st.markdown("Selecione um estado e/ou cidade para visualizar os dados. Não há fundo de mapa, apenas o contorno do Brasil, para máxima velocidade.")

@st.cache_data(ttl=600)
def load_data_from_private_sheet():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet_conf = st.secrets["google_sheet"]
        spreadsheet = client.open_by_key(sheet_conf["sheet_id"])
        worksheet = spreadsheet.worksheet(sheet_conf["sheet_name"])
        data = pd.DataFrame(worksheet.get_all_records())
        for col in ["latitude", "longitude", "ADO"]:
            data[col] = pd.to_numeric(
                data[col].astype(str).str.replace(",", "."),
                errors='coerce'
            )
        data.dropna(
            subset=['latitude', 'longitude', 'ADO', 'min buyer_city', 'min buyer_state'],
            inplace=True
        )
        return data
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        return pd.DataFrame()

sheet_data = load_data_from_private_sheet()

if sheet_data.empty:
    st.warning("Nenhum dado carregado. Verifique os segredos e a planilha.")
else:
    st.success(f"{len(sheet_data)} cidades carregadas com sucesso!")

    # Filtro por Estado
    estados = sorted(sheet_data['min buyer_state'].unique())
    estado_selecionado = st.sidebar.selectbox("Selecione o estado:", ["Todos"] + estados)

    if estado_selecionado != "Todos":
        df_estado = sheet_data[sheet_data['min buyer_state'] == estado_selecionado]
    else:
        df_estado = sheet_data

    # Filtro por Cidade (opcional)
    cidades = sorted(df_estado['min buyer_city'].unique())
    cidade_selecionada = st.sidebar.selectbox("Selecione a cidade:", ["Todas"] + cidades)

    if cidade_selecionada != "Todas":
        df = df_estado[df_estado['min buyer_city'] == cidade_selecionada]
    else:
        df = df_estado

    # Paleta de cor baseada no ADO
    def get_cor(ado):
        if ado <= 20:
            return "red"
        elif ado <= 50:
            return "orange"
        elif ado <= 100:
            return "gray"
        else:
            return "green"

    df["cor"] = df["ADO"].apply(get_cor)

    fig = px.scatter_geo(
        df,
        lat="latitude",
        lon="longitude",
        color="cor",
        hover_name="min buyer_city",
        hover_data={"ADO": True, "latitude": False, "longitude": False, "cor": False},
        scope="south america",
        center={"lat": -14.2, "lon": -51.9},
        fitbounds="locations",
        size_max=10,
    )
    fig.update_traces(marker=dict(size=7, opacity=0.7, line=dict(width=0)))
    fig.update_geos(
        showcountries=True, countrycolor="White",
        lataxis_range=[-34, 5], lonaxis_range=[-75, -34], # Recorte Brasil
        showland=True, landcolor="#222"
    )
    fig.update_layout(
        height=700,
        margin={"r":0,"t":30,"l":0,"b":0},
        showlegend=False,
        geo_bgcolor="#222"
    )

    st.plotly_chart(fig, use_container_width=True)

    if st.sidebar.checkbox("Mostrar tabela"):
        st.sidebar.dataframe(df[['min buyer_city', 'ADO', 'min buyer_state', 'latitude', 'longitude']])

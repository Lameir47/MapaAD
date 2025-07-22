import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium

# ================= Layout Customizado ==================
st.markdown(
    """
    <style>
    .main, .stApp {background-color: #E9EBED;}
    section[data-testid="stSidebar"] {
        background-color: #D3422A !important;
    }
    section[data-testid="stSidebar"] * {
        color: #111 !important;
    }
    /* Força campos selectbox e legendas a caberem e serem legíveis */
    .stSelectbox > div[data-baseweb="select"] {
        font-size: 15px !important;
        min-width: 0 !important;
        max-width: 95% !important;
    }
    /* Ajusta largura para a barra lateral não "explodir" */
    .st-emotion-cache-1cypcdb {max-width: 95vw !important;}
    /* Ajusta botões e checkboxes */
    .st-c8, .st-c9, .stCheckbox {background: transparent !important;}
    .st-bx {background: #fff !important;color: #111 !important;}
    div[data-testid="stVerticalBlock"] > div:has(.folium-map) {max-width: 100vw !important;width: 100vw !important;margin-left: -4vw !important;}
    .folium-map, .stMarkdown, .stPlotlyChart, .stDataFrame, .element-container {width: 100vw !important;min-width: 100vw !important;}
    /* Legenda horizontal - área principal */
    .cor-legenda {display: inline-block; width: 16px; height: 16px; border-radius: 50%; margin: 0 8px 0 16px; vertical-align: middle; border:1.5px solid #888;}
    .label-legenda {margin-right: 18px; font-weight: 500; font-size: 15px; vertical-align: middle; color: #111 !important;}
    </style>
    """, unsafe_allow_html=True)
# ======================================================

st.set_page_config(page_title="Mapa de ADO por Cidade", page_icon="⭐", layout="wide")

st.title("⭐ Mapa de ADO por Cidade")
st.markdown("Selecione um estado e/ou XPT para visualizar os dados do estado no mapa. O carregamento é mais rápido ao focar em estados ou XPT específicos.")

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
            subset=['latitude', 'longitude', 'ADO', 'min buyer_city', 'min buyer_state', 'Atendimento XPT', 'CEP Atendido', 'Station Name'],
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

    # Filtro por Estado (pré-selecionado em São Paulo, se existir)
    estados = sorted(sheet_data['min buyer_state'].unique())
    default_estado = "São Paulo" if "São Paulo" in estados else estados[0]
    estado_selecionado = st.sidebar.selectbox("Selecione o estado:", ["Todos"] + estados, index=(estados.index(default_estado)+1) if default_estado in estados else 0)
    if estado_selecionado != "Todos":
        df = sheet_data[sheet_data['min buyer_state'] == estado_selecionado].copy()
    else:
        df = sheet_data.copy()

    # Filtro por Station Name (XPT)
    xpt_options = (
        df[df['Station Name'].str.strip().str.upper() != 'N/A']['Station Name']
        .dropna().sort_values().unique().tolist()
    )
    xpt_options_full = (
        sheet_data[sheet_data['Station Name'].str.strip().str.upper() != 'N/A']['Station Name']
        .dropna().sort_values().unique().tolist()
    )
    if estado_selecionado == "Todos":
        xpt_select_list = xpt_options_full
    else:
        xpt_select_list = xpt_options
    xpt_select_list = ["(Todos)"] + xpt_select_list
    selected_xpt = st.sidebar.selectbox("Selecione o XPT", xpt_select_list)
    limpar = st.sidebar.button("Limpar")

    # Lógica do filtro de XPT
    if selected_xpt != "(Todos)" and not limpar:
        df['destaque_xpt'] = df['Station Name'] == selected_xpt
    else:
        df['destaque_xpt'] = False
        if limpar:
            selected_xpt = "(Todos)"

    # LEGENDA NA ÁREA PRINCIPAL COMO ERA ANTES (com círculos coloridos, horizontal)
    st.markdown(
        """
        <div style='padding:7px 0 12px 0; white-space:nowrap;'>
        <span class='cor-legenda' style='background:#AD63D4;'></span><span class='label-legenda'>XPT Selecionado</span>
        <span class='cor-legenda' style='background:#78c878;'></span><span class='label-legenda'>Cidades Atendidas</span>
        <span class='cor-legenda' style='background:yellow;'></span><span class='label-legenda'>ADO ≥ 100</span>
        <span class='cor-legenda' style='background:#ff6464;'></span><span class='label-legenda'>0 a 20</span>
        <span class='cor-legenda' style='background:#ffa564;'></span><span class='label-legenda'>21 a 50</span>
        <span class='cor-legenda' style='background:#b4b4b4;'></span><span class='label-legenda'>51 a 99</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if df.empty:
        st.warning("Nenhuma cidade encontrada para esse estado/XPT.")
    else:
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        zoom = 6 if len(df) > 1 else 10

        def get_color(row):
            if row['destaque_xpt']:
                return '#AD63D4'  # lilás destaque
            if str(row['CEP Atendido']).strip() == "Sim":
                return '#78c878'  # verde claro
            if row['ADO'] >= 100:
                return 'yellow'
            elif row['ADO'] <= 20:
                return 'red'
            elif row['ADO'] <= 50:
                return 'orange'
            elif row['ADO'] < 100:
                return 'lightgray'
            return 'gray'

        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="Cartodb Positron")
        for _, row in df.iterrows():
            tamanho = 6.5 if row['destaque_xpt'] else 5
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=tamanho,
                color=get_color(row),
                fill=True,
                fill_color=get_color(row),
                fill_opacity=0.8,
                popup=f"<b>Cidade:</b> {row['min buyer_city']}<br/><b>ADO:</b> {row['ADO']}<br/><b>Atend. XPT:</b> {row['Atendimento XPT']}<br/><b>XPT:</b> {row['Station Name']}"
            ).add_to(m)
        st_folium(m, width=1900, height=700)

        if st.sidebar.checkbox("Mostrar tabela"):
            st.sidebar.subheader("Dados")
            st.sidebar.dataframe(df[['min buyer_city', 'ADO', 'min buyer_state', 'latitude', 'longitude', 'Atendimento XPT', 'CEP Atendido', 'Station Name', 'destaque_xpt']])

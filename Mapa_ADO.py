import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
import geopandas as gpd

# --- Configuração da Página ---
st.set_page_config(
    page_title="Mapa de Cidades (ADO)",
    page_icon="🗺️",
    layout="wide"
)

# --- Título do Aplicativo ---
st.title("🗺️ Mapa Interativo de Cidades por ADO")
st.markdown("Passe o mouse sobre uma cidade para ver os detalhes. As fronteiras são exibidas no mapa.")

# --- Constantes e URLs ---
GEOJSON_URL = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-mun.json"

# --- Funções de Carregamento de Dados (com Cache) ---

@st.cache_data(ttl=3600) # Cache por 1 hora
def load_geojson(url):
    """Carrega os dados das fronteiras e simplifica as geometrias para melhor performance."""
    try:
        gdf = gpd.read_file(url)
        gdf = gdf.rename(columns={'id': 'code_muni'})
        gdf['code_muni'] = pd.to_numeric(gdf['code_muni'], errors='coerce')
        gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.005)
        return gdf
    except Exception as e:
        st.error(f"Não foi possível carregar os dados de fronteiras (GeoJSON): {e}")
        return None

@st.cache_data(ttl=600) # Cache por 10 minutos
def load_data_from_private_sheet():
    """Autentica e carrega os dados da planilha privada do Google Sheets."""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(st.secrets["google_sheet"]["sheet_id"])
        worksheet = spreadsheet.worksheet(st.secrets["google_sheet"]["sheet_name"])
        data = pd.DataFrame(worksheet.get_all_records())
        data['ADO'] = pd.to_numeric(data['ADO'], errors='coerce')
        data['min CITY_ID_IBGE'] = pd.to_numeric(data['min CITY_ID_IBGE'], errors='coerce')
        data.dropna(subset=['min CITY_ID_IBGE', 'ADO'], inplace=True)
        data['min CITY_ID_IBGE'] = data['min CITY_ID_IBGE'].astype(int)
        return data
    except Exception as e:
        st.error("Ocorreu um erro ao acessar a planilha.")
        st.exception(e)
        return pd.DataFrame()

# --- Função de Geração do Mapa (sem cache para manter a interatividade) ---
def create_map(data):
    """Cria e retorna o objeto do mapa Folium."""
    map_center = [-14.2350, -51.9253]
    m = folium.Map(location=map_center, zoom_start=4, tiles="cartodbpositron")

    geojson_layer = folium.GeoJson(
        data,
        style_function=lambda feature: {
            'fillColor': '#3186cc',
            'color': 'transparent',
            'weight': 0,
            'fillOpacity': 0.0,
        },
        highlight_function=lambda x: {
            'fillColor': '#3186cc',
            'color': 'yellow',
            'weight': 3,
            'fillOpacity': 0.6,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['buyer_city', 'ADO'],
            aliases=['Cidade:', 'ADO:'],
            localize=True,
            sticky=False,
            style="""
                background-color: #F0EFEF;
                color: #333333;
                border: 1px solid black;
                border-radius: 3px;
                box-shadow: 3px;
            """
        )
    )
    geojson_layer.add_to(m)
    return m

# --- Lógica Principal do Aplicativo ---

geojson_data = load_geojson(GEOJSON_URL)
sheet_data = load_data_from_private_sheet()

if geojson_data is not None and not sheet_data.empty:
    merged_data = geojson_data.merge(
        sheet_data,
        left_on='code_muni',
        right_on='min CITY_ID_IBGE',
        how='inner'
    )

    if not merged_data.empty:
        st.success(f"{len(merged_data)} cidades da sua planilha foram encontradas com sucesso nos dados de fronteiras!")

        # Chama a função que cria o mapa
        folium_map = create_map(merged_data)

        # Exibe o mapa no Streamlit
        st_folium(folium_map, use_container_width=True, height=700)

        if st.checkbox("Mostrar dados da tabela (após junção com fronteiras)"):
            st.subheader("Dados Combinados")
            st.dataframe(merged_data[['buyer_city', 'min buyer_state', 'ADO', 'code_muni']])

    else:
        st.warning("Nenhuma cidade correspondente encontrada entre a planilha e os dados de fronteiras. Verifique se os códigos IBGE ('min CITY_ID_IBGE') estão corretos.")
else:
    st.warning("Não foi possível carregar os dados necessários para exibir o mapa.")

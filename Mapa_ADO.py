import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pydeck as pdk

# --- Configuração da Página ---
st.set_page_config(
    page_title="Mapa de Cidades (ADO)",
    page_icon="⭐",
    layout="wide"
)

# --- Configuração do Mapbox (Token obrigatório no Streamlit Cloud Secrets) ---
# Adicione nos Secrets: mapbox_token = "SEU_MAPBOX_TOKEN"
pdk.settings.mapbox_api_key = st.secrets.get("mapbox_token", "")

# --- Título do Aplicativo ---
st.title("⭐ Mapa de ADO por Cidade")
st.markdown(
    "Passe o mouse sobre um ponto para ver os detalhes ou use o filtro na barra lateral para focar em uma cidade específica."
)

# --- Legenda de Cores ---
st.markdown(
    """
### Legenda das Cores
- <span style='color:#ff6464;'>**0 a 20** → Vermelho claro</span>  
- <span style='color:#ffa564;'>**21 a 50** → Laranja claro</span>  
- <span style='color:#b4b4b4;'>**51 a 100** → Cinza claro</span>  
- <span style='color:#78c878;'>**Acima de 100** → Verde claro</span>
""",
    unsafe_allow_html=True
)

# --- Carregamento de Dados com Google Sheets ---
@st.cache_data(ttl=600)
def load_data_from_private_sheet():
    """Autentica e carrega os dados do Google Sheets. Fica em cache por 10 minutos."""
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
        # Converte colunas numéricas
        for col in ["latitude", "longitude", "ADO"]:
            data[col] = pd.to_numeric(
                data[col].astype(str).str.replace(",", "."),
                errors='coerce'
            )
        # Remove linhas sem dados essenciais
        data.dropna(
            subset=['latitude', 'longitude', 'ADO', 'min buyer_city'],
            inplace=True
        )
        return data
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        return pd.DataFrame()

# --- Lógica Principal ---
sheet_data = load_data_from_private_sheet()

if sheet_data.empty:
    st.warning("Nenhum dado carregado. Verifique os segredos e a planilha.")
else:
    st.success(f"{len(sheet_data)} cidades carregadas com sucesso!")

    # Filtro na barra lateral
    st.sidebar.header("Filtros do Mapa")
    cities = sorted(sheet_data['min buyer_city'].unique())
    cities.insert(0, "Ver todas as cidades")
    selected_city = st.sidebar.selectbox(
        "Selecione uma cidade:", cities
    )

    # Define dados e visualização
    if selected_city != "Ver todas as cidades":
        df = sheet_data[sheet_data['min buyer_city'] == selected_city].copy()
        center_lat = df.iloc[0]['latitude']
        center_lon = df.iloc[0]['longitude']
        zoom = 10
    else:
        df = sheet_data.copy()
        center_lat, center_lon, zoom = -14.2350, -51.9253, 4

    # Define cores por faixa de ADO
    def get_color(a):
        if a <= 20:
            return [255, 100, 100, 180]
        if a <= 50:
            return [255, 165, 100, 180]
        if a <= 100:
            return [180, 180, 180, 180]
        return [120, 200, 120, 180]

    df['color'] = df['ADO'].apply(get_color)

    # Monta camada PyDeck
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        pickable=True,
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius=8000
    )

    view = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0
    )

    tooltip = {
        "html": (
            "<b>Cidade:</b> {min buyer_city}<br/>"  
            "<b>ADO:</b> {ADO}"
        ),
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    # Exibe o mapa online
st.pydeck_chart(
    pdk.Deck(
        # Usa o token definido em pdk.settings.mapbox_api_key
        map_style='mapbox://styles/mapbox/dark-v10',
        initial_view_state=view,
        layers=[layer],
        tooltip=tooltip
    ),
    height=700
)



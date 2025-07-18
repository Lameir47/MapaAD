import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Mapa de ADO por Cidade", page_icon="⭐", layout="wide")

st.title("⭐ Mapa de ADO por Cidade")
st.markdown("Selecione um estado para visualizar os dados do estado no mapa. O carregamento é mais rápido ao focar em estados específicos.")

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
    estado_selecionado = st.sidebar.selectbox("Selecione o estado:", estados)

    df = sheet_data[sheet_data['min buyer_state'] == estado_selecionado].copy()

    if df.empty:
        st.warning("Nenhuma cidade encontrada para esse estado.")
    else:
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        zoom = 6 if len(df) > 1 else 10

        def get_color(ado):
            if ado <= 20:
                return 'red'
            elif ado <= 50:
                return 'orange'
            elif ado <= 100:
                return 'lightgray'
            return 'green'

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

        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB dark_matter")

        # Adiciona todos os pontos individualmente (sem cluster)
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=5,
                color=get_color(row["ADO"]),
                fill=True,
                fill_color=get_color(row["ADO"]),
                fill_opacity=0.8,
                popup=f"<b>Cidade:</b> {row['min buyer_city']}<br/><b>ADO:</b> {row['ADO']}"
            ).add_to(m)

        st_folium(m, width=1000, height=700)

        if st.sidebar.checkbox("Mostrar tabela"):
            st.sidebar.subheader("Dados")
            st.sidebar.dataframe(df[['min buyer_city', 'ADO', 'min buyer_state', 'latitude', 'longitude']])

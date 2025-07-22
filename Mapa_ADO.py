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

# NOVA LÓGICA DO FILTRO DE XPT
if selected_xpt != "(Todos)" and not limpar:
    # Pegue todos os pontos desse XPT independente do estado
    xpt_df = sheet_data[sheet_data['Station Name'] == selected_xpt].copy()
    xpt_df['destaque_xpt'] = True
    # Pegue todos do estado selecionado que não têm esse XPT (ou todos se "Todos")
    if estado_selecionado != "Todos":
        outros_df = df[df['Station Name'] != selected_xpt].copy()
    else:
        outros_df = sheet_data[(sheet_data['Station Name'] != selected_xpt)].copy()
    outros_df['destaque_xpt'] = False
    # O df final: sempre pontos do estado + pontos do XPT mesmo que de outro estado (sem duplicar)
    # Para não duplicar pontos do XPT que já existem no estado:
    xpt_nao_no_estado = xpt_df[~xpt_df.index.isin(outros_df.index)]
    df = pd.concat([outros_df, xpt_nao_no_estado], ignore_index=True)
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

import streamlit as st
import pandas as pd
import urllib.parse

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL (MOBILE FIRST)
# ==============================================================================
st.set_page_config(page_title="Radar Almenara", page_icon="🕵️", layout="centered")

# CSS para botões grandes, cards bonitos e remoção de espaços extras
st.markdown("""
    <style>
    .stButton button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: 600;
    }
    div.block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CARREGAMENTO E LIMPEZA
# ==============================================================================
@st.cache_data
def load_data():
    try:
        # Carrega o Excel
        df = pd.read_excel("Leads_Almenara_GPS.xlsx")
        
        # Garante que tudo é texto para não dar erro
        df['telefone_completo'] = df['telefone_completo'].astype(str)
        df['endereco_completo'] = df['endereco_completo'].astype(str)
        df['bairro'] = df['bairro'].fillna("Não informado")
        
        # Tratamento do MEI (Preenche vazios com 0)
        if 'opcao_mei' in df.columns:
            df['opcao_mei'] = df['opcao_mei'].fillna(0).astype(int)
        else:
            df['opcao_mei'] = 0 
            
    except Exception as e:
        return None
    return df

df = load_data()

# ==============================================================================
# 3. INTERFACE DO APP
# ==============================================================================
st.title("🕵️ Radar de Vendas")
st.caption("Almenara & Vale do Jequitinhonha")

if df is not None and not df.empty:
    
    # --- A. FILTROS (No topo) ---
    with st.expander("🔍 Filtrar Lista", expanded=False):
        cidades = ["Todas"] + sorted(list(df['municipio_nome'].unique()))
        cidade_sel = st.selectbox("Cidade:", cidades)
        
        # Filtro de bairro dinâmico
        if cidade_sel != "Todas":
            bairros_cidade = df[df['municipio_nome'] == cidade_sel]['bairro'].unique()
            bairros = ["Todos"] + sorted([b for b in bairros_cidade if b != "Não informado"])
        else:
            bairros = ["Todos"]
            
        bairro_sel = st.selectbox("Bairro:", bairros)
        score_min = st.slider("Qualidade (Score):", 0, 10, 3)

    # --- B. APLICAÇÃO DOS FILTROS ---
    df_filtered = df[df['Score'] >= score_min]
    if cidade_sel != "Todas":
        df_filtered = df_filtered[df_filtered['municipio_nome'] == cidade_sel]
    if bairro_sel != "Todos":
        df_filtered = df_filtered[df_filtered['bairro'] == bairro_sel]

    # Mostra total encontrado
    st.markdown(f"**{len(df_filtered)}** empresas encontradas")
    st.markdown("---")

    # ==========================================================================
    # 4. LÓGICA DE PAGINAÇÃO (NOVO!)
    # ==========================================================================
    
    # Define quantos cards aparecem por página
    ITENS_POR_PAGINA = 10 
    
    # Inicializa a variável de página na memória
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 0

    # Calcula totais
    total_empresas = len(df_filtered)
    # Cálculo de total de páginas (arredondando para cima)
    total_paginas = (total_empresas // ITENS_POR_PAGINA) + (1 if total_empresas % ITENS_POR_PAGINA > 0 else 0)
    
    # Se o filtro mudou e a página atual não existe mais, volta para a zero
    if st.session_state.pagina_atual >= total_paginas:
        st.session_state.pagina_atual = 0

    # Define onde começa e termina o corte (slice) do dataframe
    inicio = st.session_state.pagina_atual * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    
    # Cria o sub-dataframe apenas com as empresas da página atual
    batch_empresas = df_filtered.iloc[inicio:fim]

    # Texto informativo (Ex: Página 1 de 5)
    if total_empresas > 0:
        st.caption(f"Página {st.session_state.pagina_atual + 1} de {total_paginas}")

    # ==========================================================================
    # 5. LOOP DOS CARDS
    # ==========================================================================
    
    for index, row in batch_empresas.iterrows():
        
        # Definições visuais
        eh_mei = row['opcao_mei'] == 1
        
        if eh_mei:
            status_txt = "Microempreendedor (MEI)"
            status_icon = "👤"
            cor_status = "orange"
        else:
            status_txt = "Empresa Padrão (ME/EPP)"
            status_icon = "🏢" 
            cor_status = "green"

        fire = "🔥" * int(row['Score'] - 2) if row['Score'] > 2 else "🌱"

        # Dados
        nome = row['nome_fantasia']
        dono = row['socios_nomes'] if pd.notnull(row['socios_nomes']) else "Sócio não identificado"
        capital = f"R$ {row['capital_social']:,.0f}".replace(",", ".")
        
        # Endereço
        end_raw = str(row['endereco_completo'])
        tem_endereco_valido = len(end_raw) > 10 and 'None' not in end_raw and 'nan' not in end_raw

        # --- O CARD ---
        with st.expander(f"{status_icon} {nome} {fire}"):
            
            st.markdown(f"**Dono:** {dono}")
            st.markdown(f"**Porte:** :{cor_status}[{status_txt}]")
            st.markdown(f"**Capital:** {capital}")
            
            if tem_endereco_valido:
                st.info(f"📍 {end_raw}")
            else:
                st.warning("⚠️ Endereço incompleto na Receita Federal")

            col1, col2 = st.columns(2)
            
            # Botão GPS
            with col1:
                if tem_endereco_valido:
                    end_encoded = urllib.parse.quote(end_raw)
                    link_maps = f"https://www.google.com/maps/search/?api=1&query={end_encoded}"
                    st.link_button("📍 Ir p/ Local", link_maps)
                else:
                    # Key única usando index para evitar erro
                    st.button("🚫 Sem GPS", disabled=True, key=f"btn_gps_{index}")

            # Botão Contato
            with col2:
                telefones = str(row['telefone_completo']).split(',')
                tem_zap = False
                
                for tel in telefones:
                    tel_clean = tel.strip().replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                    if "9" in tel and len(tel_clean) >= 10:
                        link_zap = f"https://wa.me/55{tel_clean}"
                        st.link_button("🟢 WhatsApp", link_zap)
                        tem_zap = True
                        break 
                
                if not tem_zap:
                    # Key única usando index para evitar erro (CORREÇÃO APLICADA AQUI)
                    st.button("📞 Só Fixo", disabled=True, help=f"Tente ligar: {telefones[0]}", key=f"btn_fixo_{index}")

    # ==========================================================================
    # 6. RODAPÉ COM NAVEGAÇÃO
    # ==========================================================================
    st.markdown("---")
    
    # Só mostra navegação se tiver mais de uma página
    if total_paginas > 1:
        col_prev, col_msg, col_next = st.columns([1, 2, 1])

        with col_prev:
            if st.session_state.pagina_atual > 0:
                if st.button("⬅️ Anterior"):
                    st.session_state.pagina_atual -= 1
                    st.rerun()

        with col_next:
            if st.session_state.pagina_atual < total_paginas - 1:
                if st.button("Próxima ➡️"):
                    st.session_state.pagina_atual += 1
                    st.rerun()

else:
    st.error("⚠️ Arquivo Excel não encontrado ou vazio.")
    st.info("Certifique-se que o arquivo 'Leads_Almenara_GPS.xlsx' está na mesma pasta.")

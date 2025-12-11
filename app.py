import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px  # <--- NOVA BIBLIOTECA PARA O GRÁFICO

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL (MOBILE FIRST)
# ==============================================================================
st.set_page_config(page_title="Radar Almenara", page_icon="🕵️", layout="centered")

# CSS para interface limpa
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
        df = pd.read_excel("Leads_Almenara_GPS.xlsx")
        
        # Converte colunas para texto
        cols_text = ['telefone_completo', 'endereco_completo', 'nome_fantasia', 'cnae_fiscal_descricao']
        for col in cols_text:
            if col in df.columns:
                df[col] = df[col].astype(str)
            else:
                df[col] = "" # Cria vazia se não existir
        
        df['bairro'] = df['bairro'].fillna("Não informado")
        
        if 'opcao_mei' in df.columns:
            df['opcao_mei'] = df['opcao_mei'].fillna(0).astype(int)
        else:
            df['opcao_mei'] = 0 
            
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None
    return df

df = load_data()

# ==============================================================================
# 3. FUNÇÃO INTELIGENTE DE CLASSIFICAÇÃO (NOVO!)
# ==============================================================================
def classificar_setor(row):
    # Junta nome e descrição da atividade para procurar palavras-chave
    texto = (str(row['nome_fantasia']) + " " + str(row.get('cnae_fiscal_descricao', ''))).lower()
    
    if any(x in texto for x in ['fazenda', 'sítio', 'agro', 'rural', 'gado', 'criacao', 'plantio', 'soja', 'milho', 'café']):
        return '🚜 Agro & Rural'
    elif any(x in texto for x in ['comércio', 'varejo', 'loja', 'mercado', 'bazar', 'modas', 'roupas', 'calçados', 'supermercado']):
        return '🛍️ Varejo'
    elif any(x in texto for x in ['serviço', 'consultoria', 'manutenção', 'transporte', 'advoca', 'clínica', 'estética', 'beleza', 'oficina']):
        return '🛠️ Serviços'
    elif any(x in texto for x in ['indústria', 'confecção', 'fabricação', 'metal', 'móveis']):
        return '🏭 Indústria'
    elif any(x in texto for x in ['alimentação', 'restaurante', 'bar', 'lanchonete', 'pizzaria']):
        return '🍔 Alimentação'
    else:
        return '🏢 Outros'

# ==============================================================================
# 4. INTERFACE DO APP
# ==============================================================================
st.title("🕵️ Radar de Vendas")
st.caption("Almenara & Vale do Jequitinhonha")

if df is not None and not df.empty:
    
    # --- A. FILTROS ---
    with st.expander("🔍 Filtrar Lista", expanded=False):
        cidades = ["Todas"] + sorted(list(df['municipio_nome'].unique()))
        cidade_sel = st.selectbox("Cidade:", cidades)
        
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

    # --- C. DASHBOARD GRÁFICO (NOVO!) ---
    if not df_filtered.empty:
        # Aplica a classificação
        df_filtered['Setor'] = df_filtered.apply(classificar_setor, axis=1)
        
        # Conta quantos tem em cada setor
        contagem_setores = df_filtered['Setor'].value_counts().reset_index()
        contagem_setores.columns = ['Setor', 'Quantidade']
        
        st.markdown("### 📊 Raio-X do Mercado")
        
        col_graf, col_kpi = st.columns([1.5, 1])
        
        with col_graf:
            # Gráfico de Rosca (Donut Chart)
            fig = px.pie(contagem_setores, values='Quantidade', names='Setor', hole=0.4)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_kpi:
            # Mostra o top setor em destaque
            top_setor = contagem_setores.iloc[0]['Setor']
            top_qtd = contagem_setores.iloc[0]['Quantidade']
            st.metric("Total Listado", len(df_filtered))
            st.metric("Setor Dominante", top_setor, f"{top_qtd} empresas")

    st.markdown("---")

    # ==========================================================================
    # 5. PAGINAÇÃO E LOOP
    # ==========================================================================
    ITENS_POR_PAGINA = 10 
    
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 0

    total_empresas = len(df_filtered)
    total_paginas = (total_empresas // ITENS_POR_PAGINA) + (1 if total_empresas % ITENS_POR_PAGINA > 0 else 0)
    
    if st.session_state.pagina_atual >= total_paginas:
        st.session_state.pagina_atual = 0

    inicio = st.session_state.pagina_atual * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    batch_empresas = df_filtered.iloc[inicio:fim]

    if total_empresas > 0:
        st.caption(f"Página {st.session_state.pagina_atual + 1} de {total_paginas}")

    # --- LOOP DOS CARDS ---
    for index, row in batch_empresas.iterrows():
        
        eh_mei = row['opcao_mei'] == 1
        
        # Tags Visuais
        setor_tag = row['Setor'] # Pega o setor que calculamos agora pouco
        
        if eh_mei:
            status_txt = "MEI"
            status_icon = "👤"
            cor_status = "orange"
        else:
            status_txt = "ME/EPP"
            status_icon = "🏢" 
            cor_status = "green"

        fire = "🔥" * int(row['Score'] - 2) if row['Score'] > 2 else "🌱"

        nome = row['nome_fantasia']
        dono = row['socios_nomes'] if pd.notnull(row['socios_nomes']) else "Sócio não identificado"
        capital = f"R$ {row['capital_social']:,.0f}".replace(",", ".")
        end_raw = str(row['endereco_completo'])
        tem_endereco_valido = len(end_raw) > 10 and 'None' not in end_raw and 'nan' not in end_raw

        with st.expander(f"{status_icon} {nome} {fire}"):
            
            # Adicionei a Tag do Setor aqui dentro também
            st.markdown(f"**Setor:** {setor_tag} | **Porte:** :{cor_status}[{status_txt}]")
            st.markdown(f"**Dono:** {dono}")
            st.markdown(f"**Capital:** {capital}")
            
            if tem_endereco_valido:
                st.info(f"📍 {end_raw}")
            else:
                st.warning("⚠️ Endereço incompleto")

            col1, col2 = st.columns(2)
            
            with col1:
                if tem_endereco_valido:
                    end_encoded = urllib.parse.quote(end_raw)
                    link_maps = f"https://www.google.com/maps/search/?api=1&query={end_encoded}"
                    st.link_button("📍 Mapa", link_maps)
                else:
                    st.button("🚫 Sem GPS", disabled=True, key=f"btn_gps_{index}")

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
                    st.button("📞 Só Fixo", disabled=True, help=f"Tente ligar: {telefones[0]}", key=f"btn_fixo_{index}")

    # --- RODAPÉ ---
    st.markdown("---")
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

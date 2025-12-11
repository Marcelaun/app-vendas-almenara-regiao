import streamlit as st
import pandas as pd
import urllib.parse

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL (MOBILE FIRST)
# ==============================================================================
st.set_page_config(page_title="Radar Almenara", page_icon="🕵️", layout="centered")

# CSS para botões grandes e cards bonitos
st.markdown("""
    <style>
    .stButton button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: 600;
    }
    .card-container {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CARREGAMENTO E LIMPEZA
# ==============================================================================
@st.cache_data
def load_data():
    try:
        # Tente usar o arquivo mais recente que você gerou (V14 ou V11)
        # Se o nome for diferente, altere aqui!
        df = pd.read_excel("Leads_Almenara_GPS.xlsx")
        
        # Garante que tudo é texto para não dar erro
        df['telefone_completo'] = df['telefone_completo'].astype(str)
        df['endereco_completo'] = df['endereco_completo'].astype(str)
        df['bairro'] = df['bairro'].fillna("Não informado")
        
        # Tratamento do MEI (Preenche vazios com 0)
        if 'opcao_mei' in df.columns:
            df['opcao_mei'] = df['opcao_mei'].fillna(0).astype(int)
        else:
            df['opcao_mei'] = 0 # Assume padrão se não tiver a coluna
            
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
    
    # --- FILTROS (No topo) ---
    with st.expander("🔍 Filtrar Lista", expanded=False):
        cidades = ["Todas"] + sorted(list(df['municipio_nome'].unique()))
        cidade_sel = st.selectbox("Cidade:", cidades)
        
        # Filtro de bairro inteligente
        if cidade_sel != "Todas":
            bairros_cidade = df[df['municipio_nome'] == cidade_sel]['bairro'].unique()
            bairros = ["Todos"] + sorted([b for b in bairros_cidade if b != "Não informado"])
        else:
            bairros = ["Todos"]
            
        bairro_sel = st.selectbox("Bairro:", bairros)
        score_min = st.slider("Qualidade (Score):", 0, 10, 3)

    # --- APLICAÇÃO DOS FILTROS ---
    df_filtered = df[df['Score'] >= score_min]
    if cidade_sel != "Todas":
        df_filtered = df_filtered[df_filtered['municipio_nome'] == cidade_sel]
    if bairro_sel != "Todos":
        df_filtered = df_filtered[df_filtered['bairro'] == bairro_sel]

    st.markdown(f"**{len(df_filtered)}** empresas encontradas")
    st.markdown("---")

    # --- LOOP DOS CARDS (ONDE A MÁGICA ACONTECE) ---
    for index, row in df_filtered.head(50).iterrows():
        
        # A. ÍCONES E DEFNIÇÕES
        eh_mei = row['opcao_mei'] == 1
        
        # Definindo o Status da empresa
        if eh_mei:
            status_txt = "Microempreendedor (MEI)"
            status_icon = "👤"
            cor_status = "orange" # Alerta: Paga menos
        else:
            status_txt = "Empresa Padrão (ME/EPP)"
            status_icon = "🏢" 
            cor_status = "green" # Bom: Paga mais

        # Definindo o Score visual
        fire = "🔥" * int(row['Score'] - 2) if row['Score'] > 2 else "🌱"

        # B. DADOS BÁSICOS
        nome = row['nome_fantasia']
        dono = row['socios_nomes'] if pd.notnull(row['socios_nomes']) else "Sócio não identificado"
        capital = f"R$ {row['capital_social']:,.0f}".replace(",", ".")
        
        # C. LÓGICA DO ENDEREÇO (AQUI ESTÁ O QUE VOCÊ PEDIU!)
        end_raw = str(row['endereco_completo'])
        
        # Verifica se o endereço é válido (tem mais de 10 letras e não tem a palavra None)
        tem_endereco_valido = len(end_raw) > 10 and 'None' not in end_raw and 'nan' not in end_raw

        # --- O CARD VISUAL ---
        with st.expander(f"{status_icon} {nome} {fire}"):
            
            # Detalhes
            st.markdown(f"**Dono:** {dono}")
            st.markdown(f"**Porte:** :{cor_status}[{status_txt}]")
            st.markdown(f"**Capital:** {capital}")
            
            if tem_endereco_valido:
                st.info(f"📍 {end_raw}")
            else:
                st.warning("⚠️ Endereço incompleto na Receita Federal")

            # --- BOTÕES CONDICIONAIS ---
            col1, col2 = st.columns(2)
            
            # BOTÃO 1: MAPA (Só aparece se tiver endereço bom)
            with col1:
                if tem_endereco_valido:
                    # Cria link do Google Maps
                    end_encoded = urllib.parse.quote(end_raw)
                    link_maps = f"https://www.google.com/maps/search/?api=1&query={end_encoded}"
                    st.link_button("📍 Ir p/ Local", link_maps)
                else:
                    st.button("🚫 Sem GPS", disabled=True)

            # BOTÃO 2: WHATSAPP (Só aparece se tiver celular)
            with col2:
                telefones = str(row['telefone_completo']).split(',')
                tem_zap = False
                
                # Procura o primeiro celular da lista
                for tel in telefones:
                    tel_clean = tel.strip().replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                    if "9" in tel and len(tel_clean) >= 10:
                        link_zap = f"https://wa.me/55{tel_clean}"
                        st.link_button("🟢 WhatsApp", link_zap)
                        tem_zap = True
                        break 
                
                if not tem_zap:
                    st.button("📞 Só Fixo", disabled=True, help=f"Tente ligar: {telefones[0]}", key=f"btn_fixo_{telefones[0]}")

else:
    st.error("⚠️ Arquivo Excel não encontrado ou vazio.")
    st.info("Certifique-se que o arquivo 'Leads_Almenara_GPS.xlsx' está na mesma pasta.")

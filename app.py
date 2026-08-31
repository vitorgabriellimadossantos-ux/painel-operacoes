import streamlit as st
import html as html_lib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time
from sqlalchemy import text as sql_text

# 1. Configurações da Página (Deve ser o primeiro comando Streamlit)
st.set_page_config(
    page_title="Painel de Controle Operacional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importando os módulos internos criados anteriormente
# O try/except garante que se os arquivos não estiverem na mesma pasta, o erro será amigável
try:
    import processamento as proc
    import relatorio_pdf as pdf
    import banco as db
except ImportError as e:
    st.error(
        "⚠️ Módulo interno não encontrado. Certifique-se de que "
        "processamento.py, relatorio_pdf.py e banco.py estão na mesma pasta. "
        f"Detalhe: {e}"
    )
    st.stop()


# ==========================================
# VISUAL MODERNO
# ==========================================
st.markdown("""
<style>
:root {
    --bg: #07111F;
    --bg-2: #0A1628;
    --surface: #0F1D32;
    --surface-2: #142641;
    --surface-3: #19304F;
    --border: #243A5A;
    --border-soft: #1B304C;
    --text: #F3F7FD;
    --text-2: #B8C7DA;
    --text-3: #8397B2;
    --accent: #3B82F6;
    --accent-2: #60A5FA;
    --accent-soft: rgba(59, 130, 246, .14);
    --success: #55C9A5;
    --warning: #E5B768;
}

/* BASE */
html, body, [data-testid="stAppViewContainer"], .stApp {
    background:
        radial-gradient(circle at 85% 0%, rgba(39, 91, 160, .12), transparent 30%),
        linear-gradient(180deg, #081424 0%, #07111F 100%) !important;
    color: var(--text) !important;
}

[data-testid="stHeader"] {
    background: rgba(7, 17, 31, .90) !important;
}

.block-container {
    padding-top: 1.65rem !important;
    padding-bottom: 3rem !important;
    max-width: 1500px !important;
}

[data-testid="stMainBlockContainer"] {
    position: relative !important;
    z-index: 1 !important;
}

[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4,
[data-testid="stMainBlockContainer"] h5,
[data-testid="stMainBlockContainer"] h6 {
    color: var(--text) !important;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #091528 !important;
    border-right: 1px solid var(--border-soft) !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: var(--text) !important;
}

[data-testid="stSidebar"] hr {
    border-color: var(--border-soft) !important;
}

/* BOTÕES */
.stButton > button,
button[kind="secondary"],
button[kind="primary"] {
    background: var(--surface-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    min-height: 2.65rem !important;
    font-weight: 650 !important;
    box-shadow: none !important;
    transition: background .18s ease, border-color .18s ease, transform .18s ease !important;
}

.stButton > button *,
button[kind="secondary"] *,
button[kind="primary"] * {
    color: var(--text) !important;
}

.stButton > button:hover,
button[kind="secondary"]:hover,
button[kind="primary"]:hover {
    background: var(--surface-3) !important;
    border-color: #35577F !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}

[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    justify-content: flex-start !important;
    background: transparent !important;
    border-color: transparent !important;
    padding: .68rem .78rem !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--surface-2) !important;
    border-color: var(--border-soft) !important;
}

/* MÉTRICAS */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #102039 0%, #0E1C31 100%) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 1rem 1.05rem !important;
    min-height: 116px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, .13) !important;
    overflow: visible !important;
}

div[data-testid="stMetric"] [data-testid="stMetricLabel"],
div[data-testid="stMetric"] [data-testid="stMetricLabel"] *,
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] label * {
    color: var(--text-3) !important;
    opacity: 1 !important;
    font-size: .80rem !important;
    font-weight: 700 !important;
    letter-spacing: .025em !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] * {
    color: #F7FAFF !important;
    opacity: 1 !important;
    visibility: visible !important;
    position: relative !important;
    z-index: 10 !important;
    font-weight: 800 !important;
    letter-spacing: -.025em !important;
}

div[data-testid="stMetric"] [data-testid="stMetricDelta"],
div[data-testid="stMetric"] [data-testid="stMetricDelta"] * {
    color: var(--accent-2) !important;
    opacity: 1 !important;
}

/* CARDS DE EMPRESA */
.company-card {
    background: linear-gradient(145deg, #102039 0%, #0D1B30 100%) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 1.15rem !important;
    min-height: 118px !important;
    box-shadow: 0 8px 22px rgba(0,0,0,.10) !important;
    margin-bottom: .45rem !important;
}

.company-name {
    color: var(--text) !important;
    font-size: 1.07rem !important;
    font-weight: 750 !important;
    margin-bottom: .35rem !important;
}

.company-meta {
    color: var(--text-3) !important;
    font-size: .86rem !important;
}

/* CABEÇALHO */
.page-kicker {
    color: var(--accent-2) !important;
    font-size: .72rem !important;
    font-weight: 750 !important;
    letter-spacing: .09em !important;
    text-transform: uppercase !important;
}

.page-title {
    color: #F6F9FE !important;
    font-size: 2rem !important;
    font-weight: 760 !important;
    letter-spacing: -.035em !important;
    line-height: 1.17 !important;
    margin-top: .30rem !important;
}

.page-subtitle {
    color: var(--text-3) !important;
    margin-top: .42rem !important;
    margin-bottom: 1.35rem !important;
}

/* ABAS - estilo pill da referência */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
    padding: .34rem !important;
    gap: .30rem !important;
}

.stTabs [data-baseweb="tab"] {
    position: relative !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 9px !important;
    padding: .62rem .92rem !important;
    margin: 0 !important;
    box-shadow: none !important;
    user-select: none !important;
    -webkit-user-select: none !important;
    transition: all .16s ease !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] div {
    color: var(--text-3) !important;
    font-weight: 650 !important;
    opacity: 1 !important;
    background: transparent !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--surface-2) !important;
}

.stTabs [data-baseweb="tab"]:hover p,
.stTabs [data-baseweb="tab"]:hover span,
.stTabs [data-baseweb="tab"]:hover div {
    color: var(--text-2) !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-soft) !important;
    border-color: rgba(96, 165, 250, .28) !important;
}

.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] div {
    color: #A9D0FF !important;
    font-weight: 750 !important;
}

.stTabs [data-baseweb="tab"]:focus,
.stTabs [data-baseweb="tab"]:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}

/* INPUTS / SELECTS */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
[data-testid="stDateInput"] > div > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--surface) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
}

[data-baseweb="input"] input,
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    color: var(--text) !important;
    opacity: 1 !important;
}

[data-testid="stDateInput"] svg,
[data-baseweb="select"] svg {
    fill: var(--text-2) !important;
}

/* Multiselect tags */
[data-baseweb="tag"] {
    background: var(--accent-soft) !important;
    border: 1px solid rgba(96,165,250,.22) !important;
}

[data-baseweb="tag"] *,
[data-baseweb="tag"] span {
    color: #BBD9FF !important;
}

/* Dropdowns */
div[role="listbox"],
ul[role="listbox"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
}

div[role="option"],
li[role="option"],
div[role="option"] span,
li[role="option"] span {
    color: var(--text-2) !important;
}

div[role="option"]:hover,
li[role="option"]:hover {
    background: var(--surface-2) !important;
}

/* UPLOAD */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border-radius: 14px !important;
}

[data-testid="stFileUploader"] section {
    background: #0C192B !important;
    border: 1px dashed #36567E !important;
    border-radius: 12px !important;
}

[data-testid="stFileUploader"] section *,
[data-testid="stFileUploader"] button * {
    color: var(--text-2) !important;
    opacity: 1 !important;
}

/* EXPANDER */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}

[data-testid="stExpander"] summary *,
[data-testid="stExpander"] details * {
    color: var(--text-2) !important;
}

/* TABELAS */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: var(--surface) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* ALERTAS */
[data-testid="stAlert"] {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-2) !important;
    border-radius: 11px !important;
}
[data-testid="stAlert"] * {
    color: var(--text-2) !important;
    opacity: 1 !important;
}

/* GRÁFICOS */
[data-testid="stPlotlyChart"] {
    background: linear-gradient(145deg, #102039 0%, #0D1B30 100%) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: .55rem !important;
    box-shadow: 0 8px 24px rgba(0,0,0,.10) !important;
}

/* Separadores */
hr {
    border: none !important;
    border-top: 1px solid var(--border-soft) !important;
    margin: 1.2rem 0 !important;
}

/* Captions */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color: var(--text-3) !important;
}

/* Evita qualquer conteúdo invisível */
[data-testid="stMainBlockContainer"] button,
[data-testid="stMainBlockContainer"] [data-testid="stMetric"],
[data-testid="stMainBlockContainer"] .company-card {
    visibility: visible !important;
    opacity: 1 !important;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* CORREÇÃO DE LEGIBILIDADE DOS KPIs */
div[data-testid="stMetric"] {
    min-width: 0 !important;
    margin-bottom: .75rem !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] > div,
div[data-testid="stMetric"] [data-testid="stMetricValue"] p {
    font-size: clamp(1.55rem, 2.25vw, 2.35rem) !important;
    line-height: 1.15 !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    max-width: none !important;
    width: auto !important;
    color: #F7FAFF !important;
}

div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

/* Evita reticências nos valores internos do Streamlit */
div[data-testid="stMetric"] * {
    text-overflow: clip !important;
}

/* Espaçamento visual entre as duas linhas de KPIs */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) {
    gap: .85rem !important;
}



/* =========================================================
   MENU SUPERIOR - ESTILO PILL MODERNO
   ========================================================= */
.stTabs {
    margin-top: .45rem !important;
    margin-bottom: 1.15rem !important;
}

/* Faixa horizontal do menu */
.stTabs [data-baseweb="tab-list"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: .38rem !important;

    background: linear-gradient(180deg, #101E33 0%, #0D192B 100%) !important;
    border: 1px solid #203754 !important;
    border-radius: 13px !important;

    padding: .42rem .48rem !important;
    min-height: 52px !important;

    overflow-x: auto !important;
    overflow-y: hidden !important;
    scrollbar-width: thin !important;
    scrollbar-color: #294463 transparent !important;

    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.025),
        0 8px 22px rgba(0,0,0,.10) !important;
}

/* Cada opção */
.stTabs [data-baseweb="tab"] {
    flex: 0 0 auto !important;

    background: #13243B !important;
    border: 1px solid #213A59 !important;
    border-radius: 999px !important;

    padding: .58rem 1rem !important;
    min-height: 38px !important;

    transition:
        background .18s ease,
        border-color .18s ease,
        transform .18s ease,
        box-shadow .18s ease !important;

    user-select: none !important;
    -webkit-user-select: none !important;
    cursor: pointer !important;
}

/* Texto normal */
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] div {
    color: #AFC0D5 !important;
    font-weight: 650 !important;
    font-size: .88rem !important;
    line-height: 1 !important;
    white-space: nowrap !important;

    background: transparent !important;
    opacity: 1 !important;
    text-decoration: none !important;
}

/* Hover */
.stTabs [data-baseweb="tab"]:hover {
    background: #18304E !important;
    border-color: #315579 !important;
    transform: translateY(-1px) !important;
}

.stTabs [data-baseweb="tab"]:hover p,
.stTabs [data-baseweb="tab"]:hover span,
.stTabs [data-baseweb="tab"]:hover div {
    color: #E8F2FF !important;
}

/* Selecionada - destaque claro igual referência */
.stTabs [aria-selected="true"] {
    background: #DCEBFC !important;
    border-color: #DCEBFC !important;

    box-shadow:
        0 3px 10px rgba(28, 93, 160, .20),
        inset 0 1px 0 rgba(255,255,255,.85) !important;

    transform: none !important;
}

.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] div {
    color: #16375B !important;
    font-weight: 800 !important;
}

/* Remove underline / foco padrão */
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

.stTabs [data-baseweb="tab"]:focus,
.stTabs [data-baseweb="tab"]:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}

/* Evita seleção de texto ao clicar */
.stTabs [data-baseweb="tab"],
.stTabs [data-baseweb="tab"] * {
    user-select: none !important;
    -webkit-user-select: none !important;
}

/* Scrollbar discreta caso a tela seja menor */
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
    height: 5px !important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
    background: #294463 !important;
    border-radius: 999px !important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-track {
    background: transparent !important;
}



/* =========================================================
   KPI CARDS / SEÇÕES — NOVA ARQUITETURA POWERBI-LIKE
   ========================================================= */
.kpi-grid-title {
    color: #8EA6C4;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin: .25rem 0 .65rem 0;
}

.kpi-card {
    background: linear-gradient(145deg, #102039 0%, #0D1B30 100%);
    border: 1px solid #243A5A;
    border-radius: 14px;
    padding: 1rem 1.05rem .95rem 1.05rem;
    min-height: 116px;
    box-shadow: 0 8px 24px rgba(0,0,0,.12);
    overflow: hidden;
}

.kpi-card .kpi-label {
    color: #8397B2;
    font-size: .73rem;
    font-weight: 800;
    letter-spacing: .045em;
    text-transform: uppercase;
    margin-bottom: .55rem;
}

.kpi-card .kpi-value {
    color: #F4F8FE;
    font-size: clamp(1.55rem, 2.4vw, 2.35rem);
    line-height: 1.05;
    font-weight: 820;
    letter-spacing: -.035em;
    white-space: nowrap;
}

.kpi-card .kpi-sub {
    color: #7790AF;
    font-size: .76rem;
    margin-top: .48rem;
    min-height: 18px;
}

.kpi-card.accent {
    border-color: rgba(96,165,250,.35);
    background: linear-gradient(145deg, #122743 0%, #0E1D32 100%);
}

.kpi-card.soft {
    background: linear-gradient(145deg, #112238 0%, #0E1D31 100%);
}

.section-head {
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    gap:1rem;
    margin:1.35rem 0 .75rem 0;
}

.section-head .section-title {
    color:#F3F7FD;
    font-size:1.03rem;
    font-weight:800;
}

.section-head .section-sub {
    color:#7F94AE;
    font-size:.78rem;
    margin-top:.20rem;
}

.data-note {
    background:#0F1D32;
    border:1px solid #243A5A;
    border-radius:12px;
    color:#8EA6C4;
    padding:.75rem .9rem;
    font-size:.80rem;
}



.kpi-card {
    min-height: 142px !important;
}

.kpi-delta {
    margin-top: .55rem;
    padding-top: .50rem;
    border-top: 1px solid rgba(105, 139, 180, .15);
    font-size: .76rem;
    font-weight: 750;
    line-height: 1.2;
}

.kpi-delta.up {
    color: #63C7B2;
}

.kpi-delta.down {
    color: #E6B672;
}

.kpi-delta.neutral {
    color: #8397B2;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# CONEXÃO COM O BANCO SUPABASE / POSTGRESQL
# ==========================================
@st.cache_resource
def obter_conexao_banco():
    """Cria a conexão SQL usando os Secrets configurados no Streamlit Cloud."""
    return st.connection("supabase", type="sql")


def carregar_empresas():
    """Carrega as empresas ativas diretamente do Supabase."""
    try:
        conn = obter_conexao_banco()
        df_empresas = conn.query(
            """
            SELECT id, nome, tipo, sistema_voz, sistema_chat, ativo
            FROM empresas
            WHERE ativo IS TRUE
            ORDER BY nome;
            """,
            ttl=0
        )

        registros = []
        for _, row in df_empresas.iterrows():
            registros.append({
                "id": int(row["id"]),
                "nome": str(row["nome"]),
                "tipo": row["tipo"] if pd.notna(row["tipo"]) else "",
                "erp": "",
                "voz": row["sistema_voz"] if pd.notna(row["sistema_voz"]) else "",
                "chat": row["sistema_chat"] if pd.notna(row["sistema_chat"]) else "",
                "ativo": bool(row["ativo"])
            })
        return registros

    except Exception as e:
        st.sidebar.error(f"Erro ao conectar ao Supabase: {e}")
        return []


def cadastrar_empresa_banco(nome, tipo, sistema_voz="", sistema_chat=""):
    """Cadastra uma nova empresa diretamente no Supabase."""
    conn = obter_conexao_banco()
    with conn.session as session:
        session.execute(
            sql_text(
                """
                INSERT INTO empresas (nome, tipo, sistema_voz, sistema_chat, ativo)
                VALUES (:nome, :tipo, :sistema_voz, :sistema_chat, TRUE)
                ON CONFLICT (nome) DO NOTHING;
                """
            ),
            {
                "nome": nome.upper().strip(),
                "tipo": tipo,
                "sistema_voz": sistema_voz.strip() if sistema_voz else None,
                "sistema_chat": sistema_chat.strip() if sistema_chat else None,
            }
        )
        session.commit()


def ler_arquivo_upload(uploaded_file):
    """Lê Excel/CSV e devolve o DataFrame bruto."""
    nome_arquivo = uploaded_file.name
    extensao = nome_arquivo.split('.')[-1].lower()

    if extensao == 'csv':
        return pd.read_csv(uploaded_file, sep=None, engine='python')
    if extensao in ['xls', 'xlsx']:
        return pd.read_excel(uploaded_file)
    return pd.DataFrame()


def processar_arquivos_upload(arquivos, lista_empresas):
    """
    Detecta automaticamente os formatos recebidos.
    Relaciona Volume + Indicadores de uma mesma empresa, separa
    produtividade agregada e mantém os metadados necessários
    para salvar cada arquivo no Supabase.
    """
    brutos = []

    # 1) Lê todos os arquivos e calcula o hash de cada upload.
    for uploaded_file in arquivos:
        try:
            hash_arquivo = db.gerar_hash_arquivo(uploaded_file)
            df_bruto = ler_arquivo_upload(uploaded_file)
            uploaded_file.seek(0)

            if df_bruto.empty:
                continue

            nome_arquivo = uploaded_file.name
            empresa = proc.identificar_empresa_por_arquivo(
                nome_arquivo,
                lista_empresas
            )
            tipo = proc.detectar_tipo_planilha(df_bruto, nome_arquivo)

            brutos.append({
                'nome': nome_arquivo,
                'empresa': empresa,
                'tipo': tipo,
                'df': df_bruto,
                'hash': hash_arquivo
            })

        except Exception as e:
            st.sidebar.error(f"Erro ao ler {uploaded_file.name}: {e}")

    # 2) Indexa indicadores por empresa para parear R2/NEX.
    indicadores_por_empresa = {}

    for item in brutos:
        if item['tipo'] == 'chat_indicadores':
            empresa = item['empresa']

            if (
                empresa == 'EMPRESA NÃO IDENTIFICADA'
                and 'EMPRESA' in item['df'].columns
            ):
                vals = (
                    item['df']['EMPRESA']
                    .dropna()
                    .astype(str)
                    .str.strip()
                )
                if not vals.empty:
                    empresa = vals.iloc[0]

            indicadores_por_empresa[str(empresa).upper()] = item['df']

    dataframes_atendimentos = []
    dataframes_produtividade = []
    itens_importacao = []

    # 3) Processa cada arquivo e prepara sua gravação.
    for item in brutos:
        nome = item['nome']
        empresa = item['empresa']
        tipo = item['tipo']
        df_bruto = item['df']
        hash_arquivo = item['hash']

        try:
            # Indicadores diários são salvos em tabela própria.
            if tipo == 'chat_indicadores':
                df_ind = proc.processar_indicadores_chat(df_bruto)

                empresa_final = empresa
                if 'Empresa' in df_ind.columns:
                    vals = df_ind['Empresa'].dropna().astype(str).str.strip()
                    vals = vals[vals != '']
                    if not vals.empty:
                        empresa_final = vals.iloc[0]

                itens_importacao.append({
                    'nome': nome,
                    'empresa': empresa_final,
                    'tipo': tipo,
                    'canal': 'Chat',
                    'hash': hash_arquivo,
                    'df': df_ind,
                    'destino': 'indicadores'
                })
                continue

            # LIG TOP: relatório agregado por agente.
            if tipo == 'ligtop_agentes':
                empresa_final = (
                    empresa
                    if empresa != 'EMPRESA NÃO IDENTIFICADA'
                    else 'LIG TOP'
                )

                df_prod = proc.processar_ligtop_agentes(
                    df_bruto,
                    empresa_final
                )

                dataframes_produtividade.append(df_prod)

                itens_importacao.append({
                    'nome': nome,
                    'empresa': empresa_final,
                    'tipo': tipo,
                    'canal': 'Chat',
                    'hash': hash_arquivo,
                    'df': df_prod,
                    'destino': 'produtividade'
                })
                continue

            # Para Volume R2/NEX, procura Indicadores correspondente.
            df_indicadores = None

            if tipo == 'chat_volume':
                chave = str(empresa).upper()
                df_indicadores = indicadores_por_empresa.get(chave)

                if df_indicadores is None:
                    nome_upper = nome.upper()
                    prefixo = nome_upper.split(' - ')[0]

                    for chave_ind, df_ind in indicadores_por_empresa.items():
                        if chave_ind in nome_upper or prefixo in chave_ind:
                            df_indicadores = df_ind
                            break

            df_processado = proc.processar_dataframe_automatico(
                df_bruto,
                nome_arquivo=nome,
                nome_empresa=(
                    None
                    if empresa == 'EMPRESA NÃO IDENTIFICADA'
                    else empresa
                ),
                df_indicadores=df_indicadores
            )

            if not df_processado.empty:
                dataframes_atendimentos.append(df_processado)

                empresa_final = empresa
                if 'Empresa' in df_processado.columns:
                    vals = (
                        df_processado['Empresa']
                        .dropna()
                        .astype(str)
                        .str.strip()
                    )
                    vals = vals[vals != '']
                    if not vals.empty:
                        empresa_final = vals.iloc[0]

                canal_final = ''
                if 'Canal' in df_processado.columns:
                    vals_canal = (
                        df_processado['Canal']
                        .dropna()
                        .astype(str)
                        .str.strip()
                    )
                    vals_canal = vals_canal[vals_canal != '']
                    if not vals_canal.empty:
                        canal_final = vals_canal.iloc[0]

                itens_importacao.append({
                    'nome': nome,
                    'empresa': empresa_final,
                    'tipo': tipo,
                    'canal': canal_final,
                    'hash': hash_arquivo,
                    'df': df_processado,
                    'destino': 'atendimentos'
                })

        except Exception as e:
            st.sidebar.error(f"Erro ao processar {nome}: {e}")

    return (
        dataframes_atendimentos,
        dataframes_produtividade,
        itens_importacao
    )


def obter_periodo_dataframe(df):
    """Retorna data inicial e final quando o DataFrame possui a coluna Data."""
    if df is None or df.empty or 'Data' not in df.columns:
        return None, None

    datas = pd.to_datetime(df['Data'], errors='coerce').dropna()
    if datas.empty:
        return None, None

    return datas.min().date(), datas.max().date()


def normalizar_indicadores_banco(df):
    """Compatibiliza as colunas do processamento.py com banco.py."""
    resultado = df.copy()

    mapa = {
        'ATENDIMENTOS': 'Atendimentos',
        'SLA': 'SLA_Percentual'
    }
    resultado = resultado.rename(columns=mapa)

    for coluna in [
        'Atendimentos',
        'TMA_Seg',
        'TME_Seg',
        'TMR_Seg',
        'SLA_Percentual'
    ]:
        if coluna not in resultado.columns:
            resultado[coluna] = None

    return resultado


def excluir_importacao_em_caso_de_erro(importacao_id):
    """Remove o registro de importação se a gravação principal falhar."""
    if not importacao_id:
        return

    try:
        conn = db.obter_conexao()
        with conn.session as session:
            session.execute(
                sql_text("DELETE FROM importacoes WHERE id = :id"),
                {'id': importacao_id}
            )
            session.commit()
    except Exception:
        pass



# ==========================================
# CONSULTAS E FUNÇÕES DA INTERFACE PERSISTENTE
# ==========================================
def consultar_produtividade_empresa(empresa_id):
    conn = db.obter_conexao()
    consulta = """
        SELECT
            p.id,
            e.nome AS "Empresa",
            p.data_inicial AS "Data_Inicial",
            p.data_final AS "Data_Final",
            p.agente AS "Agente",
            p.conversas_atribuidas AS "Conversas_Atribuidas",
            p.resolucoes AS "Resolvidos",
            p.tempo_primeira_resposta_seg AS "Primeira_Resposta_Seg",
            p.tempo_resolucao_seg AS "Tempo_Resolucao_Seg",
            p.tempo_espera_cliente_seg AS "Espera_Cliente_Seg"
        FROM produtividade_agentes p
        JOIN empresas e ON e.id = p.empresa_id
        WHERE p.empresa_id = :empresa_id
        ORDER BY p.data_final DESC NULLS LAST, p.agente;
    """
    with conn.session as session:
        rows = session.execute(
            sql_text(consulta), {"empresa_id": empresa_id}
        ).mappings().all()
    return pd.DataFrame(rows)


def consultar_indicadores_empresa(empresa_id):
    conn = db.obter_conexao()
    consulta = """
        SELECT
            data AS "Data",
            canal AS "Canal",
            atendimentos AS "Atendimentos",
            tma_seg AS "TMA_Seg",
            tme_seg AS "TME_Seg",
            tmr_seg AS "TMR_Seg",
            sla_percentual AS "SLA_Percentual"
        FROM indicadores_diarios
        WHERE empresa_id = :empresa_id
        ORDER BY data;
    """
    with conn.session as session:
        rows = session.execute(
            sql_text(consulta), {"empresa_id": empresa_id}
        ).mappings().all()
    return pd.DataFrame(rows)


def preparar_dataframe_banco(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=list(proc.COLUNAS_PADRAO) + ["Data_Parse"])

    resultado = df.copy()
    for coluna in proc.COLUNAS_PADRAO:
        if coluna not in resultado.columns:
            resultado[coluna] = None

    resultado["Data_Parse"] = pd.to_datetime(resultado["Data"], errors="coerce")
    resultado["Tempo_Espera_Seg"] = pd.to_numeric(
        resultado["Tempo_Espera_Seg"], errors="coerce"
    )
    resultado["Tempo_Conversa_Seg"] = pd.to_numeric(
        resultado["Tempo_Conversa_Seg"], errors="coerce"
    )
    return resultado


def filtrar_dataframe_painel(df, chave):
    if df.empty:
        return df, "Sem período"

    min_ts = df["Data_Parse"].min()
    max_ts = df["Data_Parse"].max()

    if pd.isna(min_ts) or pd.isna(max_ts):
        return df, "Período não identificado"

    min_date = min_ts.date()
    max_date = max_ts.date()

    periodo = st.date_input(
        "Período de análise",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key=f"periodo_{chave}",
    )

    filtrado = df.copy()
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        inicio, fim = periodo
        filtrado = filtrado[
            (filtrado["Data_Parse"].dt.date >= inicio)
            & (filtrado["Data_Parse"].dt.date <= fim)
        ]
        periodo_str = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    else:
        periodo_str = min_date.strftime("%d/%m/%Y")

    canais = sorted(filtrado["Canal"].dropna().astype(str).unique().tolist())
    canais_sel = st.multiselect(
        "Canal",
        canais,
        default=canais,
        key=f"canal_{chave}",
    )
    if canais_sel:
        filtrado = filtrado[filtrado["Canal"].isin(canais_sel)]

    return filtrado, periodo_str



def aplicar_tema_grafico(fig, titulo, subtitulo="", x_titulo="", y_titulo="", altura=360):
    """Tema visual único para gráficos do painel."""
    titulo_html = f"<b>{titulo}</b>"
    if subtitulo:
        titulo_html += f"<br><span style='font-size:12px;color:#7F94AE'>{subtitulo}</span>"

    fig.update_layout(
        title=dict(
            text=titulo_html,
            x=0.025,
            xanchor="left",
            y=0.96,
            yanchor="top",
            font=dict(size=17, color="#F3F7FD"),
        ),
        height=altura,
        paper_bgcolor="#0F1D32",
        plot_bgcolor="#0F1D32",
        font=dict(
            family="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif",
            color="#B8C7DA",
            size=12,
        ),
        margin=dict(l=34, r=24, t=78, b=38),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#142641",
            bordercolor="#365878",
            font=dict(color="#F3F7FD", size=12),
        ),
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            font=dict(color="#AFC0D5", size=11),
        ),
        transition=dict(duration=250),
    )

    fig.update_xaxes(
        title=x_titulo,
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(color="#8397B2", size=11),
        title_font=dict(color="#8397B2", size=11),
        fixedrange=False,
    )

    fig.update_yaxes(
        title=y_titulo,
        gridcolor="rgba(106, 137, 174, .13)",
        zeroline=False,
        showline=False,
        tickfont=dict(color="#8397B2", size=11),
        title_font=dict(color="#8397B2", size=11),
        rangemode="tozero",
        fixedrange=False,
    )

    return fig



def cabecalho_pagina(kicker, titulo, subtitulo=""):
    st.markdown(f'<div class="page-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{titulo}</div>', unsafe_allow_html=True)
    if subtitulo:
        st.markdown(f'<div class="page-subtitle">{subtitulo}</div>', unsafe_allow_html=True)



def card_kpi(label, valor, subtitulo="", destaque=False, delta_texto=None, delta_direcao=None):
    classe = "kpi-card accent" if destaque else "kpi-card"
    label = html_lib.escape(str(label))
    valor = html_lib.escape(str(valor))
    subtitulo = html_lib.escape(str(subtitulo)) if subtitulo else ""

    delta_html = ""
    if delta_texto:
        delta_safe = html_lib.escape(str(delta_texto))
        classe_delta = "neutral"
        seta = ""
        if delta_direcao == "up":
            classe_delta = "up"
            seta = "↑"
        elif delta_direcao == "down":
            classe_delta = "down"
            seta = "↓"

        delta_html = f'<div class="kpi-delta {classe_delta}">{seta} {delta_safe}</div>'

    st.markdown(
        f"""
        <div class="{classe}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{valor}</div>
            <div class="kpi-sub">{subtitulo}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )



def calcular_variacao_percentual(atual, anterior):
    """Retorna texto e direção da variação percentual."""
    try:
        if anterior is None or pd.isna(anterior) or float(anterior) == 0:
            return "Sem comparação", None
        if atual is None or pd.isna(atual):
            return "Sem comparação", None

        atual = float(atual)
        anterior = float(anterior)
        variacao = ((atual - anterior) / abs(anterior)) * 100

        if abs(variacao) < 0.005:
            return "0,00% vs. período anterior", None

        direcao = "up" if variacao > 0 else "down"
        texto = f"{abs(variacao):.2f}% vs. período anterior".replace(".", ",")
        return texto, direcao
    except Exception:
        return "Sem comparação", None


def obter_periodo_anterior(df_completo, df_atual):
    """Seleciona o período imediatamente anterior com a mesma duração."""
    if df_atual is None or df_atual.empty or "Data_Parse" not in df_atual.columns:
        return pd.DataFrame()

    datas = df_atual["Data_Parse"].dropna()
    if datas.empty:
        return pd.DataFrame()

    inicio = pd.to_datetime(datas.min()).normalize()
    fim = pd.to_datetime(datas.max()).normalize()
    dias = (fim - inicio).days + 1

    fim_anterior = inicio - pd.Timedelta(days=1)
    inicio_anterior = fim_anterior - pd.Timedelta(days=dias - 1)

    base = df_completo.copy()
    if "Data_Parse" not in base.columns:
        base = preparar_dataframe_banco(base)

    datas_base = pd.to_datetime(base["Data_Parse"], errors="coerce")
    mask = (datas_base >= inicio_anterior) & (datas_base <= fim_anterior)
    return base.loc[mask].copy()


def metricas_voz_comparacao(df):
    """Calcula os KPIs de voz usados nos cards comparativos."""
    voz = df[
        df["Canal"].astype(str).str.contains("Voz", case=False, na=False)
    ].copy()

    if voz.empty:
        return {
            "recebidas": 0,
            "atendidas": 0,
            "abandonadas": 0,
            "sla": None,
            "tma": None,
            "tme": None,
            "tme_abandonadas": None,
        }

    mask_ab = _status_abandonado(voz["Status"])
    recebidas = len(voz)
    abandonadas = int(mask_ab.sum())
    atendidas = recebidas - abandonadas
    sla = _sla_dataframe(voz)
    tma = pd.to_numeric(voz["Tempo_Conversa_Seg"], errors="coerce").mean()
    tme = pd.to_numeric(voz["Tempo_Espera_Seg"], errors="coerce").mean()
    tme_ab = (
        pd.to_numeric(voz.loc[mask_ab, "Tempo_Espera_Seg"], errors="coerce").mean()
        if abandonadas else None
    )

    return {
        "recebidas": recebidas,
        "atendidas": atendidas,
        "abandonadas": abandonadas,
        "sla": sla,
        "tma": tma,
        "tme": tme,
        "tme_abandonadas": tme_ab,
    }



def titulo_secao(titulo, subtitulo=""):
    titulo = html_lib.escape(str(titulo))
    subtitulo = html_lib.escape(str(subtitulo))
    st.markdown(
        f"""
        <div class="section-head">
            <div>
                <div class="section-title">{titulo}</div>
                <div class="section-sub">{subtitulo}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _status_abandonado(serie):
    return serie.astype(str).str.contains("aband", case=False, na=False)


def _percentual(parte, total):
    if not total:
        return "0,00%"
    return f"{(parte / total * 100):.2f}%".replace(".", ",")


def _sla_dataframe(df):
    if df is None or df.empty:
        return None
    try:
        return proc.calcular_metricas(df).get("SLA (%)")
    except Exception:
        return None


def _fmt_sla(valor):
    if valor is None or pd.isna(valor):
        return "Sem dado"
    try:
        return f"{float(valor):.2f}%".replace(".", ",")
    except Exception:
        return str(valor)


def _extrair_hora(valor):
    try:
        if isinstance(valor, str):
            return int(valor.split(":")[0])
        if isinstance(valor, time):
            return valor.hour
        if hasattr(valor, "hour"):
            return int(valor.hour)
    except Exception:
        pass
    return None


def _coluna_classificacao(df):
    candidatos = [
        "Classificacao", "Classificação", "classificacao", "classificação",
        "Motivo", "motivo", "Categoria", "categoria"
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def _tabela_voz_empresas(df):
    voz = df[df["Canal"].astype(str).str.contains("Voz", case=False, na=False)].copy()
    if voz.empty:
        return pd.DataFrame()

    linhas = []
    for empresa, grupo in voz.groupby("Empresa", dropna=False):
        recebidas = len(grupo)
        mask_ab = _status_abandonado(grupo["Status"])
        abandonadas = int(mask_ab.sum())
        atendidas = recebidas - abandonadas
        sla = _sla_dataframe(grupo)
        tme_ab = grupo.loc[mask_ab, "Tempo_Espera_Seg"].mean() if abandonadas else None

        linhas.append({
            "Empresa": str(empresa),
            "Recebidas": recebidas,
            "Atendidas": atendidas,
            "% Atendidas": _percentual(atendidas, recebidas),
            "Nível de Serviço": _fmt_sla(sla),
            "Abandonadas": abandonadas,
            "% Abandonadas": _percentual(abandonadas, recebidas),
            "TME Abandonadas": proc.formatar_segundos_para_hora(tme_ab) if pd.notna(tme_ab) else "Sem dado",
            "Sem Classificação": "Sem dado",
        })

    return pd.DataFrame(linhas).sort_values("Recebidas", ascending=False)


def _grafico_horario(df, titulo, subtitulo, nome_valor="Atendimentos", area=False):
    temp = df.copy()
    temp["Hora_Inteira"] = temp["Hora"].apply(_extrair_hora)
    hora = (
        temp.dropna(subset=["Hora_Inteira"])
        .groupby("Hora_Inteira")
        .size()
        .reindex(range(24), fill_value=0)
        .rename("Volume")
        .reset_index()
    )
    if hora["Volume"].sum() == 0:
        return None

    if area:
        fig = go.Figure(go.Scatter(
            x=hora["Hora_Inteira"],
            y=hora["Volume"],
            mode="lines+markers",
            line=dict(color="#62A9EE", width=3, shape="spline", smoothing=.65),
            marker=dict(size=5, color="#94C9FA"),
            fill="tozeroy",
            fillcolor="rgba(73, 147, 215, .18)",
            hovertemplate="<b>%{x}:00</b><br>%{y} " + nome_valor.lower() + "<extra></extra>",
        ))
    else:
        fig = go.Figure(go.Bar(
            x=hora["Hora_Inteira"],
            y=hora["Volume"],
            marker=dict(
                color=hora["Volume"],
                colorscale=[[0, "#193653"], [.5, "#326B9B"], [1, "#61A6E5"]],
                line=dict(width=0),
            ),
            hovertemplate="<b>%{x}:00</b><br>%{y} " + nome_valor.lower() + "<extra></extra>",
        ))
        try:
            fig.update_traces(marker_cornerradius=6)
        except Exception:
            pass

    fig = aplicar_tema_grafico(
        fig, titulo, subtitulo,
        x_titulo="Horário",
        y_titulo=nome_valor,
        altura=380,
    )
    fig.update_layout(showlegend=False, hovermode="closest")
    fig.update_xaxes(
        tickvals=list(range(0,24,3)),
        ticktext=[f"{h:02d}:00" for h in range(0,24,3)],
    )
    return fig

def renderizar_painel(df, titulo, chave, mostrar_empresas=False):
    cabecalho_pagina(
        "PAINEL OPERACIONAL",
        titulo,
        "Indicadores consolidados a partir dos dados salvos no Supabase."
    )

    df = preparar_dataframe_banco(df)
    if df.empty:
        st.info("Nenhum dado importado para esta seleção.")
        return

    # Filtro de empresas somente na visão consolidada
    if mostrar_empresas:
        empresas = sorted(df["Empresa"].dropna().astype(str).unique().tolist())
        empresas_sel = st.multiselect(
            "Empresas",
            empresas,
            default=empresas,
            key=f"empresas_{chave}",
        )
        if empresas_sel:
            df = df[df["Empresa"].astype(str).isin(empresas_sel)]

    df_filtrado, periodo_str = filtrar_dataframe_painel(df, chave)
    st.caption(f"Dados salvos no Supabase — {periodo_str}")

    if df_filtrado.empty:
        st.warning("Não há dados para os filtros selecionados.")
        return

    # Mesmo recorte de empresa/canal, mas no período imediatamente anterior
    df_periodo_anterior = obter_periodo_anterior(df, df_filtrado)

    # Se a visão consolidada usa seleção de empresas, mantém as mesmas empresas na comparação
    if mostrar_empresas and 'empresas_sel' in locals() and empresas_sel and not df_periodo_anterior.empty:
        df_periodo_anterior = df_periodo_anterior[
            df_periodo_anterior["Empresa"].astype(str).isin(empresas_sel)
        ]

    abas = st.tabs([
        "Visão Executiva",
        "Telefonia e Voz",
        "Mensageria e Chat",
        "Produtividade",
        "Dados",
        "Exportar PDF",
    ])

    # =====================================================
    # 1. VISÃO EXECUTIVA
    # =====================================================
    with abas[0]:
        voz = df_filtrado[
            df_filtrado["Canal"].astype(str).str.contains("Voz", case=False, na=False)
        ].copy()
        chat = df_filtrado[
            df_filtrado["Canal"].astype(str).str.contains("Chat", case=False, na=False)
        ].copy()

        total = len(df_filtrado)
        total_voz = len(voz)
        total_chat = len(chat)

        if mostrar_empresas:
            # Tela equivalente à "VISÃO GERAL DAS EMPRESAS (SOMENTE VOZ)"
            titulo_secao(
                "Visão geral das empresas — Voz",
                "Recebidas, atendidas, abandono e nível de serviço por empresa"
            )

            recebidas = total_voz
            mask_ab = _status_abandonado(voz["Status"]) if not voz.empty else pd.Series(dtype=bool)
            abandonadas = int(mask_ab.sum()) if not voz.empty else 0
            atendidas = recebidas - abandonadas
            sla_voz = _sla_dataframe(voz)

            cols = st.columns(4)
            with cols[0]:
                card_kpi("Recebidas", recebidas, "Atendidas + abandonadas", True)
            with cols[1]:
                card_kpi("Atendidas", atendidas, _percentual(atendidas, recebidas))
            with cols[2]:
                card_kpi("Abandonadas", abandonadas, _percentual(abandonadas, recebidas))
            with cols[3]:
                card_kpi("Nível de Serviço", _fmt_sla(sla_voz), "Indicador SLA")

            tabela_voz = _tabela_voz_empresas(df_filtrado)

            ctab, cgraf = st.columns([1.12, 1.45])
            with ctab:
                titulo_secao("Desempenho por empresa", "Consolidado de Voz no período")
                if tabela_voz.empty:
                    st.info("Não há registros de Voz no período.")
                else:
                    st.dataframe(
                        tabela_voz,
                        width="stretch",
                        height=445,
                        hide_index=True,
                    )

            with cgraf:
                fig_hora = _grafico_horario(
                    voz,
                    "Volume de atendimento por horário",
                    "Distribuição das chamadas recebidas ao longo do dia",
                    "Chamadas",
                    area=False,
                )
                if fig_hora is not None:
                    st.plotly_chart(
                        fig_hora,
                        width="stretch",
                        config={
                            "displaylogo": False,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                    )
                else:
                    st.info("Não há horários válidos para montar o gráfico.")

        else:
            # Tela individual inspirada no painel R2
            titulo_secao(
                "Resumo da operação",
                "Visão integrada de Chat e Voz para a empresa selecionada"
            )

            franquia = "Sem dado"
            excedidos = "Sem dado"

            top = st.columns(3)
            with top[0]:
                card_kpi("Franquia de atendimentos", franquia, "Aguardando configuração")
            with top[1]:
                card_kpi("Total de atendimentos", total, "Chat + Voz", True)
            with top[2]:
                card_kpi("Atendimentos excedidos", excedidos, "Depende da franquia")

            st.markdown("<br>", unsafe_allow_html=True)

            col_chat, col_voz = st.columns(2)

            with col_chat:
                titulo_secao("Chat", "Indicadores de mensageria")
                pct_chat = _percentual(total_chat, total)
                c = st.columns(1)
                with c[0]:
                    card_kpi("Atendimentos", total_chat, pct_chat, True)

                tma_chat = chat["Tempo_Conversa_Seg"].mean() if not chat.empty else None
                tme_chat = chat["Tempo_Espera_Seg"].mean() if not chat.empty else None

                m = st.columns(3)
                with m[0]:
                    card_kpi(
                        "TMA",
                        proc.formatar_segundos_para_hora(tma_chat) if pd.notna(tma_chat) else "Sem dado"
                    )
                with m[1]:
                    card_kpi(
                        "TME",
                        proc.formatar_segundos_para_hora(tme_chat) if pd.notna(tme_chat) else "Sem dado"
                    )
                with m[2]:
                    card_kpi("TMR", "Sem dado", "Campo ainda não salvo")

            with col_voz:
                titulo_secao("Voz", "Indicadores de telefonia")
                mask_ab = _status_abandonado(voz["Status"]) if not voz.empty else pd.Series(dtype=bool)
                abandonadas = int(mask_ab.sum()) if not voz.empty else 0
                atendidas = total_voz - abandonadas
                sla_voz = _sla_dataframe(voz)
                pct_voz = _percentual(total_voz, total)

                cv = st.columns(2)
                with cv[0]:
                    card_kpi("Atendimentos", total_voz, pct_voz, True)
                with cv[1]:
                    card_kpi("Nível de Serviço", _fmt_sla(sla_voz), "SLA")

                tma_voz = voz["Tempo_Conversa_Seg"].mean() if not voz.empty else None
                tme_voz = voz["Tempo_Espera_Seg"].mean() if not voz.empty else None
                tme_ab = voz.loc[mask_ab, "Tempo_Espera_Seg"].mean() if abandonadas else None

                mv = st.columns(4)
                with mv[0]:
                    card_kpi(
                        "TMA",
                        proc.formatar_segundos_para_hora(tma_voz) if pd.notna(tma_voz) else "Sem dado"
                    )
                with mv[1]:
                    card_kpi(
                        "TME",
                        proc.formatar_segundos_para_hora(tme_voz) if pd.notna(tme_voz) else "Sem dado"
                    )
                with mv[2]:
                    card_kpi("Abandonadas", abandonadas, _percentual(abandonadas, total_voz))
                with mv[3]:
                    card_kpi(
                        "TME Abandonadas",
                        proc.formatar_segundos_para_hora(tme_ab) if pd.notna(tme_ab) else "Sem dado"
                    )

            titulo_secao(
                "Volume de atendimento por horário",
                "Os gráficos abaixo respondem ao comportamento de Chat e Voz ao longo do dia"
            )
            g1, g2 = st.columns(2)
            with g1:
                fig_chat = _grafico_horario(
                    chat,
                    "Chat por horário",
                    "Conversas iniciadas em cada hora",
                    "Conversas",
                    area=True,
                )
                if fig_chat is not None:
                    st.plotly_chart(
                        fig_chat,
                        width="stretch",
                        config={"displaylogo": False, "scrollZoom": True}
                    )
                else:
                    st.info("Sem dados horários de Chat.")

            with g2:
                voz_atendidas = voz.copy()
                if not voz_atendidas.empty:
                    voz_atendidas = voz_atendidas[~_status_abandonado(voz_atendidas["Status"])]

                fig_voz = _grafico_horario(
                    voz_atendidas,
                    "Voz atendida por horário",
                    "Chamadas atendidas em cada hora",
                    "Chamadas",
                    area=True,
                )
                if fig_voz is not None:
                    st.plotly_chart(
                        fig_voz,
                        width="stretch",
                        config={"displaylogo": False, "scrollZoom": True}
                    )
                else:
                    st.info("Sem dados horários de Voz.")

    # =====================================================
    # 2. TELEFONIA E VOZ
    # =====================================================
    with abas[1]:
        voz = df_filtrado[
            df_filtrado["Canal"].astype(str).str.contains("Voz", case=False, na=False)
        ].copy()

        if voz.empty:
            st.info("Nenhum registro de Voz neste período.")
        else:
            mask_ab = _status_abandonado(voz["Status"])
            recebidas = len(voz)
            abandonadas = int(mask_ab.sum())
            atendidas = recebidas - abandonadas
            sla = _sla_dataframe(voz)
            tme_ab = voz.loc[mask_ab, "Tempo_Espera_Seg"].mean() if abandonadas else None

            titulo_secao(
                "Telefonia e Voz",
                "Indicadores de recebimento, atendimento, abandono e nível de serviço"
            )

            atual_comp = metricas_voz_comparacao(df_filtrado)
            anterior_comp = metricas_voz_comparacao(df_periodo_anterior) if not df_periodo_anterior.empty else {}

            d_recebidas = calcular_variacao_percentual(
                atual_comp["recebidas"], anterior_comp.get("recebidas")
            )
            d_atendidas = calcular_variacao_percentual(
                atual_comp["atendidas"], anterior_comp.get("atendidas")
            )
            d_abandonadas = calcular_variacao_percentual(
                atual_comp["abandonadas"], anterior_comp.get("abandonadas")
            )
            d_sla = calcular_variacao_percentual(
                atual_comp["sla"], anterior_comp.get("sla")
            )
            d_tma = calcular_variacao_percentual(
                atual_comp["tma"], anterior_comp.get("tma")
            )
            d_tme = calcular_variacao_percentual(
                atual_comp["tme"], anterior_comp.get("tme")
            )
            d_tme_ab = calcular_variacao_percentual(
                atual_comp["tme_abandonadas"], anterior_comp.get("tme_abandonadas")
            )

            r1 = st.columns(4)
            with r1[0]:
                card_kpi(
                    "Recebidas", recebidas, "Total de chamadas", True,
                    delta_texto=d_recebidas[0], delta_direcao=d_recebidas[1]
                )
            with r1[1]:
                card_kpi(
                    "Atendidas", atendidas, _percentual(atendidas, recebidas),
                    delta_texto=d_atendidas[0], delta_direcao=d_atendidas[1]
                )
            with r1[2]:
                card_kpi(
                    "Abandonadas", abandonadas, _percentual(abandonadas, recebidas),
                    delta_texto=d_abandonadas[0], delta_direcao=d_abandonadas[1]
                )
            with r1[3]:
                card_kpi(
                    "Nível de Serviço", _fmt_sla(sla), "SLA",
                    delta_texto=d_sla[0], delta_direcao=d_sla[1]
                )

            r2 = st.columns(3)
            with r2[0]:
                card_kpi(
                    "TMA",
                    proc.formatar_segundos_para_hora(voz["Tempo_Conversa_Seg"].mean()),
                    delta_texto=d_tma[0], delta_direcao=d_tma[1]
                )
            with r2[1]:
                card_kpi(
                    "TME",
                    proc.formatar_segundos_para_hora(voz["Tempo_Espera_Seg"].mean()),
                    delta_texto=d_tme[0], delta_direcao=d_tme[1]
                )
            with r2[2]:
                card_kpi(
                    "TME Abandonadas",
                    proc.formatar_segundos_para_hora(tme_ab) if pd.notna(tme_ab) else "Sem dado",
                    delta_texto=d_tme_ab[0], delta_direcao=d_tme_ab[1]
                )

            titulo_secao(
                "Volume de atendimento por horário",
                "Passe o mouse para ver o volume exato de cada hora"
            )
            fig = _grafico_horario(
                voz,
                "Chamadas recebidas por horário",
                "Distribuição das chamadas ao longo das 24 horas",
                "Chamadas",
                area=False,
            )
            if fig is not None:
                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                    },
                )

            if mostrar_empresas:
                tabela = _tabela_voz_empresas(df_filtrado)
                titulo_secao("Tabela por empresa", "Detalhamento dos indicadores de Voz")
                st.dataframe(tabela, width="stretch", height=430, hide_index=True)

            with st.expander("Ver registros detalhados de Voz"):
                st.dataframe(voz, width="stretch", height=380)

    # =====================================================
    # 3. MENSAGERIA E CHAT
    # =====================================================
    with abas[2]:
        chat = df_filtrado[
            df_filtrado["Canal"].astype(str).str.contains("Chat", case=False, na=False)
        ].copy()

        if chat.empty:
            st.info("Nenhum registro de Chat neste período.")
        else:
            titulo_secao(
                "Mensageria e Chat",
                "Volume, tempos de atendimento e comportamento por horário"
            )

            r = st.columns(4)
            with r[0]:
                card_kpi("Atendimentos", len(chat), "Conversas processadas", True)
            with r[1]:
                card_kpi(
                    "TMA",
                    proc.formatar_segundos_para_hora(chat["Tempo_Conversa_Seg"].mean())
                )
            with r[2]:
                card_kpi(
                    "TME",
                    proc.formatar_segundos_para_hora(chat["Tempo_Espera_Seg"].mean())
                )
            with r[3]:
                card_kpi("TMR", "Sem dado", "Campo ainda não salvo")

            fig = _grafico_horario(
                chat,
                "Chat por horário",
                "Distribuição das conversas ao longo das 24 horas",
                "Conversas",
                area=True,
            )
            if fig is not None:
                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={"displaylogo": False, "scrollZoom": True},
                )

            with st.expander("Ver registros detalhados de Chat"):
                st.dataframe(chat, width="stretch", height=380)

    # =====================================================
    # 4. PRODUTIVIDADE
    # =====================================================
    with abas[3]:
        agentes = df_filtrado[
            df_filtrado["Agente"].notna()
            & (df_filtrado["Agente"].astype(str).str.strip() != "")
            & (df_filtrado["Agente"].astype(str) != "Não Informado")
        ].copy()

        if agentes.empty:
            st.info("Não há dados individuais de agentes neste período.")
        else:
            titulo_secao(
                "Desempenho por agente",
                "Atendimentos, TMA, TME, nível de serviço e classificação"
            )

            linhas = []
            for agente, grupo in agentes.groupby("Agente"):
                sla_ag = _sla_dataframe(grupo)
                linhas.append({
                    "Agente": agente,
                    "Atendimentos": len(grupo),
                    "TMA": proc.formatar_segundos_para_hora(grupo["Tempo_Conversa_Seg"].mean()),
                    "TME": proc.formatar_segundos_para_hora(grupo["Tempo_Espera_Seg"].mean()),
                    "Nível de Serviço": _fmt_sla(sla_ag),
                    "% Sem Classificação": "Sem dado",
                })

            ranking = pd.DataFrame(linhas).sort_values("Atendimentos", ascending=False)

            k = st.columns(4)
            with k[0]:
                card_kpi("Total Atendimentos", len(agentes), "Com agente identificado", True)
            with k[1]:
                card_kpi("Nível de Serviço", _fmt_sla(_sla_dataframe(agentes)), "Geral")
            with k[2]:
                card_kpi("Sem Classificação", "Sem dado", "Campo ainda não salvo")
            with k[3]:
                card_kpi("Agentes", ranking["Agente"].nunique(), "Com atividade no período")

            c1, c2 = st.columns([1.15, .85])
            with c1:
                titulo_secao("Desempenho por agente — Voz/Chat", "Tabela operacional")
                st.dataframe(
                    ranking,
                    width="stretch",
                    height=420,
                    hide_index=True,
                )

            with c2:
                top = ranking.head(10).sort_values("Atendimentos", ascending=True)
                fig_ag = go.Figure(go.Bar(
                    x=top["Atendimentos"],
                    y=top["Agente"],
                    orientation="h",
                    marker=dict(
                        color=top["Atendimentos"],
                        colorscale=[[0, "#234968"], [.55, "#397AA7"], [1, "#67A7E1"]],
                    ),
                    hovertemplate="<b>%{y}</b><br>%{x} atendimentos<extra></extra>",
                ))
                try:
                    fig_ag.update_traces(marker_cornerradius=6)
                except Exception:
                    pass
                fig_ag = aplicar_tema_grafico(
                    fig_ag,
                    "Ranking de agentes",
                    "Top 10 por volume de atendimentos",
                    x_titulo="Atendimentos",
                    y_titulo="",
                    altura=420,
                )
                fig_ag.update_layout(showlegend=False, hovermode="closest")
                st.plotly_chart(fig_ag, width="stretch", config={"displaylogo": False})

            coluna_class = _coluna_classificacao(agentes)
            titulo_secao(
                "Classificações dos atendimentos",
                "Motivos/categorias mais recorrentes"
            )

            if coluna_class:
                classificacoes = (
                    agentes[coluna_class]
                    .dropna()
                    .astype(str)
                    .str.strip()
                )
                classificacoes = classificacoes[classificacoes != ""]
                cont = classificacoes.value_counts().head(10).sort_values(ascending=True)

                if not cont.empty:
                    fig_c = go.Figure(go.Bar(
                        x=cont.values,
                        y=cont.index,
                        orientation="h",
                        marker=dict(color="#69A9D2"),
                        text=cont.values,
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>%{x} classificações<extra></extra>",
                    ))
                    fig_c = aplicar_tema_grafico(
                        fig_c,
                        "Total de classificações por motivo",
                        "Top 10 classificações do período",
                        x_titulo="Quantidade",
                        y_titulo="",
                        altura=430,
                    )
                    fig_c.update_layout(showlegend=False, hovermode="closest")
                    st.plotly_chart(fig_c, width="stretch", config={"displaylogo": False})
            else:
                st.markdown(
                    '<div class="data-note">O banco atual ainda não possui o campo de Classificação/Motivo. '
                    'Quando incluirmos esse campo na integração, este gráfico será preenchido automaticamente.</div>',
                    unsafe_allow_html=True,
                )

    # =====================================================
    # 5. DADOS
    # =====================================================
    with abas[4]:
        titulo_secao("Dados detalhados", "Registros que alimentam os indicadores acima")
        st.dataframe(df_filtrado, width="stretch", height=520)

    # =====================================================
    # 6. PDF
    # =====================================================
    with abas[5]:
        titulo_secao("Exportar relatório", "Gere o relatório consolidado do período filtrado")
        try:
            buffer_pdf = pdf.gerar_pdf_consolidado(df_filtrado, periodo_str)
            st.download_button(
                "Baixar Relatório em PDF",
                data=buffer_pdf,
                file_name=f"Relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                type="primary",
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

def abrir_pagina(nome):
    st.session_state["pagina"] = nome


def abrir_empresa(empresa_id, empresa_nome):
    st.session_state["pagina"] = "empresa"
    st.session_state["empresa_id"] = empresa_id
    st.session_state["empresa_nome"] = empresa_nome


# ==========================================
# SIDEBAR MODERNA — SOMENTE MÓDULOS
# ==========================================
lista_empresas_banco = carregar_empresas()

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "visao_geral"

# ==========================================================
# MENU LATERAL COM MODO EXPANDIDO / COMPACTO
# ==========================================================
if "menu_compacto" not in st.session_state:
    st.session_state.menu_compacto = False

def alternar_menu_lateral():
    st.session_state.menu_compacto = not st.session_state.menu_compacto

compacto = st.session_state.menu_compacto

# Ajusta a largura real da lateral. No modo compacto os ícones continuam visíveis.
if compacto:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            min-width: 82px !important;
            max-width: 82px !important;
            width: 82px !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: 82px !important;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-left: .55rem !important;
            padding-right: .55rem !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            min-width: 54px !important;
            width: 54px !important;
            height: 48px !important;
            padding: 0 !important;
            justify-content: center !important;
            font-size: 1.28rem !important;
            border-radius: 12px !important;
        }
        [data-testid="stSidebar"] hr {
            margin: .65rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            min-width: 260px !important;
            max-width: 260px !important;
            width: 260px !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: 260px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Botão de recolher/expandir do nosso próprio menu
rotulo_toggle = "›" if compacto else "‹  Recolher"
st.sidebar.button(
    rotulo_toggle,
    key="btn_toggle_menu",
    width="stretch",
    on_click=alternar_menu_lateral,
    help="Expandir menu" if compacto else "Recolher menu",
)

if not compacto:
    st.sidebar.markdown("## Painel Operacional")
    st.sidebar.caption("Central de acompanhamento")
    st.sidebar.markdown("---")

# Símbolos permanecem visíveis no modo compacto
itens_menu = [
    ("▦", "Visão Geral", "visao_geral", "Visão geral do painel"),
    ("▤", "Empresas", "empresas", "Empresas"),
    ("♟", "Agentes", "agentes", "Agentes"),
    ("⇧", "Importar Dados", "importar", "Importar arquivos"),
    ("↺", "Histórico", "historico", "Histórico de importações"),
    ("⚙", "Configurações", "configuracoes", "Configurações"),
]

for simbolo, nome, pagina_destino, ajuda in itens_menu:
    texto_botao = simbolo if compacto else f"{simbolo}   {nome}"
    st.sidebar.button(
        texto_botao,
        key=f"menu_{pagina_destino}",
        width="stretch",
        on_click=abrir_pagina,
        args=(pagina_destino,),
        help=ajuda,
    )

if not compacto:
    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Banco conectado • {len(lista_empresas_banco)} empresas"
        if lista_empresas_banco
        else "Banco sem empresas"
    )

pagina = st.session_state.get("pagina", "visao_geral")


# ==========================================
# PÁGINA: VISÃO GERAL
# ==========================================
if pagina == "visao_geral":
    try:
        with st.spinner("Carregando dados salvos no Supabase..."):
            df_geral = db.consultar_atendimentos()
        renderizar_painel(
            df_geral,
            "Painel Geral das Operações",
            "geral",
            mostrar_empresas=True,
        )
    except Exception as e:
        st.error(f"Não foi possível carregar os dados do banco: {e}")


# ==========================================
# PÁGINA: EMPRESAS
# ==========================================
elif pagina == "empresas":
    cabecalho_pagina("ESTRUTURA", "Empresas", "Escolha uma empresa para abrir o painel individual da operação.")
    if not lista_empresas_banco:
        st.info("Nenhuma empresa cadastrada no banco.")
    else:
        busca = st.text_input("Buscar empresa", placeholder="Digite o nome da empresa...")
        empresas_filtradas = lista_empresas_banco
        if busca.strip():
            termo = busca.strip().lower()
            empresas_filtradas = [e for e in lista_empresas_banco if termo in e["nome"].lower()]
        st.caption(f"{len(empresas_filtradas)} empresa(s)")
        for inicio in range(0, len(empresas_filtradas), 3):
            cols = st.columns(3)
            for col, empresa in zip(cols, empresas_filtradas[inicio:inicio+3]):
                with col:
                    sistemas = []
                    if empresa.get("voz"):
                        sistemas.append("Voz")
                    if empresa.get("chat"):
                        sistemas.append("Chat")
                    meta = " • ".join(sistemas) if sistemas else "Operação cadastrada"
                    st.markdown(
                        f'<div class="company-card"><div class="company-name">{empresa["nome"]}</div><div class="company-meta">{meta}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.button("Abrir painel", key=f'card_{empresa["id"]}', width="stretch", on_click=abrir_empresa, args=(empresa["id"], empresa["nome"]))


# ==========================================
# PÁGINA: AGENTES
# ==========================================
elif pagina == "agentes":
    cabecalho_pagina("PESSOAS", "Agentes", "Área preparada para a lista oficial de agentes e seus indicadores individuais.")
    st.info("A estrutura visual está pronta. Na próxima etapa vamos ligar esta página à base oficial de agentes, sem usar Agente como filtro do painel.")


# ==========================================
# PÁGINA: EMPRESA INDIVIDUAL
# ==========================================
elif pagina == "empresa":
    empresa_id = st.session_state.get("empresa_id")
    empresa_nome = st.session_state.get("empresa_nome", "Empresa")

    if st.button("← Voltar para Empresas"):
        abrir_pagina("empresas")
        st.rerun()

    if not empresa_id:
        st.info("Selecione uma empresa na barra lateral.")
    else:
        try:
            with st.spinner(f"Carregando dados de {empresa_nome}..."):
                df_empresa = db.consultar_atendimentos(empresa_id=empresa_id)

            renderizar_painel(
                df_empresa,
                f"{empresa_nome}",
                f"empresa_{empresa_id}",
                mostrar_empresas=False,
            )

            st.markdown("---")
            st.subheader("Histórico da empresa")
            historico_empresa = db.listar_importacoes(
                empresa_id=empresa_id,
                limite=100,
            )
            if historico_empresa.empty:
                st.info("Nenhuma importação registrada para esta empresa.")
            else:
                st.dataframe(historico_empresa, width="stretch", hide_index=True)

            produtividade = consultar_produtividade_empresa(empresa_id)
            if not produtividade.empty:
                with st.expander("Produtividade agregada salva"):
                    view = produtividade.copy()
                    view["TMA Resolução"] = view["Tempo_Resolucao_Seg"].apply(proc.formatar_segundos_para_hora)
                    view["Primeira Resposta"] = view["Primeira_Resposta_Seg"].apply(proc.formatar_segundos_para_hora)
                    st.dataframe(view, width="stretch", hide_index=True)

            indicadores = consultar_indicadores_empresa(empresa_id)
            if not indicadores.empty:
                with st.expander("Indicadores diários salvos"):
                    view = indicadores.copy()
                    view["TMA"] = view["TMA_Seg"].apply(proc.formatar_segundos_para_hora)
                    view["TME"] = view["TME_Seg"].apply(proc.formatar_segundos_para_hora)
                    st.dataframe(view, width="stretch", hide_index=True)

        except Exception as e:
            st.error(f"Erro ao carregar o painel de {empresa_nome}: {e}")


# ==========================================
# PÁGINA: IMPORTAR DADOS
# ==========================================
elif pagina == "importar":
    cabecalho_pagina("ENTRADA DE DADOS", "Importar Dados", "Envie relatórios para processar e salvar permanentemente no Supabase.")

    arquivos_carregados = st.file_uploader(
        "Carregar Relatórios (Excel ou CSV)",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        key="upload_importacoes",
    )

    if not arquivos_carregados:
        st.info("Selecione uma ou mais planilhas para importar.")
    else:
        with st.spinner("Processando arquivos..."):
            dataframes, dataframes_produtividade, itens_importacao = processar_arquivos_upload(
                arquivos_carregados,
                lista_empresas_banco,
            )

        if not itens_importacao:
            st.error("Nenhum arquivo válido foi identificado.")
        else:
            resumo = []
            for item in itens_importacao:
                empresa_nome = str(item.get("empresa", "")).strip()
                empresa_id = db.obter_id_empresa(empresa_nome)
                duplicado = db.importacao_ja_existe(item.get("hash"))

                if not empresa_id:
                    situacao = "Empresa não cadastrada"
                elif duplicado:
                    situacao = "Já importado"
                else:
                    situacao = "Pronto para salvar"

                resumo.append({
                    "Arquivo": item.get("nome"),
                    "Empresa": empresa_nome,
                    "Tipo": item.get("tipo"),
                    "Canal": item.get("canal"),
                    "Registros": len(item.get("df", pd.DataFrame())),
                    "Situação": situacao,
                })

            st.dataframe(pd.DataFrame(resumo), width="stretch", hide_index=True)

            if st.button("Salvar arquivos no Supabase", type="primary", width="stretch"):
                salvos = 0
                duplicados = 0
                erros = 0
                progresso = st.progress(0)
                total_itens = len(itens_importacao)

                for posicao, item in enumerate(itens_importacao, 1):
                    importacao_id = None
                    nome_arquivo = item.get("nome")
                    try:
                        empresa_nome = str(item.get("empresa", "")).strip()
                        empresa_id = db.obter_id_empresa(empresa_nome)
                        if not empresa_id:
                            raise ValueError(f"Empresa '{empresa_nome}' não cadastrada.")

                        if db.importacao_ja_existe(item.get("hash")):
                            duplicados += 1
                            progresso.progress(posicao / total_itens)
                            continue

                        df_item = item.get("df", pd.DataFrame())
                        data_inicial, data_final = obter_periodo_dataframe(df_item)

                        importacao_id = db.criar_importacao(
                            empresa_id=empresa_id,
                            nome_arquivo=nome_arquivo,
                            tipo_arquivo=item.get("tipo"),
                            canal=item.get("canal"),
                            data_inicial=data_inicial,
                            data_final=data_final,
                            hash_arquivo=item.get("hash"),
                            quantidade_registros=len(df_item),
                            status="processando",
                        )

                        if item.get("destino") == "atendimentos":
                            db.salvar_atendimentos(df_item, empresa_id, importacao_id)
                        elif item.get("destino") == "indicadores":
                            db.salvar_indicadores_diarios(
                                normalizar_indicadores_banco(df_item),
                                empresa_id,
                                importacao_id,
                                canal=item.get("canal") or "Chat",
                            )
                        elif item.get("destino") == "produtividade":
                            db.salvar_produtividade_agentes(
                                df_item,
                                empresa_id,
                                importacao_id,
                                data_inicial=data_inicial,
                                data_final=data_final,
                            )

                        conn = db.obter_conexao()
                        with conn.session as session:
                            session.execute(
                                sql_text("UPDATE importacoes SET status = 'processado' WHERE id = :id"),
                                {"id": importacao_id},
                            )
                            session.commit()
                        salvos += 1

                    except Exception as e:
                        erros += 1
                        excluir_importacao_em_caso_de_erro(importacao_id)
                        st.error(f"Erro em {nome_arquivo}: {e}")

                    progresso.progress(posicao / total_itens)

                if salvos:
                    st.success(f"{salvos} arquivo(s) salvo(s) com sucesso.")
                if duplicados:
                    st.warning(f"{duplicados} arquivo(s) já estavam salvos e foram ignorados.")
                if erros == 0 and salvos > 0:
                    st.info("Os dados já estão disponíveis nos painéis das empresas na barra lateral.")


# ==========================================
# PÁGINA: HISTÓRICO
# ==========================================
elif pagina == "historico":
    cabecalho_pagina("AUDITORIA", "Histórico de Importações", "Acompanhe os arquivos já processados e gravados no banco.")
    try:
        historico = db.listar_importacoes(limite=500)
        if historico.empty:
            st.info("Ainda não existem importações no banco.")
        else:
            st.dataframe(historico, width="stretch", hide_index=True)
    except Exception as e:
        st.error(f"Não foi possível carregar o histórico: {e}")


# ==========================================
# PÁGINA: CONFIGURAÇÕES
# ==========================================
elif pagina == "configuracoes":
    cabecalho_pagina("ADMINISTRAÇÃO", "Configurações", "Cadastros e parâmetros básicos do painel operacional.")
    st.subheader("Empresas cadastradas")

    col_form, col_tabela = st.columns([1, 2])
    with col_form:
        with st.form("form_nova_empresa", clear_on_submit=True):
            novo_nome = st.text_input("Nome da Empresa*")
            novo_tipo = st.selectbox(
                "Grupo/Tipo*",
                ["Lista Principal", "Secundária", "Terceirizada"],
            )
            novo_chat = st.text_input("Plataforma de Chat")
            novo_voz = st.text_input("Sistema de Voz / Telefonia")
            enviar = st.form_submit_button("Salvar Empresa", type="primary")
            if enviar:
                if not novo_nome.strip():
                    st.error("O nome da empresa é obrigatório.")
                else:
                    try:
                        cadastrar_empresa_banco(
                            novo_nome,
                            novo_tipo,
                            novo_voz,
                            novo_chat,
                        )
                        st.success("Empresa cadastrada com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar empresa: {e}")

    with col_tabela:
        empresas_df = pd.DataFrame(lista_empresas_banco)
        if empresas_df.empty:
            st.info("Nenhuma empresa cadastrada.")
        else:
            cols = [c for c in ["id", "nome", "tipo", "voz", "chat", "ativo"] if c in empresas_df.columns]
            st.dataframe(empresas_df[cols], width="stretch", hide_index=True, height=500)

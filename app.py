import streamlit as st
import pandas as pd
import plotly.express as px
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
.stApp { background: #f6f8fc; }
[data-testid="stSidebar"] { background: #111827; border-right: 1px solid #1f2937; }
[data-testid="stSidebar"] * { color: #f9fafb; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent; border: 0; border-radius: 10px;
    padding: .72rem .8rem; justify-content: flex-start; font-weight: 500;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #1f2937; border: 0; }
.block-container { padding-top: 2rem; max-width: 1500px; }
div[data-testid="stMetric"] {
    background: white; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1rem; box-shadow: 0 1px 2px rgba(16,24,40,.04);
}
.company-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 16px;
    padding: 1.1rem; min-height: 112px; box-shadow: 0 1px 2px rgba(16,24,40,.04);
    margin-bottom: .45rem;
}
.company-name { font-size: 1.08rem; font-weight: 700; color: #111827; margin-bottom: .35rem; }
.company-meta { font-size: .86rem; color: #667085; }
.page-kicker { color: #3157f5; font-size: .76rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.page-title { font-size: 2rem; font-weight: 750; color: #111827; line-height: 1.2; margin-top: .25rem; }
.page-subtitle { color: #667085; margin-top: .4rem; margin-bottom: 1.4rem; }
.stTabs [data-baseweb="tab-list"] { background: #fff; border: 1px solid #e5e7eb; padding: .35rem; border-radius: 12px; gap: .35rem; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; padding-left: 1rem; padding-right: 1rem; }
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
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


def cabecalho_pagina(kicker, titulo, subtitulo=""):
    st.markdown(f'<div class="page-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{titulo}</div>', unsafe_allow_html=True)
    if subtitulo:
        st.markdown(f'<div class="page-subtitle">{subtitulo}</div>', unsafe_allow_html=True)


def renderizar_painel(df, titulo, chave, mostrar_empresas=False):
    cabecalho_pagina("PAINEL OPERACIONAL", titulo, "Indicadores consolidados a partir dos dados salvos no Supabase.")

    df = preparar_dataframe_banco(df)
    if df.empty:
        st.info("Nenhum dado importado para esta seleção.")
        return

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

    abas = st.tabs([
        "Visão Executiva",
        "Telefonia e Voz",
        "Mensageria e Chat",
        "Produtividade",
        "Dados",
        "Exportar PDF",
    ])

    with abas[0]:
        metricas = proc.calcular_metricas(df_filtrado)
        total_real = int(df_filtrado.shape[0])
        por_canal = metricas.get("Por Canal", {})
        vol_voz = sum(v for k, v in por_canal.items() if "Voz" in str(k))
        vol_chat = sum(v for k, v in por_canal.items() if "Chat" in str(k))
        sla = metricas.get("SLA (%)")

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Volume Total", total_real)
        c2.metric("% Voz", f"{(vol_voz / total_real * 100):.1f}%" if total_real else "0%")
        c3.metric("% Chat", f"{(vol_chat / total_real * 100):.1f}%" if total_real else "0%")
        c4.metric("TMA Geral", metricas.get("TMA", "00:00:00"))
        c5.metric("TME Geral", metricas.get("TME", "00:00:00"))
        c6.metric("SLA", f"{sla}%" if sla is not None else "Sem dado")

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            diario = (
                df_filtrado.dropna(subset=["Data_Parse"])
                .groupby([df_filtrado["Data_Parse"].dt.date, "Canal"])
                .size()
                .reset_index(name="Volume")
            )
            if not diario.empty:
                fig = px.bar(
                    diario,
                    x="Data_Parse",
                    y="Volume",
                    color="Canal",
                    barmode="group",
                    labels={"Data_Parse": "Data"},
                )
                st.plotly_chart(fig, width="stretch")

        with col_g2:
            def extrair_hora(valor):
                try:
                    if isinstance(valor, str):
                        return int(valor.split(":")[0])
                    if isinstance(valor, time):
                        return valor.hour
                    if hasattr(valor, "hour"):
                        return valor.hour
                except Exception:
                    pass
                return None

            temp = df_filtrado.copy()
            temp["Hora_Inteira"] = temp["Hora"].apply(extrair_hora)
            hora = temp.dropna(subset=["Hora_Inteira"]).groupby("Hora_Inteira").size().reset_index(name="Volume")
            if not hora.empty:
                fig = px.line(hora, x="Hora_Inteira", y="Volume", markers=True)
                st.plotly_chart(fig, width="stretch")

    with abas[1]:
        voz = df_filtrado[df_filtrado["Canal"].astype(str).str.contains("Voz", case=False, na=False)]
        if voz.empty:
            st.info("Nenhum registro de Voz neste período.")
        else:
            abandonadas = voz[voz["Status"].astype(str).str.contains("abandono|abandonada", case=False, na=False)].shape[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Chamadas", voz.shape[0])
            c2.metric("Atendidas", voz.shape[0] - abandonadas)
            c3.metric("Abandonadas", abandonadas)
            c4.metric("TME", proc.formatar_segundos_para_hora(voz["Tempo_Espera_Seg"].mean()))
            c5.metric("TMA", proc.formatar_segundos_para_hora(voz["Tempo_Conversa_Seg"].mean()))
            st.dataframe(voz, width="stretch", height=350)

    with abas[2]:
        chat = df_filtrado[df_filtrado["Canal"].astype(str).str.contains("Chat", case=False, na=False)]
        if chat.empty:
            st.info("Nenhum registro de Chat neste período.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Conversas", chat.shape[0])
            c2.metric("TME", proc.formatar_segundos_para_hora(chat["Tempo_Espera_Seg"].mean()))
            c3.metric("TMA", proc.formatar_segundos_para_hora(chat["Tempo_Conversa_Seg"].mean()))
            st.dataframe(chat, width="stretch", height=350)

    with abas[3]:
        agentes = df_filtrado[
            df_filtrado["Agente"].notna()
            & (df_filtrado["Agente"].astype(str).str.strip() != "")
            & (df_filtrado["Agente"].astype(str) != "Não Informado")
        ]
        if agentes.empty:
            st.info("Não há dados individuais de agentes neste período.")
        else:
            ranking = agentes.groupby("Agente").agg(
                Volume=("Data", "count"),
                TMA_Seg=("Tempo_Conversa_Seg", "mean"),
                TME_Seg=("Tempo_Espera_Seg", "mean"),
            ).reset_index()
            ranking["TMA"] = ranking["TMA_Seg"].apply(proc.formatar_segundos_para_hora)
            ranking["TME"] = ranking["TME_Seg"].apply(proc.formatar_segundos_para_hora)
            ranking = ranking.sort_values("Volume", ascending=False)
            st.dataframe(ranking[["Agente", "Volume", "TMA", "TME"]], width="stretch", hide_index=True)

    with abas[4]:
        st.dataframe(df_filtrado, width="stretch", height=500)

    with abas[5]:
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

st.sidebar.markdown("## Painel Operacional")
st.sidebar.caption("Central de acompanhamento")
st.sidebar.markdown("---")
st.sidebar.button("Visão Geral", width="stretch", on_click=abrir_pagina, args=("visao_geral",))
st.sidebar.button("Empresas", width="stretch", on_click=abrir_pagina, args=("empresas",))
st.sidebar.button("Agentes", width="stretch", on_click=abrir_pagina, args=("agentes",))
st.sidebar.button("Importar Dados", width="stretch", on_click=abrir_pagina, args=("importar",))
st.sidebar.button("Histórico", width="stretch", on_click=abrir_pagina, args=("historico",))
st.sidebar.button("Configurações", width="stretch", on_click=abrir_pagina, args=("configuracoes",))
st.sidebar.markdown("---")
st.sidebar.caption(f"Banco conectado • {len(lista_empresas_banco)} empresas" if lista_empresas_banco else "Banco sem empresas")

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

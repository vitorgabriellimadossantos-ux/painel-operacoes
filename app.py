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
except ImportError:
    st.error("⚠️ Módulos internos não encontrados. Certifique-se de que processamento.py e relatorio_pdf.py estão na mesma pasta.")
    st.stop()

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
    Também relaciona arquivos Volume + Indicadores de uma mesma empresa
    e separa relatórios agregados de produtividade (ex.: LIG TOP).
    """
    brutos = []

    # 1) Lê todos os arquivos primeiro
    for uploaded_file in arquivos:
        try:
            df_bruto = ler_arquivo_upload(uploaded_file)
            if df_bruto.empty:
                continue

            nome_arquivo = uploaded_file.name
            empresa = proc.identificar_empresa_por_arquivo(nome_arquivo, lista_empresas)
            tipo = proc.detectar_tipo_planilha(df_bruto, nome_arquivo)

            brutos.append({
                'nome': nome_arquivo,
                'empresa': empresa,
                'tipo': tipo,
                'df': df_bruto
            })
        except Exception as e:
            st.sidebar.error(f"Erro ao ler {uploaded_file.name}: {e}")

    # 2) Indexa os arquivos de indicadores por empresa
    indicadores_por_empresa = {}
    for item in brutos:
        if item['tipo'] == 'chat_indicadores':
            empresa = item['empresa']
            if empresa == 'EMPRESA NÃO IDENTIFICADA' and 'EMPRESA' in item['df'].columns:
                vals = item['df']['EMPRESA'].dropna().astype(str).str.strip()
                if not vals.empty:
                    empresa = vals.iloc[0]
            indicadores_por_empresa[str(empresa).upper()] = item['df']

    dataframes_atendimentos = []
    dataframes_produtividade = []

    # 3) Processa cada arquivo pelo formato detectado
    for item in brutos:
        nome = item['nome']
        empresa = item['empresa']
        tipo = item['tipo']
        df_bruto = item['df']

        try:
            # Indicadores são auxiliares do Volume; não entram sozinhos no master.
            if tipo == 'chat_indicadores':
                continue

            # LIG TOP é relatório agregado por agente, não atendimento individual.
            if tipo == 'ligtop_agentes':
                df_prod = proc.processar_ligtop_agentes(
                    df_bruto,
                    empresa if empresa != 'EMPRESA NÃO IDENTIFICADA' else 'LIG TOP'
                )
                dataframes_produtividade.append(df_prod)
                continue

            # Para Volume R2/NEX, procura o arquivo de Indicadores correspondente.
            df_indicadores = None
            if tipo == 'chat_volume':
                chave = str(empresa).upper()
                df_indicadores = indicadores_por_empresa.get(chave)

                # Fallback pelo nome da empresa dentro da planilha de indicadores
                if df_indicadores is None:
                    nome_upper = nome.upper()
                    for chave_ind, df_ind in indicadores_por_empresa.items():
                        if chave_ind in nome_upper or nome_upper.split(' - ')[0] in chave_ind:
                            df_indicadores = df_ind
                            break

            df_processado = proc.processar_dataframe_automatico(
                df_bruto,
                nome_arquivo=nome,
                nome_empresa=None if empresa == 'EMPRESA NÃO IDENTIFICADA' else empresa,
                df_indicadores=df_indicadores
            )

            if not df_processado.empty:
                dataframes_atendimentos.append(df_processado)

        except Exception as e:
            st.sidebar.error(f"Erro ao processar {nome}: {e}")

    return dataframes_atendimentos, dataframes_produtividade

# ==========================================
# 2. BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/7901/7901358.png", width=60) # Ícone genérico de dashboard
st.sidebar.title("Configurações")
st.sidebar.markdown("---")

lista_empresas_banco = carregar_empresas()

if lista_empresas_banco:
    st.sidebar.success(f"Banco conectado: {len(lista_empresas_banco)} empresas")
else:
    st.sidebar.warning("Nenhuma empresa ativa foi carregada do banco.")

# Upload Múltiplo
arquivos_carregados = st.sidebar.file_uploader(
    "Carregar Relatórios (Excel ou CSV)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# ==========================================
# TRATAMENTO DE EXCEÇÃO INICIAL (O CURTO-CIRCUITO)
# ==========================================
# Se nenhum arquivo foi carregado, mostramos uma mensagem de boas-vindas e paramos a execução.
if not arquivos_carregados:
    st.title("📊 Painel de Controle Operacional")
    st.info("👋 Bem-vindo ao sistema de relatórios consolidados.")
    st.write("Para começar, utilize a barra lateral à esquerda para fazer o upload dos relatórios exportados das suas plataformas de Voz e Chat.")
    st.stop() # INTERROMPE A EXECUÇÃO AQUI. Impede erros de DataFrames vazios abaixo.

# Se chegou aqui, temos arquivos. Vamos processá-los.
with st.spinner('Processando e unificando relatórios...'):
    dataframes, dataframes_produtividade = processar_arquivos_upload(
        arquivos_carregados,
        lista_empresas_banco
    )

if not dataframes and not dataframes_produtividade:
    st.error("Não foi possível extrair dados válidos dos arquivos enviados. Verifique os formatos.")
    st.stop()

# Concatena os atendimentos em um ÚNICO DataFrame Master
if dataframes:
    df_master = pd.concat(dataframes, ignore_index=True)
else:
    df_master = pd.DataFrame(columns=proc.COLUNAS_PADRAO)

# Relatórios agregados de produtividade ficam separados do volume de atendimentos
if dataframes_produtividade:
    df_produtividade_extra = pd.concat(dataframes_produtividade, ignore_index=True)
else:
    df_produtividade_extra = pd.DataFrame()

# Garante que Data seja formato Datetime para os filtros
df_master['Data_Parse'] = pd.to_datetime(df_master['Data'], errors='coerce')

st.sidebar.markdown("### Filtros de Análise")

# Filtro de Data
min_date = df_master['Data_Parse'].min().date() if not pd.isna(df_master['Data_Parse'].min()) else datetime.today().date()
max_date = df_master['Data_Parse'].max().date() if not pd.isna(df_master['Data_Parse'].max()) else datetime.today().date()

datas_selecionadas = st.sidebar.date_input(
    "Período de Análise",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filtro de Empresa
empresas_disponiveis = df_master['Empresa'].dropna().unique().tolist()
empresas_selecionadas = st.sidebar.multiselect("Empresas", empresas_disponiveis, default=empresas_disponiveis)

# Filtro de Canal
canais_disponiveis = df_master['Canal'].dropna().unique().tolist()
canais_selecionados = st.sidebar.multiselect("Canal", canais_disponiveis, default=canais_disponiveis)

# Filtro de Agente
agentes_disponiveis = sorted(df_master['Agente'].dropna().astype(str).unique().tolist())
agentes_selecionados = st.sidebar.multiselect("Agentes", agentes_disponiveis)

# Aplicando os filtros matematicamente
df_filtrado = df_master.copy()

if len(datas_selecionadas) == 2:
    start_d, end_d = datas_selecionadas
    df_filtrado = df_filtrado[(df_filtrado['Data_Parse'].dt.date >= start_d) & (df_filtrado['Data_Parse'].dt.date <= end_d)]

if empresas_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Empresa'].isin(empresas_selecionadas)]

if canais_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Canal'].isin(canais_selecionados)]

if agentes_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Agente'].isin(agentes_selecionados)]

st.title("📊 Painel de Controle Operacional")
periodo_str = f"{datas_selecionadas[0].strftime('%d/%m/%Y')} a {datas_selecionadas[1].strftime('%d/%m/%Y')}" if len(datas_selecionadas) == 2 else "Período Único"
st.caption(f"Dados consolidados para o período: {periodo_str}")

# Prepara abas
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "📈 Visão Executiva", 
    "📞 Telefonia e Voz", 
    "💬 Mensageria e Chat", 
    "👥 Produtividade (Agentes)", 
    "📄 Exportar Relatórios", 
    "⚙️ Gerenciar Empresas"
])

# ==========================================
# 3. ABA 1 - VISÃO EXECUTIVA
# ==========================================
with aba1:
    if df_filtrado.empty:
        st.warning("Não há dados para os filtros selecionados.")
    else:
        # Pega as métricas do processamento.py
        metricas = proc.calcular_metricas(df_filtrado)
        
        # Ajusta cálculo percentual de Canais
        total = metricas.get("Total de Atendimentos", 1)
        total = total if total > 0 else 1
        vol_voz = sum([v for k, v in metricas.get("Por Canal", {}).items() if 'Voz' in k])
        vol_chat = sum([v for k, v in metricas.get("Por Canal", {}).items() if 'Chat' in k])
        
        # Cards (st.metric)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Volume Total", total)
        c2.metric("% Voz", f"{(vol_voz/total)*100:.1f}%", f"{vol_voz} chamadas")
        c3.metric("% Chat", f"{(vol_chat/total)*100:.1f}%", f"{vol_chat} conversas")
        c4.metric("TMA Geral", metricas.get("TMA", "00:00:00"))
        c5.metric("TME Geral", metricas.get("TME", "00:00:00"))
        sla_valor = metricas.get('SLA (%)')
        c6.metric("SLA Atingido", f"{sla_valor}%" if sla_valor is not None else "Sem dado")
        
        st.markdown("---")
        
        # Gráficos
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("**Volume Diário por Canal**")
            df_diario = df_filtrado.groupby([df_filtrado['Data_Parse'].dt.date, 'Canal']).size().reset_index(name='Volume')
            if not df_diario.empty:
                fig_bar = px.bar(df_diario, x='Data_Parse', y='Volume', color='Canal', barmode='group', 
                                 labels={'Data_Parse': 'Data', 'Volume': 'Qtd Atendimentos'},
                                 color_discrete_sequence=['#1f77b4', '#ff7f0e'])
                fig_bar.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_graf2:
            st.markdown("**Distribuição por Faixa de Horário (Mapa de Calor)**")
            # Extraindo a hora (tentativa segura)
            def extrair_hora(h):
                try:
                    if isinstance(h, str): return int(h.split(':')[0])
                    elif isinstance(h, time): return h.hour
                    else: return 0
                except: return 0
                
            df_filtrado['Hora_Inteira'] = df_filtrado['Hora'].apply(extrair_hora)
            df_hora = df_filtrado.groupby('Hora_Inteira').size().reset_index(name='Volume')
            
            if not df_hora.empty:
                fig_line = px.line(df_hora, x='Hora_Inteira', y='Volume', markers=True,
                                   labels={'Hora_Inteira': 'Hora do Dia (0-23)', 'Volume': 'Pico de Chamadas'},
                                   line_shape='spline')
                fig_line.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                fig_line.update_traces(line_color='#2ca02c', fill='tozeroy')
                st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# 4. ABA 2 - TELEFONIA E VOZ
# ==========================================
with aba2:
    df_voz = df_filtrado[df_filtrado['Canal'].str.contains('Voz', case=False, na=False)]
    
    if df_voz.empty:
        st.info("Nenhum registro de Voz encontrado neste período/filtro.")
    else:
        st.subheader("Indicadores Exclusivos de Voz")
        
        # Filtra status para ver o que é atendimento e o que é abandono
        abandonadas = df_voz[df_voz['Status'].astype(str).str.contains('abandono|abandonada', case=False)].shape[0]
        atendidas = df_voz.shape[0] - abandonadas
        tme_voz = proc.formatar_segundos_para_hora(df_voz['Tempo_Espera_Seg'].mean())
        tma_voz = proc.formatar_segundos_para_hora(df_voz['Tempo_Conversa_Seg'].mean())
        
        cv1, cv2, cv3, cv4, cv5 = st.columns(5)
        cv1.metric("Total Chamadas", df_voz.shape[0])
        cv2.metric("Atendidas", atendidas)
        cv3.metric("Abandonadas", abandonadas, f"{(abandonadas/df_voz.shape[0])*100:.1f}%", delta_color="inverse")
        cv4.metric("TME (Fila)", tme_voz)
        cv5.metric("TMA (Conversa)", tma_voz)
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown("**Distribuição por Fila**")
            df_fila = df_voz['Fila'].value_counts().reset_index()
            df_fila.columns = ['Fila', 'Volume']
            fig_fila = px.bar(df_fila, x='Fila', y='Volume', color='Fila')
            st.plotly_chart(fig_fila, use_container_width=True)
            
        with col_v2:
            st.markdown("**Motivos de Status**")
            df_status = df_voz['Status'].value_counts().reset_index()
            df_status.columns = ['Status', 'Quantidade']
            fig_status = px.pie(df_status, names='Status', values='Quantidade', hole=0.4)
            st.plotly_chart(fig_status, use_container_width=True)
            
        st.markdown("**Detalhamento de Registros (Busca)**")
        busca_protocolo = st.text_input("Buscar por Protocolo (Voz):")
        df_tabela_voz = df_voz.copy()
        if busca_protocolo:
            df_tabela_voz = df_tabela_voz[df_tabela_voz['Protocolo'].astype(str).str.contains(busca_protocolo)]
        st.dataframe(df_tabela_voz, use_container_width=True, height=200)

# ==========================================
# 5. ABA 3 - MENSAGERIA E CHAT
# ==========================================
with aba3:
    df_chat = df_filtrado[df_filtrado['Canal'].str.contains('Chat', case=False, na=False)]
    
    if df_chat.empty:
        st.info("Nenhum registro de Chat encontrado neste período/filtro.")
    else:
        st.subheader("Indicadores Exclusivos de Chat")
        
        tme_chat = proc.formatar_segundos_para_hora(df_chat['Tempo_Espera_Seg'].mean())
        tma_chat = proc.formatar_segundos_para_hora(df_chat['Tempo_Conversa_Seg'].mean())
        
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Total Conversas", df_chat.shape[0])
        cc2.metric("Tempo Médio de Fila", tme_chat)
        cc3.metric("TMA (Resolução)", tma_chat)
        
        st.markdown("**Comparativo entre Plataformas de Chat**")
        df_plat = df_chat['Canal'].value_counts().reset_index()
        df_plat.columns = ['Plataforma', 'Volume']
        fig_plat = px.bar(df_plat, y='Plataforma', x='Volume', orientation='h', color='Plataforma')
        st.plotly_chart(fig_plat, use_container_width=True)
        
        st.markdown("**Detalhamento de Registros (Chat)**")
        st.dataframe(df_chat, use_container_width=True, height=250)

# ==========================================
# 6. ABA 4 - PRODUTIVIDADE DOS AGENTES
# ==========================================
with aba4:
    st.subheader("Ranking e Performance da Equipe")
    
    # Filtra vazios
    df_agentes = df_filtrado[df_filtrado['Agente'].astype(str).str.strip() != '']
    df_agentes = df_agentes[df_agentes['Agente'] != 'Não Informado']
    
    if df_agentes.empty:
        st.info("Não há dados suficientes de Agentes para gerar o ranking.")
    else:
        # Agrupa e calcula
        ranking = df_agentes.groupby('Agente').agg(
            Volume=('Data', 'count'),
            TMA_Seg=('Tempo_Conversa_Seg', 'mean'),
            SLA_Atingido=('Nivel_Servico', lambda x: x.astype(str).str.contains('dentro|sim|atingido', case=False).sum())
        ).reset_index()
        
        # Formatação
        ranking['TMA'] = ranking['TMA_Seg'].apply(proc.formatar_segundos_para_hora)
        ranking['Conformidade (%)'] = round((ranking['SLA_Atingido'] / ranking['Volume']) * 100, 1)
        ranking = ranking.sort_values(by='Volume', ascending=False)
        
        col_r1, col_r2 = st.columns([2, 3])
        
        with col_r1:
            st.markdown("**Top 10 Operadores (Volume)**")
            top10 = ranking.head(10)
            fig_top = px.bar(top10, x='Volume', y='Agente', orientation='h', text='Volume')
            fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_top, use_container_width=True)
            
        with col_r2:
            st.markdown("**Tabela Completa de Produtividade**")
            st.dataframe(
                ranking[['Agente', 'Volume', 'TMA', 'Conformidade (%)']],
                use_container_width=True,
                height=350
            )


    # Relatórios agregados adicionais (ex.: LIG TOP)
    if not df_produtividade_extra.empty:
        st.markdown("---")
        st.subheader("Produtividade por Plataforma / Relatório Agregado")

        df_prod_view = df_produtividade_extra.copy()
        if empresas_selecionadas:
            df_prod_view = df_prod_view[df_prod_view['Empresa'].isin(empresas_selecionadas)]

        if not df_prod_view.empty:
            df_prod_view['Tempo médio de resolução'] = df_prod_view['Tempo_Resolucao_Seg'].apply(proc.formatar_segundos_para_hora)
            df_prod_view['Tempo médio de primeira resposta'] = df_prod_view['Primeira_Resposta_Seg'].apply(proc.formatar_segundos_para_hora)
            df_prod_view['Tempo médio de espera do cliente'] = df_prod_view['Espera_Cliente_Seg'].apply(proc.formatar_segundos_para_hora)

            st.dataframe(
                df_prod_view[[
                    'Empresa', 'Agente', 'Conversas_Atribuidas', 'Resolvidos',
                    'Tempo médio de primeira resposta',
                    'Tempo médio de resolução',
                    'Tempo médio de espera do cliente'
                ]],
                use_container_width=True,
                height=350
            )

# ==========================================
# 7. ABA 5 - EXPORTAÇÃO DE RELATÓRIOS
# ==========================================
with aba5:
    st.subheader("Exportar Documento Oficial")
    st.write("Gere um relatório em PDF consolidado com todos os dados e filtros atualmente aplicados na barra lateral.")
    
    st.info(f"O documento incluirá **{df_filtrado.shape[0]} atendimentos** referentes ao período de **{periodo_str}**.")
    
    # Botão de download
    if not df_filtrado.empty:
        # Só gera o PDF em memória quando o botão é renderizado
        try:
            buffer_pdf = pdf.gerar_pdf_consolidado(df_filtrado, periodo_str)
            
            st.download_button(
                label="📥 Baixar Relatório em PDF",
                data=buffer_pdf,
                file_name=f"Relatorio_Consolidado_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        except Exception as e:
            st.error(f"Erro ao gerar o documento PDF: {e}")
    else:
        st.warning("Não há dados para exportar. Remova alguns filtros.")

# ==========================================
# 8. ABA 6 - GERENCIAMENTO DE EMPRESAS
# ==========================================
with aba6:
    st.subheader("Base de Operações Cadastradas")
    
    col_form, col_table = st.columns([1, 2])
    
    with col_form:
        st.markdown("**Cadastrar Nova Operação**")
        with st.form("form_nova_empresa", clear_on_submit=True):
            novo_nome = st.text_input("Nome da Empresa*", max_chars=100)
            novo_tipo = st.selectbox("Grupo/Tipo*", ["Lista Principal", "Secundária", "Terceirizada"])
            novo_chat = st.text_input("Plataforma de Chat")
            novo_voz = st.text_input("Sistema de Voz / Telefonia")
            
            submit_empresa = st.form_submit_button("Salvar Empresa", type="primary")
            
            if submit_empresa:
                if not novo_nome.strip():
                    st.error("O Nome da Empresa é obrigatório!")
                else:
                    try:
                        cadastrar_empresa_banco(
                            nome=novo_nome,
                            tipo=novo_tipo,
                            sistema_voz=novo_voz,
                            sistema_chat=novo_chat
                        )
                        st.success(f"Empresa '{novo_nome}' adicionada com sucesso no Supabase!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar a empresa no Supabase: {e}")
                        
    with col_table:
        st.markdown("**Empresas Ativas**")
        df_empresas_view = pd.DataFrame(lista_empresas_banco)
        if not df_empresas_view.empty:
            colunas_exibir = ["id", "nome", "tipo", "voz", "chat", "ativo"]
            colunas_exibir = [c for c in colunas_exibir if c in df_empresas_view.columns]
            st.dataframe(
                df_empresas_view[colunas_exibir],
                width="stretch",
                height=400,
                hide_index=True
            )
        else:
            st.info("Nenhuma empresa cadastrada no Supabase.")

# Fim da execução principal

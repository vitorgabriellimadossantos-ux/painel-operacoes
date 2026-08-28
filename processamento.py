
import pandas as pd
import numpy as np
import re
import datetime
import unicodedata

COLUNAS_PADRAO = [
    'Empresa', 'Canal', 'Data', 'Hora', 'Horario_Critico',
    'Fila', 'Agente', 'Tempo_Espera_Seg', 'Tempo_Conversa_Seg',
    'Status', 'Nivel_Servico', 'Protocolo'
]

def _limpar_colunas(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def converter_para_segundos(valor_tempo):
    """Converte durações variadas para segundos."""
    if valor_tempo is None:
        return 0
    try:
        if pd.isna(valor_tempo):
            return 0
    except Exception:
        pass

    if isinstance(valor_tempo, pd.Timedelta):
        return int(valor_tempo.total_seconds())
    if isinstance(valor_tempo, datetime.timedelta):
        return int(valor_tempo.total_seconds())
    if isinstance(valor_tempo, datetime.time):
        return valor_tempo.hour * 3600 + valor_tempo.minute * 60 + valor_tempo.second

    if isinstance(valor_tempo, (np.integer, int)):
        return int(valor_tempo)
    if isinstance(valor_tempo, (np.floating, float)):
        if np.isnan(valor_tempo):
            return 0
        # Excel pode representar horário/duração como fração de um dia.
        if 0 <= float(valor_tempo) < 1:
            return int(round(float(valor_tempo) * 86400))
        return int(valor_tempo)

    texto = str(valor_tempo).strip()
    if not texto or texto.lower() in {'nan', 'nat', 'none', 'n/a', 'na', '-'}:
        return 0

    # Pandas timedelta: "0 days 00:22:49", "1 day 02:00:00"
    if re.search(r'\bday[s]?\b', texto, flags=re.I):
        try:
            return int(pd.to_timedelta(texto).total_seconds())
        except Exception:
            pass

    # Formatos HH:MM:SS / MM:SS
    if ':' in texto:
        try:
            partes = texto.split(':')
            if len(partes) == 3:
                h, m, s = partes
                return int(float(h)) * 3600 + int(float(m)) * 60 + int(float(s))
            if len(partes) == 2:
                m, s = partes
                return int(float(m)) * 60 + int(float(s))
        except (ValueError, TypeError):
            pass

    # Formatos em português: "1 dia 6 horas", "13 minutos 43 segundos"
    unidades = {
        'dia': 86400, 'dias': 86400,
        'hora': 3600, 'horas': 3600,
        'minuto': 60, 'minutos': 60,
        'segundo': 1, 'segundos': 1,
    }
    achados = re.findall(
        r'(\d+(?:[.,]\d+)?)\s*(dias?|horas?|minutos?|segundos?)',
        texto.lower()
    )
    if achados:
        total = 0.0
        for numero, unidade in achados:
            total += float(numero.replace(',', '.')) * unidades[unidade]
        return int(round(total))

    # Número em texto
    try:
        n = float(texto.replace(',', '.'))
        if 0 <= n < 1:
            return int(round(n * 86400))
        return int(n)
    except ValueError:
        return 0

def formatar_segundos_para_hora(segundos_totais):
    if segundos_totais is None or pd.isna(segundos_totais) or segundos_totais < 0:
        return "00:00:00"
    segundos_totais = int(round(float(segundos_totais)))
    horas = segundos_totais // 3600
    minutos = (segundos_totais % 3600) // 60
    segundos = segundos_totais % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

def identificar_empresa_por_arquivo(nome_arquivo, lista_empresas_json):
    nome_arquivo_limpo = str(nome_arquivo).upper()
    for empresa in lista_empresas_json:
        nome_empresa = str(empresa.get('nome', '')).upper()
        if nome_empresa and nome_empresa in nome_arquivo_limpo:
            return empresa['nome']
    return "EMPRESA NÃO IDENTIFICADA"

def _empresa_por_dados_ou_nome(df, nome_arquivo="", nome_empresa=None):
    if nome_empresa and nome_empresa != "EMPRESA NÃO IDENTIFICADA":
        return nome_empresa

    for col in ['Empresa', 'EMPRESA']:
        if col in df.columns:
            vals = df[col].dropna().astype(str).str.strip()
            vals = vals[vals != '']
            if not vals.empty:
                return vals.iloc[0]

    nome = str(nome_arquivo).upper()
    aliases = [
        ('AGE', 'AGE FIBRA'), ('NETFREE', 'NETFREE'), ('WEB LINK', 'WEB LINK'),
        ('WEBLINK', 'WEB LINK'), ('NEX TELECOM', 'NEX TELECOM'),
        ('R2 TELECOM', 'R2 TELECOM'), ('LIG TOP', 'LIG TOP'),
    ]
    for chave, empresa in aliases:
        if chave in nome:
            return empresa
    return "EMPRESA NÃO IDENTIFICADA"

def padronizar_dataframe(df):
    df = df.copy()
    for col in COLUNAS_PADRAO:
        if col not in df.columns:
            if col in ['Tempo_Espera_Seg', 'Tempo_Conversa_Seg']:
                df[col] = 0
            elif col == 'Nivel_Servico':
                # Ausência de SLA não deve virar falha (0).
                df[col] = np.nan
            else:
                df[col] = "Não Informado"

    # Tipos mínimos
    df['Tempo_Espera_Seg'] = pd.to_numeric(df['Tempo_Espera_Seg'], errors='coerce').fillna(0)
    df['Tempo_Conversa_Seg'] = pd.to_numeric(df['Tempo_Conversa_Seg'], errors='coerce').fillna(0)
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    return df[COLUNAS_PADRAO]

def detectar_tipo_planilha(df, nome_arquivo=""):
    df = _limpar_colunas(df)
    cols = set(df.columns)
    nome = str(nome_arquivo).upper()

    if {'DATA', 'EMPRESA', 'TMA', 'TME', 'TMR', 'ATENDIMENTOS'}.issubset(cols):
        return 'chat_indicadores'

    if {'Empresa', 'Canal', 'Data', 'Hora', 'Status'}.issubset(cols) and 'CHAT' in nome:
        return 'chat_volume'

    if {'Empresa', 'Canal', 'Data', 'Hora', 'Status'}.issubset(cols):
        # Pelos arquivos reais R2/NEX de volume, o próprio campo Canal informa Chat.
        canais = df['Canal'].dropna().astype(str).str.lower()
        if not canais.empty and canais.str.contains('chat').mean() > 0.5:
            return 'chat_volume'

    if {'Data do Atendimento', 'Horário', 'Status', 'SLA', 'TMA', 'TME'}.issubset(cols):
        return 'chat_weblink'

    if {'Data do Chat', 'Nome da Fila', 'Nome do Agente', 'Tempo de espera', 'Tempo de conversa', 'Status do Chat'}.issubset(cols):
        return 'chat_padrao'

    if {'Data do Atendimento', 'Hora do Atendimento', 'Fila', 'Agente', 'Tempo de espera', 'Tempo de conversa', 'Status da Chamada'}.issubset(cols):
        return 'voz_padrao'

    if {'Data', 'Hora', 'Fila', 'Agente', 'Tempo de espera', 'Tempo de conversa', 'Status da Chamada'}.issubset(cols):
        return 'voz_consolidada'

    if {'Nome do Agente', 'Conversas atribuídas', 'Tempo médio de resolução', 'Contagem de Resolução'}.issubset(cols):
        return 'ligtop_agentes'

    return 'desconhecido'

def processar_voz_vonix(df_bruto, nome_empresa=None):
    # Compatibilidade com versões antigas do app.py:
    # se o app chamar esta função para uma planilha de Chat, redireciona pelo formato.
    tipo_real = detectar_tipo_planilha(df_bruto)
    if tipo_real == 'chat_weblink':
        return processar_chat_weblink(df_bruto, nome_empresa)
    if tipo_real == 'chat_padrao':
        return processar_chat_padrao(df_bruto, nome_empresa)
    if tipo_real == 'chat_volume':
        return processar_chat_volume(df_bruto, nome_empresa)

    df = _limpar_colunas(df_bruto)
    mapa = {
        'Data do Atendimento': 'Data',
        'Hora do Atendimento': 'Hora',
        'Horário crítico': 'Horario_Critico',
        'Fila': 'Fila',
        'Agente': 'Agente',
        'Nível de serviço': 'Nivel_Servico',
        'Tempo de espera': 'Tempo_Espera_Seg',
        'Tempo de conversa': 'Tempo_Conversa_Seg',
        'Status da Chamada': 'Status',
        'Protocolo': 'Protocolo',
    }
    df = df.rename(columns=mapa)
    empresa = nome_empresa or (
        df['Fila'].dropna().astype(str).iloc[0] if 'Fila' in df.columns and not df['Fila'].dropna().empty else "EMPRESA NÃO IDENTIFICADA"
    )
    df['Empresa'] = empresa
    df['Canal'] = 'Voz'
    df['Tempo_Espera_Seg'] = df.get('Tempo_Espera_Seg', 0).apply(converter_para_segundos)
    df['Tempo_Conversa_Seg'] = df.get('Tempo_Conversa_Seg', 0).apply(converter_para_segundos)
    return padronizar_dataframe(df)

def processar_voz_consolidada(df_bruto, nome_empresa=None):
    df = _limpar_colunas(df_bruto)
    mapa = {
        'Horário crítico': 'Horario_Critico',
        'Nível de serviço': 'Nivel_Servico',
        'Tempo de espera': 'Tempo_Espera_Seg',
        'Tempo de conversa': 'Tempo_Conversa_Seg',
        'Status da Chamada': 'Status',
    }
    df = df.rename(columns=mapa)
    if nome_empresa:
        df['Empresa'] = nome_empresa
    elif 'Fila' in df.columns:
        df['Empresa'] = df['Fila'].astype(str)
    else:
        df['Empresa'] = "EMPRESA NÃO IDENTIFICADA"
    df['Canal'] = 'Voz'
    df['Tempo_Espera_Seg'] = df.get('Tempo_Espera_Seg', 0).apply(converter_para_segundos)
    df['Tempo_Conversa_Seg'] = df.get('Tempo_Conversa_Seg', 0).apply(converter_para_segundos)
    return padronizar_dataframe(df)

def processar_chat_padrao(df_bruto, nome_empresa=None):
    df = _limpar_colunas(df_bruto)
    mapa = {
        'Data do Chat': 'Data',
        'Hora do Chat': 'Hora',
        'Horário crítico': 'Horario_Critico',
        'Nome da Fila': 'Fila',
        'Nome do Agente': 'Agente',
        'Nível de serviço': 'Nivel_Servico',
        'Tempo de espera': 'Tempo_Espera_Seg',
        'Tempo de conversa': 'Tempo_Conversa_Seg',
        'Status do Chat': 'Status',
        'Protocolo': 'Protocolo',
    }
    df = df.rename(columns=mapa)
    empresa = nome_empresa
    if not empresa:
        if 'Fila' in df.columns and not df['Fila'].dropna().empty:
            fila = str(df['Fila'].dropna().iloc[0]).upper()
            if 'AGE' in fila:
                empresa = 'AGE FIBRA'
            elif 'NETFREE' in fila:
                empresa = 'NETFREE'
    df['Empresa'] = empresa or "EMPRESA NÃO IDENTIFICADA"
    df['Canal'] = 'Chat'
    df['Tempo_Espera_Seg'] = df.get('Tempo_Espera_Seg', 0).apply(converter_para_segundos)
    df['Tempo_Conversa_Seg'] = df.get('Tempo_Conversa_Seg', 0).apply(converter_para_segundos)
    return padronizar_dataframe(df)

def processar_chat_weblink(df_bruto, nome_empresa=None):
    df = _limpar_colunas(df_bruto)
    mapa = {
        'Data do Atendimento': 'Data',
        'Horário': 'Hora',
        'Horário Crítico': 'Horario_Critico',
        'SLA': 'Nivel_Servico',
        'TMA': 'Tempo_Conversa_Seg',
        'TME': 'Tempo_Espera_Seg',
    }
    df = df.rename(columns=mapa)
    df['Empresa'] = nome_empresa or _empresa_por_dados_ou_nome(df, 'WEB LINK')
    df['Canal'] = 'Chat'
    df['Tempo_Espera_Seg'] = df['Tempo_Espera_Seg'].apply(converter_para_segundos)
    df['Tempo_Conversa_Seg'] = df['Tempo_Conversa_Seg'].apply(converter_para_segundos)
    return padronizar_dataframe(df)

def processar_chat_volume(df_volume, nome_empresa=None, df_indicadores=None):
    df = _limpar_colunas(df_volume)
    df = df.rename(columns={'Horário Crítico': 'Horario_Critico'})
    empresa = nome_empresa or _empresa_por_dados_ou_nome(df)
    df['Empresa'] = empresa
    df['Canal'] = 'Chat'

    # Sem indicadores, volume continua válido e TMA/TME ficam sem valor agregado.
    df['Tempo_Espera_Seg'] = np.nan
    df['Tempo_Conversa_Seg'] = np.nan
    df['Nivel_Servico'] = np.nan

    if df_indicadores is not None and len(df_indicadores) > 0:
        ind = _limpar_colunas(df_indicadores)
        ind = ind.rename(columns={
            'DATA': 'Data',
            'EMPRESA': 'Empresa_Indicador',
            'TMA': 'Tempo_Conversa_Seg_Indicador',
            'TME': 'Tempo_Espera_Seg_Indicador'
        })
        ind['Data'] = pd.to_datetime(ind['Data'], errors='coerce').dt.normalize()
        ind['Tempo_Conversa_Seg_Indicador'] = ind['Tempo_Conversa_Seg_Indicador'].apply(converter_para_segundos)
        ind['Tempo_Espera_Seg_Indicador'] = ind['Tempo_Espera_Seg_Indicador'].apply(converter_para_segundos)

        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.normalize()
        # Cada atendimento do dia recebe a média diária. A média mensal resultante
        # fica ponderada pelo volume diário.
        ind2 = ind[['Data', 'Tempo_Conversa_Seg_Indicador', 'Tempo_Espera_Seg_Indicador']].drop_duplicates('Data')
        df = df.merge(ind2, on='Data', how='left')
        df['Tempo_Conversa_Seg'] = df['Tempo_Conversa_Seg_Indicador']
        df['Tempo_Espera_Seg'] = df['Tempo_Espera_Seg_Indicador']
        df = df.drop(columns=['Tempo_Conversa_Seg_Indicador', 'Tempo_Espera_Seg_Indicador'], errors='ignore')

    return padronizar_dataframe(df)

def processar_indicadores_chat(df_indicadores):
    """Retorna indicadores diários em formato auxiliar."""
    df = _limpar_colunas(df_indicadores)
    df = df.rename(columns={'DATA': 'Data', 'EMPRESA': 'Empresa'})
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    for col in ['TMA', 'TME', 'TMR']:
        if col in df.columns:
            df[col + '_Seg'] = df[col].apply(converter_para_segundos)
    if 'ATENDIMENTOS' in df.columns:
        df['ATENDIMENTOS'] = pd.to_numeric(df['ATENDIMENTOS'], errors='coerce').fillna(0).astype(int)
    return df

def processar_ligtop_agentes(df_bruto, nome_empresa='LIG TOP'):
    """Relatório agregado de produtividade; não deve entrar no volume por atendimento."""
    df = _limpar_colunas(df_bruto)
    df['Empresa'] = nome_empresa
    df['Canal'] = 'Chat'
    df['Agente'] = df['Nome do Agente'].astype(str)
    df['Conversas_Atribuidas'] = pd.to_numeric(df['Conversas atribuídas'], errors='coerce').fillna(0).astype(int)
    df['Resolvidos'] = pd.to_numeric(df['Contagem de Resolução'], errors='coerce').fillna(0).astype(int)
    df['Primeira_Resposta_Seg'] = df['Tempo médio de primeira resposta'].apply(converter_para_segundos)
    df['Tempo_Resolucao_Seg'] = df['Tempo médio de resolução'].apply(converter_para_segundos)
    df['Espera_Cliente_Seg'] = df['Tempo médio de espera do cliente'].apply(converter_para_segundos)
    return df[
        ['Empresa', 'Canal', 'Agente', 'Conversas_Atribuidas', 'Resolvidos',
         'Primeira_Resposta_Seg', 'Tempo_Resolucao_Seg', 'Espera_Cliente_Seg']
    ]

def processar_dataframe_automatico(df_bruto, nome_arquivo="", nome_empresa=None, df_indicadores=None):
    tipo = detectar_tipo_planilha(df_bruto, nome_arquivo)

    if tipo == 'voz_padrao':
        return processar_voz_vonix(df_bruto, nome_empresa)
    if tipo == 'voz_consolidada':
        return processar_voz_consolidada(df_bruto, nome_empresa)
    if tipo == 'chat_padrao':
        return processar_chat_padrao(df_bruto, nome_empresa)
    if tipo == 'chat_weblink':
        return processar_chat_weblink(df_bruto, nome_empresa)
    if tipo == 'chat_volume':
        return processar_chat_volume(df_bruto, nome_empresa, df_indicadores)
    if tipo == 'chat_indicadores':
        return processar_indicadores_chat(df_bruto)
    if tipo == 'ligtop_agentes':
        return processar_ligtop_agentes(df_bruto, nome_empresa or 'LIG TOP')

    raise ValueError(f"Formato de planilha não reconhecido: {nome_arquivo}")

def processar_chat(df_bruto, nome_empresa, ferramenta_chat=None):
    """Mantém compatibilidade com o app antigo, roteando pela estrutura real."""
    tipo = detectar_tipo_planilha(df_bruto)
    if tipo == 'chat_weblink':
        return processar_chat_weblink(df_bruto, nome_empresa)
    if tipo == 'chat_padrao':
        return processar_chat_padrao(df_bruto, nome_empresa)
    if tipo == 'chat_volume':
        return processar_chat_volume(df_bruto, nome_empresa)
    # Fallback genérico conservador
    df = _limpar_colunas(df_bruto)
    df['Empresa'] = nome_empresa
    df['Canal'] = 'Chat'
    for col in df.columns:
        c = col.lower()
        if 'agente' in c or 'atendente' in c or 'operador' in c:
            df['Agente'] = df[col]
            break
    return padronizar_dataframe(df)

def calcular_metricas(df_consolidado):
    total_atendimentos = len(df_consolidado)
    if total_atendimentos == 0:
        return {"Erro": "Não há dados para calcular."}

    total_por_canal = df_consolidado['Canal'].value_counts().to_dict()

    conversa = pd.to_numeric(df_consolidado['Tempo_Conversa_Seg'], errors='coerce')
    espera = pd.to_numeric(df_consolidado['Tempo_Espera_Seg'], errors='coerce')

    # Zeros legítimos são mantidos. NaN significa informação indisponível.
    tma_segundos = conversa.mean(skipna=True)
    tme_segundos = espera.mean(skipna=True)

    status = df_consolidado['Status'].astype(str)
    abandonos = status.str.contains(
        'abandono|abandonada|perdida|cancelada', case=False, na=False
    ).sum()
    taxa_abandono = (abandonos / total_atendimentos) * 100

    ns = df_consolidado['Nivel_Servico']
    ns_num = pd.to_numeric(ns, errors='coerce')
    validos_num = ns_num.notna()

    if validos_num.any():
        # Arquivos reais usam 0/1.
        percentual_sla = (ns_num[validos_num] > 0).mean() * 100
    else:
        ns_txt = ns.astype(str).str.strip()
        validos_txt = ~ns_txt.str.lower().isin(['nan', 'none', 'não informado', ''])
        if validos_txt.any():
            positivos = ns_txt[validos_txt].str.contains(
                r'dentro|sim|atingido|cumprido|true', case=False, na=False
            )
            percentual_sla = positivos.mean() * 100
        else:
            percentual_sla = np.nan

    return {
        "Total de Atendimentos": total_atendimentos,
        "Por Canal": total_por_canal,
        "TMA": formatar_segundos_para_hora(tma_segundos) if pd.notna(tma_segundos) else "Sem dado",
        "TME": formatar_segundos_para_hora(tme_segundos) if pd.notna(tme_segundos) else "Sem dado",
        "SLA (%)": round(percentual_sla, 2) if pd.notna(percentual_sla) else None,
        "Taxa de Abandono (%)": round(taxa_abandono, 2)
    }

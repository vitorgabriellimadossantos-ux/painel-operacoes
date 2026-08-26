import pandas as pd
import numpy as np
import re

# ==========================================
# 1 E 2: CONVERSÃO E FORMATAÇÃO DE TEMPO
# ==========================================

def converter_para_segundos(valor_tempo):
    """
    Converte strings de tempo (HH:MM:SS) ou números para segundos inteiros.
    Isso é essencial para podermos calcular médias (TMA, TME).
    """
    if pd.isna(valor_tempo) or valor_tempo == '':
        return 0
    
    # Se já for um número (int ou float), assumimos que já está em segundos
    if isinstance(valor_tempo, (int, float)):
        return int(valor_tempo)
        
    valor_tempo = str(valor_tempo).strip()
    
    # Tenta extrair o padrão HH:MM:SS
    if ':' in valor_tempo:
        partes = valor_tempo.split(':')
        if len(partes) == 3: # HH:MM:SS
            h, m, s = partes
            return int(h) * 3600 + int(m) * 60 + int(float(s))
        elif len(partes) == 2: # MM:SS
            m, s = partes
            return int(m) * 60 + int(float(s))
            
    return 0

def formatar_segundos_para_hora(segundos totais):
    """
    Transforma segundos inteiros de volta para o formato de texto HH:MM:SS.
    Usado para exibir os dados de forma legível nos Dashboards e PDFs.
    """
    if pd.isna(totais) or totais < 0:
        return "00:00:00"
        
    totais = int(totais)
    horas = totais // 3600
    minutos = (totais % 3600) // 60
    segundos = totais % 60
    
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

# ==========================================
# 5: IDENTIFICAÇÃO DA EMPRESA
# ==========================================

def identificar_empresa_por_arquivo(nome_arquivo, lista_empresas_json):
    """
    Lê o nome do arquivo carregado pelo usuário (ex: 'relatorio_allge_junho.xlsx')
    e tenta encontrar o nome da empresa na nossa base de dados (empresas.json).
    """
    nome_arquivo_limpo = str(nome_arquivo).upper()
    
    for empresa in lista_empresas_json:
        nome_empresa = empresa['nome'].upper()
        if nome_empresa in nome_arquivo_limpo:
            return empresa['nome']
            
    return "EMPRESA NÃO IDENTIFICADA"

# ==========================================
# 3, 4 E 6: PROCESSAMENTO E PADRONIZAÇÃO
# ==========================================

# Colunas padrão exigidas para o DataFrame Consolidado final
COLUNAS_PADRAO = [
    'Empresa', 'Canal', 'Data', 'Hora', 'Horario_Critico', 
    'Fila', 'Agente', 'Tempo_Espera_Seg', 'Tempo_Conversa_Seg', 
    'Status', 'Nivel_Servico', 'Protocolo'
]

def padronizar_dataframe(df):
    """
    Garante que o DataFrame final tenha exatamente as colunas solicitadas,
    preenchendo com Vazio/Zero o que não existir para evitar erros no Streamlit.
    """
    for col in COLUNAS_PADRAO:
        if col not in df.columns:
            if 'Seg' in col:
                df[col] = 0
            else:
                df[col] = "Não Informado"
    
    # Retorna apenas as colunas padrão, na ordem certa
    return df[COLUNAS_PADRAO]

def processar_voz_vonix(df_bruto, nome_empresa):
    """
    Lê o relatório bruto do Vonix (Voz) e mapeia as colunas para o nosso padrão.
    (Nota: Os nomes em colunas_vonix são exemplos das exportações mais comuns do sistema).
    """
    # Exemplo de mapeamento (De: Para)
    mapa_colunas_vonix = {
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
        'Motivo do Status': 'Motivo' # Coluna extra que pode ser avaliada depois
    }
    
    # Renomeia o que encontrar
    df = df_bruto.rename(columns=mapa_colunas_vonix)
    
    # Adiciona as colunas fixas
    df['Empresa'] = nome_empresa
    df['Canal'] = 'Voz - Vonix'
    
    # Converte os tempos para segundos matemáticos
    if 'Tempo_Espera_Seg' in df.columns:
        df['Tempo_Espera_Seg'] = df['Tempo_Espera_Seg'].apply(converter_para_segundos)
    if 'Tempo_Conversa_Seg' in df.columns:
        df['Tempo_Conversa_Seg'] = df['Tempo_Conversa_Seg'].apply(converter_para_segundos)
        
    return padronizar_dataframe(df)

def processar_chat(df_bruto, nome_empresa, ferramenta_chat):
    """
    Lê relatórios de ChatMix, Fluctus, Chatwoot ou Vonix Chat.
    Usa lógicas condicionais baseadas na ferramenta.
    """
    df = df_bruto.copy()
    
    df['Empresa'] = nome_empresa
    df['Canal'] = f'Chat - {ferramenta_chat}'
    
    # Aqui criamos uma lógica de mapeamento genérica e flexível
    # O Pandas tenta adivinhar a coluna baseada em palavras-chave comuns desses sistemas
    colunas_df = [c.lower() for c in df.columns]
    
    # Tentativa de achar coluna de Agente/Atendente
    for col in df.columns:
        if any(palavra in col.lower() for palavra in ['agente', 'atendente', 'usuario', 'operador']):
            df['Agente'] = df[col]
            break
            
    # Tentativa de achar Tempo de Conversa
    for col in df.columns:
        if any(palavra in col.lower() for palavra in ['conversa', 'atendimento', 'duração', 'duracao']):
            df['Tempo_Conversa_Seg'] = df[col].apply(converter_para_segundos)
            break
            
    # Tentativa de achar Tempo de Espera
    for col in df.columns:
        if 'espera' in col.lower() or 'fila' in col.lower() and 'tempo' in col.lower():
            df['Tempo_Espera_Seg'] = df[col].apply(converter_para_segundos)
            break
            
    # Tentativa de achar Status
    for col in df.columns:
        if 'status' in col.lower() or 'situação' in col.lower():
            df['Status'] = df[col]
            break
            
    return padronizar_dataframe(df)

# ==========================================
# 7: CÁLCULO DE MÉTRICAS AGREGADAS
# ==========================================

def calcular_metricas(df_consolidado):
    """
    Pega o DataFrame padronizado e calcula os KPIs finais para o Dashboard.
    Retorna um dicionário com os resultados.
    """
    total_atendimentos = len(df_consolidado)
    
    if total_atendimentos == 0:
        return {"Erro": "Não há dados para calcular."}
        
    # Contagem por Canal (Voz vs Chat)
    total_por_canal = df_consolidado['Canal'].value_counts().to_dict()
    
    # Tempos Médios Matemáticos (TMA e TME em segundos)
    tma_segundos = df_consolidado['Tempo_Conversa_Seg'].mean()
    tme_segundos = df_consolidado['Tempo_Espera_Seg'].mean()
    
    # Taxa de Abandono (Status = Abandonada / Perdida)
    # Procuramos palavras-chave de abandono no Status
    abandonos = df_consolidado['Status'].astype(str).str.contains('abandono|abandonada|perdida|cancelada', case=False, na=False).sum()
    taxa_abandono = (abandonos / total_atendimentos) * 100
    
    # SLA (Nível de Serviço Atingido)
    # Assumimos SLA positivo se contiver 'dentro', 'sim', 'atingido', '100'
    sla_atingido = df_consolidado['Nivel_Servico'].astype(str).str.contains('dentro|sim|atingido', case=False, na=False).sum()
    percentual_sla = (sla_atingido / total_atendimentos) * 100
    
    # Retorna o pacote de métricas formatado
    return {
        "Total de Atendimentos": total_atendimentos,
        "Por Canal": total_por_canal,
        "TMA": formatar_segundos_para_hora(tma_segundos),
        "TME": formatar_segundos_para_hora(tme_segundos),
        "SLA (%)": round(percentual_sla, 2),
        "Taxa de Abandono (%)": round(taxa_abandono, 2)
    }

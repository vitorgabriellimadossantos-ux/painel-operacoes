import io
from datetime import datetime
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ==========================================
# FUNÇÃO AUXILIAR
# ==========================================
def _formatar_tempo(segundos):
    """
    Função interna para converter segundos matemáticos no formato HH:MM:SS.
    Garante que o PDF exiba os dados de forma legível.
    """
    if pd.isna(segundos) or segundos < 0:
        return "00:00:00"
    segundos = int(segundos)
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ==========================================
# CONFIGURAÇÃO DE RODAPÉ
# ==========================================
def _adicionar_rodape(canvas, doc):
    """
    Desenha o rodapé na parte inferior de cada página.
    Usa os métodos nativos do canvas do ReportLab para posicionamento absoluto.
    """
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    # Define a cor cinza para o rodapé
    canvas.setFillColor(colors.dimgrey)
    
    # Texto do rodapé com numeração de página
    texto_rodape = f"Página {canvas.getPageNumber()} | Relatório Operacional Consolidado - Gerado pelo Sistema de Gestão"
    
    # Posiciona no centro inferior da página A4
    largura_pagina = A4[0]
    canvas.drawCentredString(largura_pagina / 2.0, 1.5 * cm, texto_rodape)
    canvas.restoreState()

# ==========================================
# FUNÇÃO PRINCIPAL DE GERAÇÃO
# ==========================================
def gerar_pdf_consolidado(df, periodo_selecionado):
    """
    Recebe o DataFrame final e o período selecionado, realiza os cálculos,
    estrutura os parágrafos e tabelas, e retorna um arquivo PDF em bytes.
    """
    # 1. Preparando o buffer de memória (não salva no disco)
    buffer = io.BytesIO()
    
    # Configuração do Documento (A4 Retrato com Margens de 2cm)
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=2*cm, 
        leftMargin=2*cm, 
        topMargin=2*cm, 
        bottomMargin=2.5*cm
    )
    
    elementos = [] # Lista onde vamos "empilhar" o conteúdo do PDF
    
    # 2. Configurando Estilos de Texto
    estilos = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle(
        'TituloDoc',
        parent=estilos['Heading1'],
        fontSize=16,
        textColor=colors.HexColor("#1f497d"), # Azul profissional
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    estilo_subtitulo = ParagraphStyle(
        'SubTituloDoc',
        parent=estilos['Normal'],
        fontSize=10,
        textColor=colors.dimgrey,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    estilo_titulo_sessao = ParagraphStyle(
        'TituloSessao',
        parent=estilos['Heading2'],
        fontSize=12,
        textColor=colors.HexColor("#1f497d"),
        spaceBefore=15,
        spaceAfter=10
    )

    # 3. Cabeçalho do Documento
    data_emissao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    
    elementos.append(Paragraph("Relatório Consolidado de Atendimentos Operacionais", estilo_titulo))
    elementos.append(Paragraph(f"<b>Período:</b> {periodo_selecionado} | <b>Emissão:</b> {data_emissao}", estilo_subtitulo))
    
    # 4. Cálculos para o Quadro Executivo
    total_atendimentos = len(df)
    
    if total_atendimentos == 0:
        elementos.append(Paragraph("Nenhum dado encontrado para o período selecionado.", estilos['Normal']))
        doc.build(elementos, onFirstPage=_adicionar_rodape, onLaterPages=_adicionar_rodape)
        buffer.seek(0)
        return buffer

    # Contagem de canais
    vol_voz = len(df[df['Canal'].str.contains('Voz', case=False, na=False)])
    vol_chat = len(df[df['Canal'].str.contains('Chat', case=False, na=False)])
    
    # Tempos médios
    tma_geral = _formatar_tempo(df['Tempo_Conversa_Seg'].mean())
    tme_geral = _formatar_tempo(df['Tempo_Espera_Seg'].mean())
    
    # SLA (Exemplo de lógica: considerando quem não é abandono ou quem tem Nível Atingido)
    sla_atingido = df['Nivel_Servico'].astype(str).str.contains('dentro|sim|atingido', case=False, na=False).sum()
    pct_sla = (sla_atingido / total_atendimentos) * 100 if total_atendimentos > 0 else 0

    # 5. Quadro Executivo (Tabela)
    dados_executivo = [
        ["Total Atendimentos", "Volume Voz", "Volume Chat", "TMA Geral", "TME Geral", "Nível Serviço (SLA)"],
        [str(total_atendimentos), str(vol_voz), str(vol_chat), tma_geral, tme_geral, f"{pct_sla:.2f}%"]
    ]
    
    tabela_executiva = Table(dados_executivo, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2.8*cm, 2.8*cm, 3.2*cm])
    
    # O TableStyle define fundo, fontes, alinhamento central e linhas de grade
    tabela_executiva.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f497d")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#f2f2f2")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elementos.append(tabela_executiva)
    elementos.append(Spacer(1, 0.5*cm))

    # 6. Tabela de Detalhamento por Empresa/Canal
    elementos.append(Paragraph("Detalhamento por Operação", estilo_titulo_sessao))
    
    # Agrupando os dados (Group By)
    grupo_empresa = df.groupby(['Empresa', 'Canal']).agg(
        Total=('Data', 'count'),
        TMA_Seg=('Tempo_Conversa_Seg', 'mean'),
        TME_Seg=('Tempo_Espera_Seg', 'mean')
    ).reset_index()
    
    dados_detalhe = [["Empresa", "Canal", "Volume Total", "TMA", "TME"]]
    
    for _, row in grupo_empresa.iterrows():
        dados_detalhe.append([
            str(row['Empresa']),
            str(row['Canal']),
            str(row['Total']),
            _formatar_tempo(row['TMA_Seg']),
            _formatar_tempo(row['TME_Seg'])
        ])
        
    tabela_detalhe = Table(dados_detalhe, colWidths=[5*cm, 4*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    tabela_detalhe.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2a6395")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'), # Números centralizados
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]), # Linhas zebradas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    
    elementos.append(tabela_detalhe)
    elementos.append(Spacer(1, 0.5*cm))

    # 7. Ranking dos 10 Operadores (Agentes)
    elementos.append(Paragraph("Top 10 Operadores (Maior Volume)", estilo_titulo_sessao))
    
    # Pega os 10 agentes com maior frequência no dataframe
    top_agentes = df['Agente'].value_counts().head(10).reset_index()
    top_agentes.columns = ['Agente', 'Volume']
    
    # Filtra valores vazios ou nulos caso existam
    top_agentes = top_agentes[top_agentes['Agente'].astype(str).str.strip() != '']
    
    dados_ranking = [["Posição", "Nome do Agente", "Total de Atendimentos"]]
    
    for idx, row in top_agentes.iterrows():
        dados_ranking.append([
            f"{idx + 1}º",
            str(row['Agente']).title(),
            str(row['Volume'])
        ])
        
    tabela_ranking = Table(dados_ranking, colWidths=[2.5*cm, 8.5*cm, 4*cm])
    tabela_ranking.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4f81bd")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'), # Nomes alinhados à esquerda
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    
    elementos.append(tabela_ranking)
    
    # 8. Renderização Final
    # Constrói o PDF empilhando tudo e aplicando o rodapé em todas as páginas
    doc.build(elementos, onFirstPage=_adicionar_rodape, onLaterPages=_adicionar_rodape)
    
    # Retorna o ponteiro do buffer para o início para que o Streamlit consiga ler e baixar
    buffer.seek(0)
    
    return buffer

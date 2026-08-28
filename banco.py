import hashlib
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text


# ==========================================
# CONEXÃO COM O BANCO
# ==========================================
@st.cache_resource
def obter_conexao():
    """
    Cria e reaproveita a conexão com o
    PostgreSQL/Supabase configurado nos Secrets.
    """
    return st.connection(
        "supabase",
        type="sql"
    )


# ==========================================
# EMPRESAS
# ==========================================
def listar_empresas():
    """
    Retorna todas as empresas ativas.
    """
    conn = obter_conexao()

    return conn.query(
        """
        SELECT
            id,
            nome,
            tipo,
            sistema_voz,
            sistema_chat,
            ativo
        FROM empresas
        WHERE ativo IS TRUE
        ORDER BY nome;
        """,
        ttl=0
    )


def buscar_empresa_por_nome(nome_empresa):
    """
    Busca uma empresa pelo nome.
    """
    if not nome_empresa:
        return None

    conn = obter_conexao()

    consulta = text(
        """
        SELECT
            id,
            nome,
            tipo,
            sistema_voz,
            sistema_chat,
            ativo
        FROM empresas
        WHERE UPPER(nome) = UPPER(:nome)
        LIMIT 1;
        """
    )

    with conn.session as session:
        resultado = session.execute(
            consulta,
            {
                "nome": nome_empresa.strip()
            }
        ).mappings().first()

        return dict(resultado) if resultado else None


def obter_id_empresa(nome_empresa):
    """
    Retorna apenas o ID da empresa.
    """
    empresa = buscar_empresa_por_nome(
        nome_empresa
    )

    if empresa:
        return empresa["id"]

    return None


def cadastrar_empresa(
    nome,
    tipo=None,
    sistema_voz=None,
    sistema_chat=None
):
    """
    Cadastra uma nova empresa.
    Se já existir, não duplica.
    """
    conn = obter_conexao()

    consulta = text(
        """
        INSERT INTO empresas (
            nome,
            tipo,
            sistema_voz,
            sistema_chat,
            ativo
        )
        VALUES (
            :nome,
            :tipo,
            :sistema_voz,
            :sistema_chat,
            TRUE
        )
        ON CONFLICT (nome)
        DO NOTHING;
        """
    )

    with conn.session as session:
        session.execute(
            consulta,
            {
                "nome": nome.upper().strip(),
                "tipo": tipo,
                "sistema_voz": sistema_voz,
                "sistema_chat": sistema_chat
            }
        )

        session.commit()


# ==========================================
# HASH DO ARQUIVO
# ==========================================
def gerar_hash_arquivo(uploaded_file):
    """
    Gera um identificador único para o arquivo.

    Isso será usado para impedir que a mesma
    planilha seja importada duas vezes.
    """
    uploaded_file.seek(0)

    conteudo = uploaded_file.read()

    uploaded_file.seek(0)

    return hashlib.sha256(
        conteudo
    ).hexdigest()


def importacao_ja_existe(hash_arquivo):
    """
    Verifica se um arquivo já foi importado.
    """
    conn = obter_conexao()

    consulta = text(
        """
        SELECT id
        FROM importacoes
        WHERE hash_arquivo = :hash_arquivo
        LIMIT 1;
        """
    )

    with conn.session as session:
        resultado = session.execute(
            consulta,
            {
                "hash_arquivo": hash_arquivo
            }
        ).first()

        return resultado is not None


# ==========================================
# IMPORTAÇÕES
# ==========================================
def criar_importacao(
    empresa_id,
    nome_arquivo,
    tipo_arquivo,
    canal,
    data_inicial,
    data_final,
    hash_arquivo,
    quantidade_registros,
    status="processado"
):
    """
    Registra uma importação no banco.

    Retorna o ID da importação criada.
    """
    conn = obter_conexao()

    consulta = text(
        """
        INSERT INTO importacoes (
            empresa_id,
            nome_arquivo,
            tipo_arquivo,
            canal,
            data_inicial,
            data_final,
            hash_arquivo,
            quantidade_registros,
            status
        )
        VALUES (
            :empresa_id,
            :nome_arquivo,
            :tipo_arquivo,
            :canal,
            :data_inicial,
            :data_final,
            :hash_arquivo,
            :quantidade_registros,
            :status
        )
        RETURNING id;
        """
    )

    with conn.session as session:
        resultado = session.execute(
            consulta,
            {
                "empresa_id": empresa_id,
                "nome_arquivo": nome_arquivo,
                "tipo_arquivo": tipo_arquivo,
                "canal": canal,
                "data_inicial": data_inicial,
                "data_final": data_final,
                "hash_arquivo": hash_arquivo,
                "quantidade_registros":
                    quantidade_registros,
                "status": status
            }
        )

        importacao_id = resultado.scalar()

        session.commit()

        return importacao_id


def listar_importacoes(
    empresa_id=None,
    limite=100
):
    """
    Lista as importações mais recentes.
    """
    conn = obter_conexao()

    if empresa_id:

        consulta = text(
            """
            SELECT
                i.id,
                e.nome AS empresa,
                i.nome_arquivo,
                i.tipo_arquivo,
                i.canal,
                i.data_inicial,
                i.data_final,
                i.quantidade_registros,
                i.status,
                i.criado_em
            FROM importacoes i
            JOIN empresas e
                ON e.id = i.empresa_id
            WHERE i.empresa_id = :empresa_id
            ORDER BY i.criado_em DESC
            LIMIT :limite;
            """
        )

        with conn.session as session:
            resultado = session.execute(
                consulta,
                {
                    "empresa_id": empresa_id,
                    "limite": limite
                }
            ).mappings().all()

    else:

        consulta = text(
            """
            SELECT
                i.id,
                e.nome AS empresa,
                i.nome_arquivo,
                i.tipo_arquivo,
                i.canal,
                i.data_inicial,
                i.data_final,
                i.quantidade_registros,
                i.status,
                i.criado_em
            FROM importacoes i
            JOIN empresas e
                ON e.id = i.empresa_id
            ORDER BY i.criado_em DESC
            LIMIT :limite;
            """
        )

        with conn.session as session:
            resultado = session.execute(
                consulta,
                {
                    "limite": limite
                }
            ).mappings().all()

    return pd.DataFrame(resultado)


# ==========================================
# CONVERSORES AUXILIARES
# ==========================================
def _valor_limpo(valor):
    """
    Converte NaN/NaT para None antes
    de enviar ao PostgreSQL.
    """
    if pd.isna(valor):
        return None

    return valor


def _data_postgres(valor):
    """
    Converte datas do pandas para date.
    """
    if pd.isna(valor):
        return None

    convertido = pd.to_datetime(
        valor,
        errors="coerce"
    )

    if pd.isna(convertido):
        return None

    return convertido.date()


def _hora_postgres(valor):
    """
    Converte hora para formato aceito
    pelo PostgreSQL.
    """
    if valor is None:
        return None

    if pd.isna(valor):
        return None

    if hasattr(valor, "hour"):
        return valor

    try:
        convertido = pd.to_datetime(
            str(valor),
            errors="coerce"
        )

        if pd.isna(convertido):
            return None

        return convertido.time()

    except Exception:
        return None


# ==========================================
# ATENDIMENTOS
# ==========================================
def salvar_atendimentos(
    df,
    empresa_id,
    importacao_id
):
    """
    Salva o DataFrame padronizado
    na tabela atendimentos.
    """
    if df is None or df.empty:
        return 0

    conn = obter_conexao()

    consulta = text(
        """
        INSERT INTO atendimentos (
            empresa_id,
            importacao_id,
            canal,
            data,
            hora,
            horario_critico,
            fila,
            agente,
            tempo_espera_seg,
            tempo_conversa_seg,
            status,
            nivel_servico,
            protocolo
        )
        VALUES (
            :empresa_id,
            :importacao_id,
            :canal,
            :data,
            :hora,
            :horario_critico,
            :fila,
            :agente,
            :tempo_espera_seg,
            :tempo_conversa_seg,
            :status,
            :nivel_servico,
            :protocolo
        );
        """
    )

    registros = []

    for _, row in df.iterrows():

        registros.append({
            "empresa_id":
                empresa_id,

            "importacao_id":
                importacao_id,

            "canal":
                _valor_limpo(
                    row.get("Canal")
                ),

            "data":
                _data_postgres(
                    row.get("Data")
                ),

            "hora":
                _hora_postgres(
                    row.get("Hora")
                ),

            "horario_critico":
                _valor_limpo(
                    row.get(
                        "Horario_Critico"
                    )
                ),

            "fila":
                _valor_limpo(
                    row.get("Fila")
                ),

            "agente":
                _valor_limpo(
                    row.get("Agente")
                ),

            "tempo_espera_seg":
                _valor_limpo(
                    row.get(
                        "Tempo_Espera_Seg"
                    )
                ),

            "tempo_conversa_seg":
                _valor_limpo(
                    row.get(
                        "Tempo_Conversa_Seg"
                    )
                ),

            "status":
                _valor_limpo(
                    row.get("Status")
                ),

            "nivel_servico":
                _valor_limpo(
                    row.get(
                        "Nivel_Servico"
                    )
                ),

            "protocolo":
                _valor_limpo(
                    row.get("Protocolo")
                )
        })

    with conn.session as session:

        session.execute(
            consulta,
            registros
        )

        session.commit()

    return len(registros)


# ==========================================
# INDICADORES DIÁRIOS
# ==========================================
def salvar_indicadores_diarios(
    df,
    empresa_id,
    importacao_id,
    canal="Chat"
):
    """
    Salva arquivos do tipo Indicadores
    de R2/NEX quando necessário.
    """
    if df is None or df.empty:
        return 0

    conn = obter_conexao()

    consulta = text(
        """
        INSERT INTO indicadores_diarios (
            empresa_id,
            importacao_id,
            data,
            canal,
            atendimentos,
            tma_seg,
            tme_seg,
            tmr_seg,
            sla_percentual
        )
        VALUES (
            :empresa_id,
            :importacao_id,
            :data,
            :canal,
            :atendimentos,
            :tma_seg,
            :tme_seg,
            :tmr_seg,
            :sla_percentual
        );
        """
    )

    registros = []

    for _, row in df.iterrows():

        registros.append({
            "empresa_id":
                empresa_id,

            "importacao_id":
                importacao_id,

            "data":
                _data_postgres(
                    row.get("Data")
                ),

            "canal":
                canal,

            "atendimentos":
                int(
                    row.get(
                        "Atendimentos",
                        0
                    ) or 0
                ),

            "tma_seg":
                _valor_limpo(
                    row.get("TMA_Seg")
                ),

            "tme_seg":
                _valor_limpo(
                    row.get("TME_Seg")
                ),

            "tmr_seg":
                _valor_limpo(
                    row.get("TMR_Seg")
                ),

            "sla_percentual":
                _valor_limpo(
                    row.get(
                        "SLA_Percentual"
                    )
                )
        })

    with conn.session as session:

        session.execute(
            consulta,
            registros
        )

        session.commit()

    return len(registros)


# ==========================================
# PRODUTIVIDADE DE AGENTES
# ==========================================
def salvar_produtividade_agentes(
    df,
    empresa_id,
    importacao_id,
    data_inicial=None,
    data_final=None
):
    """
    Salva relatórios agregados
    de produtividade, como LIG TOP.
    """
    if df is None or df.empty:
        return 0

    conn = obter_conexao()

    consulta = text(
        """
        INSERT INTO produtividade_agentes (
            empresa_id,
            importacao_id,
            data_inicial,
            data_final,
            agente,
            conversas_atribuidas,
            resolucoes,
            tempo_primeira_resposta_seg,
            tempo_resolucao_seg,
            tempo_espera_cliente_seg
        )
        VALUES (
            :empresa_id,
            :importacao_id,
            :data_inicial,
            :data_final,
            :agente,
            :conversas_atribuidas,
            :resolucoes,
            :tempo_primeira_resposta_seg,
            :tempo_resolucao_seg,
            :tempo_espera_cliente_seg
        );
        """
    )

    registros = []

    for _, row in df.iterrows():

        registros.append({
            "empresa_id":
                empresa_id,

            "importacao_id":
                importacao_id,

            "data_inicial":
                data_inicial,

            "data_final":
                data_final,

            "agente":
                _valor_limpo(
                    row.get("Agente")
                ),

            "conversas_atribuidas":
                int(
                    row.get(
                        "Conversas_Atribuidas",
                        0
                    ) or 0
                ),

            "resolucoes":
                int(
                    row.get(
                        "Resolvidos",
                        0
                    ) or 0
                ),

            "tempo_primeira_resposta_seg":
                _valor_limpo(
                    row.get(
                        "Primeira_Resposta_Seg"
                    )
                ),

            "tempo_resolucao_seg":
                _valor_limpo(
                    row.get(
                        "Tempo_Resolucao_Seg"
                    )
                ),

            "tempo_espera_cliente_seg":
                _valor_limpo(
                    row.get(
                        "Espera_Cliente_Seg"
                    )
                )
        })

    with conn.session as session:

        session.execute(
            consulta,
            registros
        )

        session.commit()

    return len(registros)


# ==========================================
# CONSULTA DE ATENDIMENTOS SALVOS
# ==========================================
def consultar_atendimentos(
    empresa_id=None,
    data_inicial=None,
    data_final=None
):
    """
    Busca dados já salvos no banco.
    Será usada futuramente para abrir
    histórico sem fazer novo upload.
    """
    conn = obter_conexao()

    filtros = []
    parametros = {}

    if empresa_id:
        filtros.append(
            "a.empresa_id = :empresa_id"
        )
        parametros[
            "empresa_id"
        ] = empresa_id

    if data_inicial:
        filtros.append(
            "a.data >= :data_inicial"
        )
        parametros[
            "data_inicial"
        ] = data_inicial

    if data_final:
        filtros.append(
            "a.data <= :data_final"
        )
        parametros[
            "data_final"
        ] = data_final

    where_sql = ""

    if filtros:
        where_sql = (
            "WHERE "
            + " AND ".join(filtros)
        )

    consulta = f"""
        SELECT
            a.id,
            e.nome AS "Empresa",
            a.canal AS "Canal",
            a.data AS "Data",
            a.hora AS "Hora",
            a.horario_critico
                AS "Horario_Critico",
            a.fila AS "Fila",
            a.agente AS "Agente",
            a.tempo_espera_seg
                AS "Tempo_Espera_Seg",
            a.tempo_conversa_seg
                AS "Tempo_Conversa_Seg",
            a.status AS "Status",
            a.nivel_servico
                AS "Nivel_Servico",
            a.protocolo AS "Protocolo"
        FROM atendimentos a
        JOIN empresas e
            ON e.id = a.empresa_id
        {where_sql}
        ORDER BY
            a.data,
            a.hora;
    """

    with conn.session as session:

        resultado = session.execute(
            text(consulta),
            parametros
        ).mappings().all()

    return pd.DataFrame(resultado)


# ==========================================
# TESTE DE CONEXÃO
# ==========================================
def testar_conexao():
    """
    Teste simples para confirmar
    se o banco responde.
    """
    try:
        conn = obter_conexao()

        resultado = conn.query(
            """
            SELECT COUNT(*) AS total
            FROM empresas;
            """,
            ttl=0
        )

        if resultado.empty:
            return False, 0

        total = int(
            resultado.iloc[0]["total"]
        )

        return True, total

    except Exception as e:
        return False, str(e)

from __future__ import annotations

from typing import Any

import pandas as pd
from postgrest.exceptions import APIError

from supabase_client import obter_cliente_supabase


TABELA = "processos"

COLUNAS = [
    "id",
    "numero",
    "area",
    "classe",
    "assunto",
    "autor",
    "reu",
    "orgao_julgador",
    "relator",
    "resumo",
    "palavras_chave",
    "prioridade",
    "situacao",
    "responsavel",
    "nivel_acesso",
    "resumo_executivo",
    "providencia_pendente",
    "prazo_relevante",
    "data_cadastro",
    "data_atualizacao",
]

CAMPOS_PESQUISA = [
    "numero",
    "area",
    "classe",
    "assunto",
    "autor",
    "reu",
    "orgao_julgador",
    "relator",
    "resumo",
    "palavras_chave",
    "prioridade",
    "situacao",
    "responsavel",
    "resumo_executivo",
    "providencia_pendente",
    "prazo_relevante",
]


class ProcessoDuplicadoError(Exception):
    """Indica que ja existe processo com o mesmo numero."""


def _normalizar_dados(dados: dict[str, Any]) -> dict[str, Any]:
    """Mantem apenas campos aceitos pela tabela e converte vazios para None."""
    campos_gravaveis = set(COLUNAS) - {
        "id",
        "data_cadastro",
        "data_atualizacao",
    }

    resultado: dict[str, Any] = {}
    for campo in campos_gravaveis:
        valor = dados.get(campo)
        if isinstance(valor, str):
            valor = valor.strip()
        resultado[campo] = valor if valor != "" else None

    return resultado


def _dataframe(registros: list[dict[str, Any]]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame(columns=COLUNAS)

    df = pd.DataFrame(registros)
    for coluna in COLUNAS:
        if coluna not in df.columns:
            df[coluna] = None

    return df[COLUNAS]


def _eh_duplicidade(erro: APIError) -> bool:
    codigo = str(getattr(erro, "code", ""))
    mensagem = str(erro).lower()
    return codigo == "23505" or "duplicate key" in mensagem or "unique" in mensagem


def criar_banco() -> None:
    """Mantida por compatibilidade; a tabela e criada no Supabase."""
    obter_cliente_supabase()


def cadastrar_processo(dados: dict[str, Any]) -> None:
    cliente = obter_cliente_supabase()
    try:
        cliente.table(TABELA).insert(_normalizar_dados(dados)).execute()
    except APIError as erro:
        if _eh_duplicidade(erro):
            raise ProcessoDuplicadoError from erro
        raise


def atualizar_processo(processo_id: int, dados: dict[str, Any]) -> None:
    cliente = obter_cliente_supabase()
    try:
        cliente.table(TABELA).update(_normalizar_dados(dados)).eq(
            "id", processo_id
        ).execute()
    except APIError as erro:
        if _eh_duplicidade(erro):
            raise ProcessoDuplicadoError from erro
        raise


def obter_processo(processo_id: int) -> dict[str, Any] | None:
    cliente = obter_cliente_supabase()
    resposta = (
        cliente.table(TABELA)
        .select("*")
        .eq("id", processo_id)
        .limit(1)
        .execute()
    )

    return resposta.data[0] if resposta.data else None


def listar_processos() -> pd.DataFrame:
    cliente = obter_cliente_supabase()
    resposta = (
        cliente.table(TABELA)
        .select("*")
        .order("id", desc=True)
        .execute()
    )
    return _dataframe(resposta.data or [])


def pesquisar_processos(termo: str) -> pd.DataFrame:
    termo_normalizado = termo.strip().casefold()
    processos = listar_processos()

    if processos.empty or not termo_normalizado:
        return processos

    mascara = pd.Series(False, index=processos.index)
    for campo in CAMPOS_PESQUISA:
        mascara = mascara | (
            processos[campo]
            .fillna("")
            .astype(str)
            .str.casefold()
            .str.contains(termo_normalizado, regex=False)
        )

    return processos[mascara].reset_index(drop=True)

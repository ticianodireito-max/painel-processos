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


TABELA_DOCUMENTOS = "documentos_processo"
BUCKET_DOCUMENTOS = "processos"

COLUNAS_DOCUMENTOS = [
    "id",
    "processo_id",
    "categoria",
    "titulo",
    "descricao",
    "data_documento",
    "nome_arquivo",
    "caminho_storage",
    "tamanho_bytes",
    "data_upload",
]

CATEGORIAS_DOCUMENTOS = {"decisao", "peca", "outro"}


class DocumentoInvalidoError(ValueError):
    """Indica que o documento enviado nao atende aos requisitos."""


def _nome_seguro(nome: str) -> str:
    """Gera um nome simples e seguro para uso no Supabase Storage."""
    import re
    import unicodedata

    nome_normalizado = unicodedata.normalize("NFKD", nome)
    nome_ascii = nome_normalizado.encode("ascii", "ignore").decode("ascii")
    nome_ascii = re.sub(r"[^A-Za-z0-9._-]+", "-", nome_ascii)
    nome_ascii = re.sub(r"-+", "-", nome_ascii).strip("-.")
    return nome_ascii or "documento.pdf"


def cadastrar_documento(
    processo_id: int,
    categoria: str,
    titulo: str,
    descricao: str,
    data_documento: str | None,
    nome_arquivo: str,
    conteudo: bytes,
) -> dict[str, Any]:
    """Envia um PDF ao Storage e registra seus metadados na tabela."""
    from uuid import uuid4

    categoria = categoria.strip().lower()
    titulo = titulo.strip()
    nome_arquivo = nome_arquivo.strip()

    if categoria not in CATEGORIAS_DOCUMENTOS:
        raise DocumentoInvalidoError("Categoria de documento invalida.")
    if not titulo:
        raise DocumentoInvalidoError("Informe o titulo do documento.")
    if not nome_arquivo.lower().endswith(".pdf"):
        raise DocumentoInvalidoError("Somente arquivos PDF sao permitidos.")
    if not conteudo:
        raise DocumentoInvalidoError("O arquivo PDF esta vazio.")
    if not conteudo.startswith(b"%PDF"):
        raise DocumentoInvalidoError("O arquivo enviado nao parece ser um PDF valido.")

    cliente = obter_cliente_supabase()
    nome_storage = f"{uuid4().hex}-{_nome_seguro(nome_arquivo)}"
    caminho = f"{processo_id}/{categoria}/{nome_storage}"

    cliente.storage.from_(BUCKET_DOCUMENTOS).upload(
        caminho,
        conteudo,
        file_options={
            "content-type": "application/pdf",
            "upsert": "false",
        },
    )

    registro = {
        "processo_id": processo_id,
        "categoria": categoria,
        "titulo": titulo,
        "descricao": descricao.strip() or None,
        "data_documento": data_documento or None,
        "nome_arquivo": nome_arquivo,
        "caminho_storage": caminho,
        "tamanho_bytes": len(conteudo),
    }

    try:
        resposta = cliente.table(TABELA_DOCUMENTOS).insert(registro).execute()
    except Exception:
        cliente.storage.from_(BUCKET_DOCUMENTOS).remove([caminho])
        raise

    return resposta.data[0] if resposta.data else registro


def listar_documentos(processo_id: int, categoria: str | None = None) -> pd.DataFrame:
    cliente = obter_cliente_supabase()
    consulta = (
        cliente.table(TABELA_DOCUMENTOS)
        .select("*")
        .eq("processo_id", processo_id)
    )

    if categoria:
        consulta = consulta.eq("categoria", categoria)

    resposta = consulta.order("data_upload", desc=True).execute()
    registros = resposta.data or []

    if not registros:
        return pd.DataFrame(columns=COLUNAS_DOCUMENTOS)

    df = pd.DataFrame(registros)
    for coluna in COLUNAS_DOCUMENTOS:
        if coluna not in df.columns:
            df[coluna] = None
    return df[COLUNAS_DOCUMENTOS]


def criar_url_documento(caminho_storage: str, validade_segundos: int = 3600) -> str:
    """Cria uma URL temporaria para visualizar ou baixar um PDF privado."""
    cliente = obter_cliente_supabase()
    resposta = cliente.storage.from_(BUCKET_DOCUMENTOS).create_signed_url(
        caminho_storage,
        validade_segundos,
    )

    if isinstance(resposta, dict):
        return str(
            resposta.get("signedURL")
            or resposta.get("signedUrl")
            or resposta.get("signed_url")
            or ""
        )

    return str(getattr(resposta, "signed_url", "") or "")


def excluir_documento(documento_id: int, caminho_storage: str) -> None:
    """Exclui o arquivo do Storage e seu registro da tabela."""
    cliente = obter_cliente_supabase()
    cliente.storage.from_(BUCKET_DOCUMENTOS).remove([caminho_storage])
    cliente.table(TABELA_DOCUMENTOS).delete().eq("id", documento_id).execute()

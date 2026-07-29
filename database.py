from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
BANCO_PATH = BASE_DIR / "processos.db"


def conectar() -> sqlite3.Connection:
    conexao = sqlite3.connect(BANCO_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_banco() -> None:
    with conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS processos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL UNIQUE,
                area TEXT,
                classe TEXT,
                assunto TEXT,
                autor TEXT,
                reu TEXT,
                orgao_julgador TEXT,
                relator TEXT,
                resumo TEXT,
                palavras_chave TEXT,
                prioridade TEXT DEFAULT 'Normal',
                situacao TEXT DEFAULT 'Em andamento',
                responsavel TEXT,
                nivel_acesso TEXT DEFAULT 'Interno',
                resumo_executivo TEXT,
                providencia_pendente TEXT,
                prazo_relevante TEXT,
                data_cadastro TEXT NOT NULL,
                data_atualizacao TEXT
            )
            """
        )

        colunas_existentes = {
            linha["name"]
            for linha in conexao.execute(
                "PRAGMA table_info(processos)"
            ).fetchall()
        }

        novas_colunas = {
            "prioridade": "TEXT DEFAULT 'Normal'",
            "situacao": "TEXT DEFAULT 'Em andamento'",
            "responsavel": "TEXT",
            "nivel_acesso": "TEXT DEFAULT 'Interno'",
            "resumo_executivo": "TEXT",
            "providencia_pendente": "TEXT",
            "prazo_relevante": "TEXT",
            "data_atualizacao": "TEXT",
        }

        for nome, definicao in novas_colunas.items():
            if nome not in colunas_existentes:
                conexao.execute(
                    f"ALTER TABLE processos "
                    f"ADD COLUMN {nome} {definicao}"
                )


def cadastrar_processo(dados: dict) -> None:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO processos (
                numero,
                area,
                classe,
                assunto,
                autor,
                reu,
                orgao_julgador,
                relator,
                resumo,
                palavras_chave,
                prioridade,
                situacao,
                responsavel,
                nivel_acesso,
                resumo_executivo,
                providencia_pendente,
                prazo_relevante,
                data_cadastro,
                data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados["numero"],
                dados["area"],
                dados["classe"],
                dados["assunto"],
                dados["autor"],
                dados["reu"],
                dados["orgao_julgador"],
                dados["relator"],
                dados["resumo"],
                dados["palavras_chave"],
                dados["prioridade"],
                dados["situacao"],
                dados["responsavel"],
                dados["nivel_acesso"],
                dados["resumo_executivo"],
                dados["providencia_pendente"],
                dados["prazo_relevante"],
                agora,
                agora,
            ),
        )


def atualizar_processo(processo_id: int, dados: dict) -> None:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE processos
            SET
                numero = ?,
                area = ?,
                classe = ?,
                assunto = ?,
                autor = ?,
                reu = ?,
                orgao_julgador = ?,
                relator = ?,
                resumo = ?,
                palavras_chave = ?,
                prioridade = ?,
                situacao = ?,
                responsavel = ?,
                nivel_acesso = ?,
                resumo_executivo = ?,
                providencia_pendente = ?,
                prazo_relevante = ?,
                data_atualizacao = ?
            WHERE id = ?
            """,
            (
                dados["numero"],
                dados["area"],
                dados["classe"],
                dados["assunto"],
                dados["autor"],
                dados["reu"],
                dados["orgao_julgador"],
                dados["relator"],
                dados["resumo"],
                dados["palavras_chave"],
                dados["prioridade"],
                dados["situacao"],
                dados["responsavel"],
                dados["nivel_acesso"],
                dados["resumo_executivo"],
                dados["providencia_pendente"],
                dados["prazo_relevante"],
                agora,
                processo_id,
            ),
        )


def obter_processo(processo_id: int) -> dict | None:
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT *
            FROM processos
            WHERE id = ?
            """,
            (processo_id,),
        ).fetchone()

    if registro is None:
        return None

    return dict(registro)


def listar_processos() -> pd.DataFrame:
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT *
            FROM processos
            ORDER BY id DESC
            """
        ).fetchall()

    return pd.DataFrame([dict(registro) for registro in registros])


def pesquisar_processos(termo: str) -> pd.DataFrame:
    termo_busca = f"%{termo.strip()}%"

    campos = [
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

    condicoes = " OR ".join(
        f"COALESCE({campo}, '') LIKE ?" for campo in campos
    )

    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT *
            FROM processos
            WHERE {condicoes}
            ORDER BY id DESC
            """,
            [termo_busca] * len(campos),
        ).fetchall()

    return pd.DataFrame([dict(registro) for registro in registros])
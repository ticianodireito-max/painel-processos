from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st


ARQUIVOS_CSS = (
    "base.css",
    "sidebar.css",
    "dashboard.css",
    "components.css",
    "responsive.css",
)


def carregar_estilos(diretorio: str = "assets") -> None:
    """Carrega os módulos CSS na ordem definida, sem interromper o app se algum faltar."""
    pasta = Path(diretorio)
    partes: list[str] = []

    for nome in ARQUIVOS_CSS:
        arquivo = pasta / nome
        if arquivo.exists():
            partes.append(arquivo.read_text(encoding="utf-8"))

    # Compatibilidade com instalações antigas que ainda tenham apenas styles.css.
    if not partes:
        legado = pasta / "styles.css"
        if legado.exists():
            partes.append(legado.read_text(encoding="utf-8"))

    if partes:
        st.markdown(f"<style>{'\n'.join(partes)}</style>", unsafe_allow_html=True)


def cabecalho_pagina(titulo: str, descricao: str | None = None) -> None:
    descricao_html = (
        f'<p class="page-description">{escape(descricao)}</p>'
        if descricao
        else ""
    )
    st.markdown(
        f"""
        <div class="page-heading">
            <h1>{escape(titulo)}</h1>
            {descricao_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def titulo_secao(titulo: str, descricao: str | None = None) -> None:
    descricao_html = (
        f'<p class="section-description">{escape(descricao)}</p>'
        if descricao
        else ""
    )
    st.markdown(
        f"""
        <div class="section-heading">
            <h2>{escape(titulo)}</h2>
            {descricao_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def cartao_indicador(rotulo: str, valor: int | str, icone: str, tom: str = "neutro") -> None:
    st.markdown(
        f"""
        <div class="metric-card metric-{escape(tom)}">
            <div class="metric-icon">{escape(icone)}</div>
            <div class="metric-content">
                <div class="metric-value">{escape(str(valor))}</div>
                <div class="metric-label">{escape(rotulo)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def marca_sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-mark">⚖</div>
            <div>
                <div class="sidebar-brand-title">Sistema Estratégico</div>
                <div class="sidebar-brand-subtitle">Gestão de Processos</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

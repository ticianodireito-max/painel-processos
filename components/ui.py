from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st


def carregar_estilos(caminho: str = "assets/styles.css") -> None:
    """Carrega o CSS externo sem interromper o aplicativo se o arquivo faltar."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        return

    css = arquivo.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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



def cabecalho_formulario(titulo: str, descricao: str | None = None) -> None:
    descricao_html = (
        f'<p class="form-section-description">{escape(descricao)}</p>'
        if descricao
        else ""
    )
    st.markdown(
        f"""
        <div class="form-section-heading">
            <div class="form-section-title">{escape(titulo)}</div>
            {descricao_html}
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

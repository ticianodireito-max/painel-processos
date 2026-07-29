from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def obter_cliente_supabase() -> Client:
    """Cria e reutiliza a conexao com o Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        chave = st.secrets["SUPABASE_KEY"]
    except KeyError as erro:
        raise RuntimeError(
            "Credenciais do Supabase nao configuradas. "
            "Cadastre SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit."
        ) from erro

    if not str(url).strip() or not str(chave).strip():
        raise RuntimeError("As credenciais do Supabase estao vazias.")

    return create_client(str(url), str(chave))

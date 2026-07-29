from __future__ import annotations

import pandas as pd
import streamlit as st

from components.ui import (
    cabecalho_pagina,
    carregar_estilos,
    cartao_indicador,
    marca_sidebar,
    titulo_secao,
)

from database import (
    atualizar_processo,
    cadastrar_processo,
    criar_banco,
    listar_processos,
    obter_processo,
    pesquisar_processos,
    ProcessoDuplicadoError,
)


st.set_page_config(
    page_title="Sistema Estratégico de Processos",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

carregar_estilos()

criar_banco()

AREAS = [
    "",
    "Ambiental",
    "Administrativo",
    "Constitucional",
    "Tributário",
    "Saúde",
    "Servidor Público",
    "Patrimônio Público",
    "Outra",
]

PRIORIDADES = [
    "Baixa",
    "Normal",
    "Alta",
    "Urgente",
]

SITUACOES = [
    "Em andamento",
    "Aguardando decisão",
    "Aguardando informações",
    "Prazo em curso",
    "Suspenso",
    "Finalizado",
    "Arquivado",
]

NIVEIS_ACESSO = [
    "Interno",
    "Restrito",
    "Sigiloso",
]


ROTULOS_COLUNAS = {
    "numero": "Número do Processo",
    "area": "Área Jurídica",
    "classe": "Classe Processual",
    "assunto": "Assunto",
    "autor": "Autor",
    "reu": "Réu",
    "prioridade": "Prioridade",
    "situacao": "Situação",
    "responsavel": "Procurador Responsável",
    "providencia_pendente": "Providência Pendente",
    "prazo_relevante": "Prazo Relevante",
    "data_cadastro": "Data de Cadastro",
    "data_atualizacao": "Última Atualização",
}


def preparar_tabela(dados: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    tabela = dados.loc[:, colunas].copy()
    tabela = tabela.fillna("—")

    for coluna in tabela.columns:
        if tabela[coluna].dtype == object:
            tabela[coluna] = tabela[coluna].replace(
                {"": "—", "None": "—", "nan": "—"}
            )

    return tabela.rename(columns=ROTULOS_COLUNAS)


def texto(valor) -> str:
    if valor is None:
        return ""

    if pd.isna(valor):
        return ""

    return str(valor)


def indice_opcao(opcoes: list[str], valor: str, padrao: int = 0) -> int:
    try:
        return opcoes.index(valor)
    except ValueError:
        return padrao


def exibir_processo(processo: pd.Series) -> None:
    titulo = (
        f"{texto(processo.get('numero'))} — "
        f"{texto(processo.get('assunto')) or 'Sem assunto'}"
    )

    with st.expander(titulo):
        col1, col2 = st.columns(2)

        col1.write(
            f"**Área:** {texto(processo.get('area')) or '-'}"
        )
        col1.write(
            f"**Classe:** {texto(processo.get('classe')) or '-'}"
        )
        col1.write(
            f"**Autor:** {texto(processo.get('autor')) or '-'}"
        )
        col1.write(
            f"**Réu:** {texto(processo.get('reu')) or '-'}"
        )
        col1.write(
            f"**Responsável:** "
            f"{texto(processo.get('responsavel')) or '-'}"
        )

        col2.write(
            f"**Prioridade:** "
            f"{texto(processo.get('prioridade')) or '-'}"
        )
        col2.write(
            f"**Situação:** "
            f"{texto(processo.get('situacao')) or '-'}"
        )
        col2.write(
            f"**Nível de acesso:** "
            f"{texto(processo.get('nivel_acesso')) or '-'}"
        )
        col2.write(
            f"**Órgão julgador:** "
            f"{texto(processo.get('orgao_julgador')) or '-'}"
        )
        col2.write(
            f"**Relator:** "
            f"{texto(processo.get('relator')) or '-'}"
        )

        st.markdown("#### Resumo executivo")
        st.write(
            texto(processo.get("resumo_executivo")) or "-"
        )

        st.markdown("#### Providência pendente")
        st.write(
            texto(processo.get("providencia_pendente")) or "-"
        )

        st.markdown("#### Prazo relevante")
        st.write(
            texto(processo.get("prazo_relevante")) or "-"
        )

        st.markdown("#### Resumo jurídico")
        st.write(texto(processo.get("resumo")) or "-")

        st.markdown("#### Palavras-chave")
        st.write(
            texto(processo.get("palavras_chave")) or "-"
        )

        st.caption(
            "Última atualização: "
            f"{texto(processo.get('data_atualizacao')) or '-'}"
        )


marca_sidebar()

pagina_com_icone = st.sidebar.radio(
    "Menu principal",
    [
        "🏠  Dashboard",
        "➕  Cadastrar processo",
        "✏️  Editar processo",
        "🔎  Pesquisar",
        "⭐  Visão da chefia",
        "📂  Processos cadastrados",
    ],
    label_visibility="collapsed",
)
pagina = pagina_com_icone.split("  ", 1)[1]


if pagina == "Dashboard":
    cabecalho_pagina(
        "Sistema Estratégico de Processos",
        "Painel de acompanhamento dos processos estratégicos, prioridades e providências pendentes.",
    )

    processos = listar_processos()

    if processos.empty:
        st.info("Nenhum processo cadastrado.")
    else:
        total = len(processos)

        prioridades_altas = processos[
            processos["prioridade"].eq("Alta")
        ]

        pendencias = processos[
            processos["providencia_pendente"]
            .fillna("")
            .str.strip()
            .ne("")
        ]

        urgentes = processos[processos["prioridade"].eq("Urgente")]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            cartao_indicador("Processos cadastrados", total, "□", "primary")
        with col2:
            cartao_indicador("Urgentes", len(urgentes), "!", "danger")
        with col3:
            cartao_indicador(
                "Alta prioridade", len(prioridades_altas), "↑", "warning"
            )
        with col4:
            cartao_indicador(
                "Providências pendentes", len(pendencias), "✓", "success"
            )

        titulo_secao(
            "Pesquisa rápida",
            "Localize imediatamente um processo por número, parte, assunto, tese ou palavra-chave.",
        )

        termo_dashboard = st.text_input(
            "Pesquisar processos",
            placeholder="Digite o número do processo, uma parte, o assunto ou uma palavra-chave...",
            label_visibility="collapsed",
            key="pesquisa_dashboard",
        )

        if termo_dashboard.strip():
            resultados_dashboard = pesquisar_processos(termo_dashboard)
            if resultados_dashboard.empty:
                st.warning("Nenhum processo foi encontrado.")
            else:
                st.caption(
                    f"{len(resultados_dashboard)} processo(s) encontrado(s)."
                )
                for _, processo in resultados_dashboard.head(10).iterrows():
                    exibir_processo(processo)

        titulo_secao(
            "Cadastros recentes",
            "Acompanhe os dez registros mais recentes do sistema.",
        )

        for _, processo in processos.head(10).iterrows():
            exibir_processo(processo)


elif pagina == "Cadastrar processo":
    cabecalho_pagina("Cadastrar processo", "Inclua um novo processo estratégico no sistema.")

    with st.form(
        "formulario_cadastro",
        clear_on_submit=True,
    ):
        numero = st.text_input("Número do processo *")

        col1, col2 = st.columns(2)

        area = col1.selectbox(
            "Área jurídica",
            AREAS,
        )

        classe = col2.text_input("Classe processual")

        assunto = st.text_input("Assunto")

        col3, col4 = st.columns(2)

        autor = col3.text_input("Autor")
        reu = col4.text_input("Réu")

        col5, col6 = st.columns(2)

        orgao_julgador = col5.text_input("Órgão julgador")
        relator = col6.text_input("Relator")

        resumo = st.text_area(
            "Resumo jurídico do processo",
            height=140,
        )

        palavras_chave = st.text_area(
            "Palavras-chave",
            placeholder=(
                "Ex.: ambiental; embargo; TCA; decadência; APP"
            ),
        )

        st.markdown(
            "### Informações para acompanhamento gerencial"
        )

        col7, col8 = st.columns(2)

        prioridade = col7.selectbox(
            "Prioridade",
            PRIORIDADES,
            index=1,
        )

        situacao = col8.selectbox(
            "Situação",
            SITUACOES,
        )

        col9, col10 = st.columns(2)

        responsavel = col9.text_input(
            "Procurador responsável"
        )

        nivel_acesso = col10.selectbox(
            "Nível de acesso",
            NIVEIS_ACESSO,
        )

        resumo_executivo = st.text_area(
            "Resumo executivo para a chefia",
            placeholder=(
                "Informe o objeto, o risco para o Estado "
                "e a situação atual."
            ),
            height=140,
        )

        providencia_pendente = st.text_area(
            "Providência pendente",
            placeholder=(
                "Ex.: apresentar contestação, solicitar "
                "informações ou aguardar julgamento."
            ),
        )

        prazo_relevante = st.text_input(
            "Prazo relevante",
            placeholder="Ex.: 05/08/2026 — contestação",
        )

        enviar = st.form_submit_button(
            "Cadastrar processo",
            type="primary",
        )

    if enviar:
        if not numero.strip():
            st.error("Informe o número do processo.")
        else:
            try:
                cadastrar_processo(
                    {
                        "numero": numero.strip(),
                        "area": area,
                        "classe": classe.strip(),
                        "assunto": assunto.strip(),
                        "autor": autor.strip(),
                        "reu": reu.strip(),
                        "orgao_julgador": (
                            orgao_julgador.strip()
                        ),
                        "relator": relator.strip(),
                        "resumo": resumo.strip(),
                        "palavras_chave": (
                            palavras_chave.strip()
                        ),
                        "prioridade": prioridade,
                        "situacao": situacao,
                        "responsavel": responsavel.strip(),
                        "nivel_acesso": nivel_acesso,
                        "resumo_executivo": (
                            resumo_executivo.strip()
                        ),
                        "providencia_pendente": (
                            providencia_pendente.strip()
                        ),
                        "prazo_relevante": (
                            prazo_relevante.strip()
                        ),
                    }
                )

                st.success(
                    "Processo cadastrado com sucesso."
                )

            except ProcessoDuplicadoError:
                st.error(
                    "Esse número de processo já está cadastrado."
                )


elif pagina == "Editar processo":
    cabecalho_pagina("Editar processo", "Atualize os dados de um processo já cadastrado.")

    processos = listar_processos()

    if processos.empty:
        st.info("Nenhum processo cadastrado.")
    else:
        opcoes_processos = {
            (
                f"{texto(linha['numero'])} — "
                f"{texto(linha['assunto']) or 'Sem assunto'}"
            ): int(linha["id"])
            for _, linha in processos.iterrows()
        }

        processo_escolhido = st.selectbox(
            "Selecione o processo",
            list(opcoes_processos.keys()),
        )

        processo_id = opcoes_processos[processo_escolhido]
        processo = obter_processo(processo_id)

        if processo is None:
            st.error("Processo não encontrado.")
        else:
            with st.form("formulario_edicao"):
                numero = st.text_input(
                    "Número do processo *",
                    value=texto(processo["numero"]),
                )

                col1, col2 = st.columns(2)

                area = col1.selectbox(
                    "Área jurídica",
                    AREAS,
                    index=indice_opcao(
                        AREAS,
                        texto(processo["area"]),
                    ),
                )

                classe = col2.text_input(
                    "Classe processual",
                    value=texto(processo["classe"]),
                )

                assunto = st.text_input(
                    "Assunto",
                    value=texto(processo["assunto"]),
                )

                col3, col4 = st.columns(2)

                autor = col3.text_input(
                    "Autor",
                    value=texto(processo["autor"]),
                )

                reu = col4.text_input(
                    "Réu",
                    value=texto(processo["reu"]),
                )

                col5, col6 = st.columns(2)

                orgao_julgador = col5.text_input(
                    "Órgão julgador",
                    value=texto(
                        processo["orgao_julgador"]
                    ),
                )

                relator = col6.text_input(
                    "Relator",
                    value=texto(processo["relator"]),
                )

                resumo = st.text_area(
                    "Resumo jurídico do processo",
                    value=texto(processo["resumo"]),
                    height=140,
                )

                palavras_chave = st.text_area(
                    "Palavras-chave",
                    value=texto(
                        processo["palavras_chave"]
                    ),
                )

                st.markdown(
                    "### Informações para acompanhamento gerencial"
                )

                col7, col8 = st.columns(2)

                prioridade = col7.selectbox(
                    "Prioridade",
                    PRIORIDADES,
                    index=indice_opcao(
                        PRIORIDADES,
                        texto(processo["prioridade"]),
                        1,
                    ),
                )

                situacao = col8.selectbox(
                    "Situação",
                    SITUACOES,
                    index=indice_opcao(
                        SITUACOES,
                        texto(processo["situacao"]),
                    ),
                )

                col9, col10 = st.columns(2)

                responsavel = col9.text_input(
                    "Procurador responsável",
                    value=texto(
                        processo["responsavel"]
                    ),
                )

                nivel_acesso = col10.selectbox(
                    "Nível de acesso",
                    NIVEIS_ACESSO,
                    index=indice_opcao(
                        NIVEIS_ACESSO,
                        texto(processo["nivel_acesso"]),
                    ),
                )

                resumo_executivo = st.text_area(
                    "Resumo executivo para a chefia",
                    value=texto(
                        processo["resumo_executivo"]
                    ),
                    height=140,
                )

                providencia_pendente = st.text_area(
                    "Providência pendente",
                    value=texto(
                        processo["providencia_pendente"]
                    ),
                )

                prazo_relevante = st.text_input(
                    "Prazo relevante",
                    value=texto(
                        processo["prazo_relevante"]
                    ),
                )

                salvar = st.form_submit_button(
                    "Salvar alterações",
                    type="primary",
                )

            if salvar:
                if not numero.strip():
                    st.error(
                        "Informe o número do processo."
                    )
                else:
                    try:
                        atualizar_processo(
                            processo_id,
                            {
                                "numero": numero.strip(),
                                "area": area,
                                "classe": classe.strip(),
                                "assunto": assunto.strip(),
                                "autor": autor.strip(),
                                "reu": reu.strip(),
                                "orgao_julgador": (
                                    orgao_julgador.strip()
                                ),
                                "relator": relator.strip(),
                                "resumo": resumo.strip(),
                                "palavras_chave": (
                                    palavras_chave.strip()
                                ),
                                "prioridade": prioridade,
                                "situacao": situacao,
                                "responsavel": (
                                    responsavel.strip()
                                ),
                                "nivel_acesso": nivel_acesso,
                                "resumo_executivo": (
                                    resumo_executivo.strip()
                                ),
                                "providencia_pendente": (
                                    providencia_pendente.strip()
                                ),
                                "prazo_relevante": (
                                    prazo_relevante.strip()
                                ),
                            },
                        )

                        st.success(
                            "Processo atualizado com sucesso."
                        )

                    except ProcessoDuplicadoError:
                        st.error(
                            "Já existe outro processo com esse número."
                        )


elif pagina == "Pesquisar":
    cabecalho_pagina("Pesquisar", "Localize processos por número, parte, assunto, tese ou palavra-chave.")

    termo = st.text_input(
        "Número, parte, assunto, tese ou palavra-chave",
        placeholder=(
            "Ex.: decadência, SEMA ou número do processo"
        ),
    )

    if termo.strip():
        resultados = pesquisar_processos(termo)

        if resultados.empty:
            st.warning("Nenhum processo foi encontrado.")
        else:
            st.success(
                f"{len(resultados)} processo(s) encontrado(s)."
            )

            for _, processo in resultados.iterrows():
                exibir_processo(processo)
    else:
        st.info("Digite um termo para iniciar a pesquisa.")


elif pagina == "Visão da chefia":
    cabecalho_pagina("Visão da chefia", "Acompanhamento concentrado de prioridades e providências.")

    processos = listar_processos()

    if processos.empty:
        st.info("Nenhum processo cadastrado.")
    else:
        urgentes = processos[
            processos["prioridade"].isin(["Alta", "Urgente"])
        ]

        pendentes = processos[
            processos["providencia_pendente"]
            .fillna("")
            .str.strip()
            .ne("")
        ]

        st.markdown("### Processos prioritários")

        if urgentes.empty:
            st.success(
                "Não há processos de prioridade alta ou urgente."
            )
        else:
            for _, processo in urgentes.iterrows():
                exibir_processo(processo)

        st.markdown("### Providências pendentes")

        if pendentes.empty:
            st.success(
                "Não há providências pendentes registradas."
            )
        else:
            colunas = [
                "numero",
                "assunto",
                "prioridade",
                "responsavel",
                "providencia_pendente",
                "prazo_relevante",
            ]

            st.dataframe(
                preparar_tabela(pendentes, colunas),
                use_container_width=True,
                hide_index=True,
            )


elif pagina == "Processos cadastrados":
    cabecalho_pagina("Processos cadastrados", "Relação completa dos registros disponíveis.")

    processos = listar_processos()

    if processos.empty:
        st.info("Nenhum processo cadastrado.")
    else:
        colunas = [
            "numero",
            "area",
            "classe",
            "assunto",
            "autor",
            "reu",
            "prioridade",
            "situacao",
            "responsavel",
            "prazo_relevante",
            "data_cadastro",
            "data_atualizacao",
        ]

        st.dataframe(
            preparar_tabela(processos, colunas),
            use_container_width=True,
            hide_index=True,
        )
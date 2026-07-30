from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from components.ui import (
    cabecalho_pagina,
    carregar_estilos,
    cartao_indicador,
    marca_sidebar,
    titulo_secao,
)

from database import (
    atualizar_processo,
    cadastrar_documento,
    cadastrar_processo,
    criar_url_documento,
    criar_banco,
    excluir_documento,
    listar_documentos,
    listar_processos,
    obter_processo,
    pesquisar_processos,
    DocumentoInvalidoError,
    ProcessoDuplicadoError,
)


st.set_page_config(
    page_title="Processos Estratégicos - SUBPGMA",
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



CATEGORIAS_DOCUMENTAIS = [
    ("decisao", "📑 Decisões relevantes"),
    ("peca", "📄 Peças processuais relevantes"),
    ("outro", "📎 Outros documentos"),
]


def formatar_tamanho(tamanho_bytes) -> str:
    try:
        tamanho = int(tamanho_bytes or 0)
    except (TypeError, ValueError):
        return "—"

    if tamanho < 1024:
        return f"{tamanho} B"
    if tamanho < 1024 * 1024:
        return f"{tamanho / 1024:.1f} KB"
    return f"{tamanho / (1024 * 1024):.1f} MB"


def exibir_categoria_documental(
    processo_id: int,
    categoria: str,
    contexto: str,
) -> None:
    chave_base = f"documentos_{contexto}_{processo_id}_{categoria}"
    documentos = listar_documentos(processo_id, categoria)

    if documentos.empty:
        st.caption("Nenhum documento cadastrado nesta categoria.")
    else:
        for _, documento in documentos.iterrows():
            documento_id = int(documento["id"])
            titulo_documento = texto(documento.get("titulo")) or texto(
                documento.get("nome_arquivo")
            )
            data_documento = texto(documento.get("data_documento"))
            descricao = texto(documento.get("descricao"))
            nome_arquivo = texto(documento.get("nome_arquivo"))
            caminho = texto(documento.get("caminho_storage"))

            st.markdown(f"**{titulo_documento}**")

            detalhes = []
            if data_documento:
                detalhes.append(f"Data: {data_documento}")
            if nome_arquivo:
                detalhes.append(nome_arquivo)
            detalhes.append(formatar_tamanho(documento.get("tamanho_bytes")))
            st.caption(" · ".join(detalhes))

            if descricao:
                st.write(descricao)

            coluna_abrir, coluna_visualizar, coluna_excluir = st.columns([1, 1, 1])
            url = criar_url_documento(caminho)

            with coluna_abrir:
                if url:
                    st.link_button(
                        "Abrir PDF",
                        url,
                        use_container_width=True,
                    )
                else:
                    st.button(
                        "PDF indisponível",
                        key=f"indisponivel_{contexto}_{documento_id}",
                        disabled=True,
                        use_container_width=True,
                    )

            with coluna_visualizar:
                chave_visualizador = f"visualizar_pdf_{contexto}_{documento_id}"
                if st.button(
                    "Visualizar aqui",
                    key=f"botao_{chave_visualizador}",
                    use_container_width=True,
                ):
                    st.session_state[chave_visualizador] = not st.session_state.get(
                        chave_visualizador, False
                    )

            with coluna_excluir:
                if st.button(
                    "Excluir",
                    key=f"excluir_documento_{contexto}_{documento_id}",
                    use_container_width=True,
                ):
                    excluir_documento(documento_id, caminho)
                    st.success("Documento excluído.")
                    st.rerun()

            if st.session_state.get(f"visualizar_pdf_{contexto}_{documento_id}") and url:
                components.iframe(url, height=720, scrolling=True)

            st.markdown("---")

    enviar_documento = False
    titulo_documento = ""
    descricao_documento = ""
    informar_data = False
    data_do_documento = date.today()
    arquivo = None

    with st.expander("➕ Adicionar PDF", expanded=False):
        st.caption("O formulário permanece recolhido até esta seção ser aberta.")
        with st.form(f"form_{chave_base}", clear_on_submit=True):
            titulo_documento = st.text_input(
                "Título do documento *",
                key=f"titulo_{chave_base}",
                placeholder="Ex.: Decisão liminar de 25/06/2026",
            )
            descricao_documento = st.text_area(
                "Descrição",
                key=f"descricao_{chave_base}",
                placeholder="Breve indicação do conteúdo ou da relevância do documento.",
                height=80,
            )
            informar_data = st.checkbox(
                "Informar a data do documento",
                key=f"informar_data_{chave_base}",
            )
            data_do_documento = st.date_input(
                "Data do documento",
                value=date.today(),
                key=f"data_{chave_base}",
                disabled=not informar_data,
                format="DD/MM/YYYY",
            )
            arquivo = st.file_uploader(
                "Arquivo PDF *",
                type=["pdf"],
                accept_multiple_files=False,
                key=f"arquivo_{chave_base}",
            )
            enviar_documento = st.form_submit_button(
                "Adicionar documento",
                type="primary",
            )

    if enviar_documento:
        if not titulo_documento.strip():
            st.error("Informe o título do documento.")
        elif arquivo is None:
            st.error("Selecione um arquivo PDF.")
        else:
            try:
                cadastrar_documento(
                    processo_id=processo_id,
                    categoria=categoria,
                    titulo=titulo_documento,
                    descricao=descricao_documento,
                    data_documento=(
                        data_do_documento.isoformat() if informar_data else None
                    ),
                    nome_arquivo=arquivo.name,
                    conteudo=arquivo.getvalue(),
                )
                st.success("Documento adicionado com sucesso.")
                st.rerun()
            except DocumentoInvalidoError as erro:
                st.error(str(erro))
            except Exception as erro:
                st.error(f"Não foi possível adicionar o documento: {erro}")

def exibir_documentos_processo(processo_id: int, contexto: str) -> None:
    st.markdown("#### Documentos do processo")
    st.caption(
        "Decisões relevantes · Peças processuais relevantes · Outros documentos"
    )

    chave_pasta = f"pasta_documentos_aberta_{processo_id}"
    rotulo_botao = (
        "Fechar pasta de documentos"
        if st.session_state.get(chave_pasta, False)
        else "Abrir pasta de documentos"
    )
    if st.button(
        rotulo_botao,
        key=f"botao_pasta_documentos_{contexto}_{processo_id}",
        use_container_width=True,
    ):
        st.session_state[chave_pasta] = not st.session_state.get(chave_pasta, False)
        st.rerun()

    if not st.session_state.get(chave_pasta, False):
        return

    abas = st.tabs([rotulo for _, rotulo in CATEGORIAS_DOCUMENTAIS])
    for aba, (categoria, _) in zip(abas, CATEGORIAS_DOCUMENTAIS):
        with aba:
            exibir_categoria_documental(processo_id, categoria, contexto)

def exibir_processo(
    processo: pd.Series,
    mostrar_providencia_no_titulo: bool = False,
    contexto: str = "processo",
    expandido: bool = False,
) -> None:
    processo_id = int(processo.get("id"))
    chave_aberto = f"cartao_processo_aberto_{contexto}_{processo_id}"

    if chave_aberto not in st.session_state:
        st.session_state[chave_aberto] = expandido

    numero = texto(processo.get("numero")) or "Sem número"
    assunto = texto(processo.get("assunto")) or "Sem assunto"
    prioridade = texto(processo.get("prioridade")) or "Não informada"
    situacao = texto(processo.get("situacao")) or "Não informada"
    responsavel = texto(processo.get("responsavel")) or "Não informado"
    prazo = texto(processo.get("prazo_relevante")) or "Sem prazo registrado"
    providencia = texto(processo.get("providencia_pendente")).strip()

    icones_prioridade = {
        "Urgente": "🔴",
        "Alta": "🟠",
        "Normal": "🔵",
        "Baixa": "⚪",
    }
    icone_prioridade = icones_prioridade.get(prioridade, "⚪")

    with st.container(border=True):
        st.markdown('<span class="process-card-marker"></span>', unsafe_allow_html=True)

        coluna_principal, coluna_status, coluna_acao = st.columns([5.2, 2.2, 1.45])

        with coluna_principal:
            st.markdown(f"### ⚖️ {numero}")
            st.write(assunto)

        with coluna_status:
            st.caption("PRIORIDADE")
            st.markdown(f"**{icone_prioridade} {prioridade}**")
            st.caption(f"Situação: {situacao}")

        with coluna_acao:
            rotulo = "Fechar" if st.session_state[chave_aberto] else "Abrir processo"
            if st.button(
                rotulo,
                key=f"alternar_cartao_{contexto}_{processo_id}",
                use_container_width=True,
                type="primary" if not st.session_state[chave_aberto] else "secondary",
            ):
                st.session_state[chave_aberto] = not st.session_state[chave_aberto]
                st.rerun()

        coluna_responsavel, coluna_prazo, coluna_providencia = st.columns([1.4, 1.4, 2.6])
        with coluna_responsavel:
            st.caption("RESPONSÁVEL")
            st.write(responsavel)
        with coluna_prazo:
            st.caption("PRAZO RELEVANTE")
            st.write(prazo)
        with coluna_providencia:
            st.caption("PROVIDÊNCIA PENDENTE")
            if providencia:
                st.write(providencia)
            elif mostrar_providencia_no_titulo:
                st.write("Nenhuma providência registrada")
            else:
                st.write("—")

        if not st.session_state[chave_aberto]:
            return

        st.markdown('<div class="process-card-details-marker"></div>', unsafe_allow_html=True)
        st.markdown("---")

        with st.container(border=True):
            st.markdown('<span class="process-block-marker process-block-info"></span>', unsafe_allow_html=True)
            st.markdown("#### 📌 Informações gerais")
            col1, col2 = st.columns(2)

            col1.write(f"**Área:** {texto(processo.get('area')) or '-'}")
            col1.write(f"**Classe:** {texto(processo.get('classe')) or '-'}")
            col1.write(f"**Autor:** {texto(processo.get('autor')) or '-'}")
            col1.write(f"**Réu:** {texto(processo.get('reu')) or '-'}")
            col1.write(f"**Responsável:** {responsavel}")

            col2.write(f"**Prioridade:** {prioridade}")
            col2.write(f"**Situação:** {situacao}")
            col2.write(f"**Nível de acesso:** {texto(processo.get('nivel_acesso')) or '-'}")
            col2.write(f"**Órgão julgador:** {texto(processo.get('orgao_julgador')) or '-'}")
            col2.write(f"**Relator:** {texto(processo.get('relator')) or '-'}")

        with st.container(border=True):
            st.markdown('<span class="process-block-marker process-block-executive"></span>', unsafe_allow_html=True)
            st.markdown("#### 📋 Resumo executivo")
            st.write(texto(processo.get("resumo_executivo")) or "-")

            col_providencia, col_prazo = st.columns([2, 1])
            with col_providencia:
                st.caption("PROVIDÊNCIA PENDENTE")
                st.write(providencia or "-")
            with col_prazo:
                st.caption("PRAZO RELEVANTE")
                st.write(prazo)

        with st.container(border=True):
            st.markdown('<span class="process-block-marker process-block-legal"></span>', unsafe_allow_html=True)
            st.markdown("#### ⚖️ Resumo jurídico")
            st.write(texto(processo.get("resumo")) or "-")

        with st.container(border=True):
            st.markdown('<span class="process-block-marker process-block-keywords"></span>', unsafe_allow_html=True)
            st.markdown("#### 🏷️ Palavras-chave")
            st.write(texto(processo.get("palavras_chave")) or "-")

        with st.container(border=True):
            st.markdown('<span class="process-block-marker process-block-documents"></span>', unsafe_allow_html=True)
            exibir_documentos_processo(processo_id, contexto)

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
        "Processos Estratégicos",
        "Acompanhamento centralizado de prioridades, providências e movimentações relevantes.",
    )

    st.markdown(
        """
        <div class="dashboard-welcome">
            <div>
                <span class="dashboard-kicker">VISÃO GERAL</span>
                <strong>Panorama dos processos estratégicos</strong>
                <p>Consulte os indicadores, localize registros e acompanhe os cadastros mais recentes.</p>
            </div>
            <div class="dashboard-welcome-icon">⚖</div>
        </div>
        """,
        unsafe_allow_html=True,
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

        if "filtro_cartao_dashboard" not in st.session_state:
            st.session_state.filtro_cartao_dashboard = None

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            cartao_indicador(
                "Processos cadastrados",
                total,
                "▦",
                "primary",
                "Todos os registros estratégicos",
            )
            if st.button(
                "Abrir lista",
                key="abrir_todos_dashboard",
                use_container_width=True,
            ):
                st.session_state.filtro_cartao_dashboard = "todos"

        with col2:
            cartao_indicador(
                "Urgentes",
                len(urgentes),
                "!",
                "danger",
                "Necessitam atuação imediata",
            )
            if st.button(
                "Abrir lista",
                key="abrir_urgentes_dashboard",
                use_container_width=True,
            ):
                st.session_state.filtro_cartao_dashboard = "urgentes"

        with col3:
            cartao_indicador(
                "Alta prioridade",
                len(prioridades_altas),
                "↑",
                "warning",
                "Demandas de atenção prioritária",
            )
            if st.button(
                "Abrir lista",
                key="abrir_altas_dashboard",
                use_container_width=True,
            ):
                st.session_state.filtro_cartao_dashboard = "altas"

        with col4:
            cartao_indicador(
                "Providências pendentes",
                len(pendencias),
                "✓",
                "success",
                "Medidas ainda não concluídas",
            )
            if st.button(
                "Abrir lista",
                key="abrir_pendencias_dashboard",
                use_container_width=True,
            ):
                st.session_state.filtro_cartao_dashboard = "pendencias"

        filtro_cartao = st.session_state.filtro_cartao_dashboard

        if filtro_cartao is not None:
            if filtro_cartao == "todos":
                titulo_lista = "Todos os processos cadastrados"
                processos_filtrados = processos
            elif filtro_cartao == "urgentes":
                titulo_lista = "Processos urgentes"
                processos_filtrados = urgentes
            elif filtro_cartao == "altas":
                titulo_lista = "Processos de alta prioridade"
                processos_filtrados = prioridades_altas
            else:
                titulo_lista = "Processos com providências pendentes"
                processos_filtrados = pendencias

            st.markdown("---")
            coluna_titulo, coluna_fechar = st.columns([5, 1])

            with coluna_titulo:
                titulo_secao(
                    titulo_lista,
                    f"{len(processos_filtrados)} processo(s) encontrado(s).",
                )

            with coluna_fechar:
                if st.button(
                    "Fechar lista",
                    key="fechar_lista_dashboard",
                    use_container_width=True,
                ):
                    st.session_state.filtro_cartao_dashboard = None
                    st.rerun()

            if processos_filtrados.empty:
                st.info("Não há processos cadastrados nessa categoria.")
            else:
                for _, processo in processos_filtrados.iterrows():
                    exibir_processo(
                        processo,
                        mostrar_providencia_no_titulo=(
                            filtro_cartao == "pendencias"
                        ),
                        contexto=f"dashboard_filtro_{filtro_cartao}",
                    )

            st.markdown("---")

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
                    exibir_processo(processo, contexto="dashboard_pesquisa")

        titulo_secao(
            "Cadastros recentes",
            "Acompanhe os dez registros mais recentes do sistema.",
        )

        recentes = processos.head(10)

        if "processo_recente_aberto" not in st.session_state:
            st.session_state.processo_recente_aberto = None

        cabecalho_recente = st.columns([1.55, 4.0, 0.75, 1.0, 1.45, 1.55])
        cabecalho_recente[0].markdown("**Número do Processo**")
        cabecalho_recente[1].markdown("**Assunto**")
        cabecalho_recente[2].markdown("**Prioridade**")
        cabecalho_recente[3].markdown("**Situação**")
        cabecalho_recente[4].markdown("**Procurador Responsável**")
        cabecalho_recente[5].markdown("**Última Atualização**")

        st.markdown("---")

        for _, processo in recentes.iterrows():
            processo_id = int(processo["id"])
            colunas_linha = st.columns([1.55, 4.0, 0.75, 1.0, 1.45, 1.55])

            with colunas_linha[0]:
                if st.button(
                    texto(processo.get("numero")) or "Sem número",
                    key=f"abrir_processo_recente_{processo_id}",
                    use_container_width=True,
                    help="Abrir as informações completas deste processo",
                ):
                    st.session_state.processo_recente_aberto = processo_id
                    st.rerun()

            colunas_linha[1].write(texto(processo.get("assunto")) or "—")
            colunas_linha[2].write(texto(processo.get("prioridade")) or "—")
            colunas_linha[3].write(texto(processo.get("situacao")) or "—")
            colunas_linha[4].write(texto(processo.get("responsavel")) or "—")
            colunas_linha[5].write(texto(processo.get("data_atualizacao")) or "—")

        processo_recente_id = st.session_state.processo_recente_aberto
        if processo_recente_id is not None:
            processo_recente = obter_processo(int(processo_recente_id))

            st.markdown("---")
            coluna_titulo_recente, coluna_fechar_recente = st.columns([5, 1])

            with coluna_titulo_recente:
                titulo_secao(
                    "Processo selecionado",
                    "Informações completas do cadastro recente.",
                )

            with coluna_fechar_recente:
                if st.button(
                    "Fechar",
                    key="fechar_processo_recente",
                    use_container_width=True,
                ):
                    st.session_state.processo_recente_aberto = None
                    st.rerun()

            if processo_recente is None:
                st.warning("O processo selecionado não foi encontrado.")
            else:
                exibir_processo(
                    processo_recente,
                    contexto=f"dashboard_recente_selecionado_{processo_recente_id}",
                    expandido=True,
                )


elif pagina == "Cadastrar processo":
    cabecalho_pagina(
        "Cadastrar processo",
        "Inclua um novo processo estratégico no sistema.",
    )

    with st.form(
        "formulario_cadastro",
        clear_on_submit=True,
    ):
        st.markdown("### 1. Dados do processo")
        st.caption(
            "Informe os principais elementos de identificação do processo."
        )

        numero = st.text_input(
            "Número do processo *",
            placeholder="Ex.: 1000000-00.2026.8.11.0000",
        )

        col1, col2 = st.columns(2)
        area = col1.selectbox("Área jurídica", AREAS)
        classe = col2.text_input(
            "Classe processual",
            placeholder="Ex.: Ação Civil Pública",
        )

        assunto = st.text_input(
            "Assunto",
            placeholder="Informe o objeto principal da demanda.",
        )

        col3, col4 = st.columns(2)
        autor = col3.text_input(
            "Autor",
            placeholder="Nome da parte autora.",
        )
        reu = col4.text_input(
            "Réu",
            placeholder="Nome da parte ré.",
        )

        col5, col6 = st.columns(2)
        orgao_julgador = col5.text_input(
            "Órgão julgador",
            placeholder="Ex.: 1ª Vara Especializada da Fazenda Pública",
        )
        relator = col6.text_input(
            "Relator",
            placeholder="Nome do magistrado ou desembargador.",
        )

        st.markdown("---")
        st.markdown("### 2. Análise jurídica")
        st.caption(
            "Registre uma síntese jurídica que facilite a consulta futura."
        )

        resumo = st.text_area(
            "Resumo jurídico do processo",
            placeholder=(
                "Descreva os pedidos, os fundamentos relevantes, "
                "as teses de defesa e a situação processual."
            ),
            height=160,
        )

        palavras_chave = st.text_area(
            "Palavras-chave",
            placeholder="Ex.: ambiental; embargo; TCA; decadência; APP",
            height=90,
        )

        st.markdown("---")
        st.markdown("### 3. Acompanhamento")
        st.caption(
            "Defina a situação atual, o responsável e as medidas pendentes."
        )

        col7, col8 = st.columns(2)
        prioridade = col7.selectbox(
            "Prioridade",
            PRIORIDADES,
            index=1,
        )
        situacao = col8.selectbox("Situação", SITUACOES)

        col9, col10 = st.columns(2)
        responsavel = col9.text_input(
            "Procurador responsável",
            placeholder="Nome do procurador responsável.",
        )
        nivel_acesso = col10.selectbox(
            "Nível de acesso",
            NIVEIS_ACESSO,
        )

        providencia_pendente = st.text_area(
            "Providência pendente",
            placeholder=(
                "Ex.: apresentar contestação, solicitar informações "
                "ou aguardar julgamento."
            ),
            height=110,
        )

        prazo_relevante = st.text_input(
            "Prazo relevante",
            placeholder="Ex.: 05/08/2026 — apresentação de contestação",
        )

        st.markdown("---")
        st.markdown("### 4. Visão da chefia")
        st.caption(
            "Apresente uma síntese objetiva dos riscos e impactos para o Estado."
        )

        resumo_executivo = st.text_area(
            "Resumo executivo para a chefia",
            placeholder=(
                "Informe o objeto da demanda, o risco para o Estado, "
                "a situação atual e as providências mais relevantes."
            ),
            height=160,
        )

        st.markdown("---")
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
                        "orgao_julgador": orgao_julgador.strip(),
                        "relator": relator.strip(),
                        "resumo": resumo.strip(),
                        "palavras_chave": palavras_chave.strip(),
                        "prioridade": prioridade,
                        "situacao": situacao,
                        "responsavel": responsavel.strip(),
                        "nivel_acesso": nivel_acesso,
                        "resumo_executivo": resumo_executivo.strip(),
                        "providencia_pendente": providencia_pendente.strip(),
                        "prazo_relevante": prazo_relevante.strip(),
                    }
                )
                st.success("Processo cadastrado com sucesso.")
            except ProcessoDuplicadoError:
                st.error("Esse número de processo já está cadastrado.")

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
                exibir_processo(processo, contexto="pagina_pesquisar")
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
                exibir_processo(processo, contexto="visao_chefia_prioritarios")

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

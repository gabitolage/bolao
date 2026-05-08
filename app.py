import streamlit as st
import pandas as pd
import requests
import json
import re
import html
from datetime import datetime

API_URL = st.secrets.get("API_URL")


def chamar_api(metodo="get", payload=None, params=None):
    try:
        if metodo == "post":
            resposta = requests.post(API_URL, json=payload, timeout=15)
        else:
            resposta = requests.get(API_URL, params=params, timeout=15)

        resposta.raise_for_status()
    except requests.RequestException:
        st.error("Erro ao conectar com o servidor. Tente novamente em instantes.")
        return None

    try:
        return resposta.json()
    except ValueError:
        texto = resposta.text or ""
        texto_limpo = texto.strip()

        # Alguns backends retornam prefixos anti-XSSI antes do JSON.
        if texto_limpo.startswith(")]}'"):
            texto_limpo = texto_limpo[4:].strip()

        try:
            return json.loads(texto_limpo)
        except ValueError:
            if "<title>Erro</title>" in texto and "Google Apps Script" in texto:
                match = re.search(r"<div style=\"text-align:center[^>]*>(.*?)</div>", texto, re.DOTALL)
                if match:
                    detalhe = html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()
                    st.error(f"Erro no Apps Script: {detalhe}")
                else:
                    st.error("Erro interno no Apps Script.")
            else:
                st.error("O servidor retornou uma resposta inválida.")
            with st.expander("Detalhes da resposta do servidor"):
                st.write(f"Status HTTP: {resposta.status_code}")
                st.write(f"Content-Type: {resposta.headers.get('Content-Type', 'não informado')}")
                st.code(texto[:500] if texto else "(corpo vazio)")
        return None

st.set_page_config(page_title="Bolão Copa", layout="wide")

# CSS para página em geral
st.markdown("""
    <style>
        footer {visibility: hidden;}

        section[data-testid="stSidebar"] {
            display: none !important;
        }

        div[data-testid="stAppViewContainer"] {
            margin-left: 0 !important;
        }

        div[data-testid="stSidebarResizer"],
        div[data-testid="collapsedControl"] {
            display: none !important;
        }

        div[data-testid="stNumberInput"] button {
            display: none !important;
        }

        input[type="number"]::-webkit-outer-spin-button,
        input[type="number"]::-webkit-inner-spin-button {
            -webkit-appearance: none;
            margin: 0;
        }

        input[type="number"] {
            -moz-appearance: textfield;
        }
    </style>
""", unsafe_allow_html=True)

if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = ""
    
# LOGIN / CADASTRO
if not st.session_state.logado:

    st.title("⚽ Bolão da Copa")

    aba = st.tabs(["Login", "Cadastro"])

    # LOGIN
    with aba[0]:

        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):

            dados = chamar_api("post", payload={
                "acao": "login",
                "usuario": usuario,
                "senha": senha
            })

            if dados and dados.get("sucesso"):
                st.session_state.logado = True
                st.session_state.usuario = usuario
                st.rerun()
            elif dados:
                st.error(dados.get("mensagem", "Usuário ou senha inválidos"))
    # CADASTRO
    with aba[1]:

        novo_usuario = st.text_input("Novo usuário")
        nova_senha = st.text_input("Nova senha", type="password")

        if st.button("Cadastrar"):

            dados = chamar_api("post", payload={
                "acao": "cadastro",
                "usuario": novo_usuario,
                "senha": nova_senha
            })

            if dados and dados.get("sucesso"):
                st.session_state.logado = True
                st.session_state.usuario = novo_usuario
                st.rerun()
            elif dados:
                st.error(dados.get("mensagem", "Não foi possível realizar o cadastro"))

# SISTEMA
else:
    
    col_usuario, col_sair = st.columns([0.85, 0.15])

    with col_usuario:
        st.markdown(f"### 👤 {st.session_state.usuario}")

    with col_sair:
        if st.button("Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()

    aba_palpites, aba_ranking = st.tabs(["Palpites", "Ranking"])

    # PALPITES
    with aba_palpites:

        st.title("⚽ Jogos")

        jogos = chamar_api(params={
            "acao": "jogos"
        })

        if not isinstance(jogos, list):
            jogos = []

        palpites = []

        hoje = datetime.now()

        jogos_futuros = []
        for idx, jogo in enumerate(jogos):
            data_jogo = pd.to_datetime(jogo["data"]).tz_localize(None)
            if data_jogo > hoje:
                jogos_futuros.append((idx, jogo, data_jogo))

        for i in range(0, len(jogos_futuros), 2):
            col1, col_div, col2 = st.columns([1, 0.05, 1])

            # Divisor vertical
            with col_div:
                st.markdown("""
                    <style>
                        .divider-vertical {
                            border-left: 1px solid #ddd;
                            height: 200px;
                        }

                        @media (max-width: 768px) {
                            .divider-vertical {
                                display: none;
                            }
                        }
                    </style>
                    <div class="divider-vertical"></div>
                """, unsafe_allow_html=True)

            # Primeiro jogo
            idx, jogo, data_jogo = jogos_futuros[i]
            with col1:
                st.subheader(f'{jogo["mandante"]} x {jogo["visitante"]}')
                st.write(data_jogo.strftime("%d/%m/%Y"))

                c1, c2 = st.columns(2)
                jogo_id = jogo.get("id") or idx

                with c1:
                    mandante = st.number_input(
                        f'{jogo["mandante"]}',
                        min_value=0,
                        max_value=20,
                        value=None,
                        placeholder="-",
                        key=f'm_{jogo_id}'
                    )

                with c2:
                    visitante = st.number_input(
                        f'{jogo["visitante"]}',
                        min_value=0,
                        max_value=20,
                        value=None,
                        placeholder="-",
                        key=f'v_{jogo_id}'
                    )

                if mandante is not None and visitante is not None:
                    palpites.append({
                        "jogo_id": jogo_id,
                        "mandante": mandante,
                        "visitante": visitante
                    })

            # Segundo jogo (se existir)
            if i + 1 < len(jogos_futuros):
                idx, jogo, data_jogo = jogos_futuros[i + 1]
                with col2:
                    st.subheader(f'{jogo["mandante"]} x {jogo["visitante"]}')
                    st.write(data_jogo.strftime("%d/%m/%Y"))

                    c1, c2 = st.columns(2)
                    jogo_id = jogo.get("id") or idx

                    with c1:
                        mandante = st.number_input(
                            f'{jogo["mandante"]}',
                            min_value=0,
                            max_value=20,
                            value=None,
                            placeholder="-",
                            key=f'm_{jogo_id}'
                        )

                    with c2:
                        visitante = st.number_input(
                            f'{jogo["visitante"]}',
                            min_value=0,
                            max_value=20,
                            value=None,
                            placeholder="-",
                            key=f'v_{jogo_id}'
                        )

                    if mandante is not None and visitante is not None:
                        palpites.append({
                            "jogo_id": jogo_id,
                            "mandante": mandante,
                            "visitante": visitante
                        })

            st.divider()

        st.markdown('<div style="height: 80px;"></div>', unsafe_allow_html=True)

        st.markdown("""
            <style>
                div[data-testid="stForm"] {
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    z-index: 99999;
                    height: 72px;
                    padding: 12px 16px;
                    background: transparent; /* footer transparent */
                    border-top: 1px solid rgba(0,0,0,0.12);
                    box-sizing: border-box;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    overflow: visible;
                    backdrop-filter: blur(6px);
                    -webkit-backdrop-filter: blur(6px);
                }

                div[data-testid="stForm"] form {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 100%;
                    height: 100%;
                }

                div[data-testid="stForm"] button,
                div[data-testid="stForm"] .stButton > button {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 32px;
                    font-size: 15px;
                    font-weight: 600;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    display: inline-block;
                    margin: 0; /* centering handled by parent flex */
                    min-width: 220px;
                    max-width: 90vw;
                    white-space: nowrap;
                    box-shadow: 0 6px 18px rgba(76,175,80,0.18);
                }

                div[data-testid="stForm"] button:hover {
                    background-color: #45a049;
                }
            </style>
        """, unsafe_allow_html=True)

        with st.form("salvar_palpites_form", clear_on_submit=False):
            salvar_clicado = st.form_submit_button("💾 Salvar Palpites")

        if salvar_clicado:
            dados = chamar_api("post", payload={
                "acao": "salvar_palpite",
                "usuario": st.session_state.usuario,
                "palpites": palpites
            })

            if dados and dados.get("sucesso", True):
                st.success("Palpites salvos!")
            elif dados:
                st.error(dados.get("mensagem", "Erro ao salvar"))

    # RANKING
    with aba_ranking:

        st.title("🏆 Ranking")

        ranking = chamar_api(params={
            "acao": "ranking"
        })

        if not isinstance(ranking, list):
            ranking = []

        df = pd.DataFrame(ranking)

        if not df.empty:
            df.index = df.index + 1
            st.dataframe(df)
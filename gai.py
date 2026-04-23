import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64 # <-- IMPORTAÇÃO NECESSÁRIA PARA A MARCA D'ÁGUA

# ================= BLOCO 1: MARCA D'ÁGUA FRONTAL (OVERLAY DEFINITIVO) =================
def inject_watermark(nome_paciente, id_sessao):
    paciente_display = nome_paciente if nome_paciente else "PACIENTE NÃO IDENTIFICADO"
    token_display = id_sessao if id_sessao else "TOKEN"
    
    # Criamos o desenho em SVG
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">
        <g transform="translate(150,150) rotate(-45)">
            <text text-anchor="middle" fill="rgba(140, 140, 140, 0.3)" font-size="22" font-family="Arial, sans-serif" font-weight="bold">
                <tspan x="0" dy="-25">INSTRUMENTO SIGILOSO</tspan>
                <tspan x="0" dy="25">{paciente_display}</tspan>
                <tspan x="0" dy="25">{token_display}</tspan>
            </text>
        </g>
    </svg>
    """
    
    # Conversão para Base64
    b64_svg = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    
    # Injeção no ::after do contêiner principal para criar uma película POR CIMA de tudo
    watermark_style = f"""
    <style>
    [data-testid="stAppViewContainer"]::after {{
        content: "";
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background-image: url("data:image/svg+xml;base64,{b64_svg}") !important;
        background-repeat: repeat !important;
        background-position: center !important;
        pointer-events: none !important;
        z-index: 9999999 !important;
    }}
    </style>
    """
    st.markdown(watermark_style, unsafe_allow_html=True)

# ================= CONFIGURAÇÕES DE E-MAIL =================
SEU_EMAIL = st.secrets["EMAIL_USUARIO"]
SENHA_DO_EMAIL = st.secrets["SENHA_USUARIO"]
# ===========================================================

# ================= CONEXÃO COM GOOGLE SHEETS =================
@st.cache_resource
def conectar_planilha():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=escopos)
    client = gspread.authorize(creds)
    return client.open("Controle_Tokens").sheet1 

try:
    planilha = conectar_planilha()
except Exception as e:
    st.error(f"Erro de conexão com a planilha de controle: {e}")
    st.stop()
# =============================================================

def enviar_email_resultados(nome, token, data_nasc, idade, perguntas, respostas):
    total_concordo = sum(1 for r in respostas.values() if r == "Concordo")
    total_discordo = sum(1 for r in respostas.values() if r == "Discordo")
    
    classificacao = "CLÍNICO (Indicativo de sintomas de ansiedade)" if total_concordo >= 13 else "NÃO CLÍNICO"

    assunto = f"Resultados GAI - Paciente: {nome}"
    
    corpo = f"Avaliação GAI (Geriatric Anxiety Inventory) concluída.\n\n"
    corpo += f"=== DADOS DO(A) PACIENTE ===\n\n"
    corpo += f"Nome Completo: {nome}\n"
    corpo += f"Data de Nascimento: {data_nasc}\n"
    corpo += f"Idade Calculada: {idade} anos\n"
    corpo += f"Token de Validação: {token}\n\n"
    
    corpo += f"=== RESUMO DO SCORE ===\n\n"
    corpo += f"CONCORDO: {total_concordo}\n"
    corpo += f"DISCORDO: {total_discordo}\n"
    corpo += f"RESULTADO: {classificacao}\n"
    corpo += f"Ponto de corte: >= 13 pontos para Clínico.\n\n"
    
    corpo += "================ RESPOSTAS ================\n\n"
    for i, pergunta in enumerate(perguntas):
        corpo += f"{pergunta}\n"
        corpo += f"Resposta: {respostas[i]}\n\n"

    msg = MIMEMultipart()
    msg['From'] = SEU_EMAIL
    msg['To'] = "psicologabrunaligoski@gmail.com"
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SEU_EMAIL, SENHA_DO_EMAIL)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

st.set_page_config(page_title="GAI", layout="centered")

# CSS para Título Centralizado e Botão Azul
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 2.5rem !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #003380 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

if "avaliacao_concluida" not in st.session_state:
    st.session_state.avaliacao_concluida = False

# Título Centralizado
st.markdown("<h1 style='text-align: center;'>Clínica de Psicologia e Psicanálise Bruna Ligoski</h1>", unsafe_allow_html=True)

# TELA FINAL
if st.session_state.avaliacao_concluida:
    st.success("Avaliação concluída e enviada com sucesso! Muito obrigado(a) pela sua colaboração.")
    st.stop()

# ================= VALIDAÇÃO SILENCIOSA DO TOKEN E SMART LINK =================
parametros = st.query_params
token_url = parametros.get("token", None)
nome_na_url = parametros.get("nome", "") # Captura do link inteligente

if not token_url:
    st.warning("⚠️ Link de acesso inválido. Solicite um novo link à profissional.")
    st.stop()

try:
    registros = planilha.get_all_records()
    dados_token = None
    linha_alvo = 2 
    for i, reg in enumerate(registros):
        if str(reg.get("Token")) == token_url:
            dados_token = reg
            linha_alvo += i
            break
            
    if not dados_token or dados_token.get("Status") != "Aberto":
        st.error("⚠️ Este link é inválido ou já foi utilizado.")
        st.stop()
except Exception:
    st.error("Erro na validação do link.")
    st.stop()

# ================= QUESTIONÁRIO GAI =================
linha_fina = "<hr style='margin-top: 8px; margin-bottom: 8px;'/>"
st.markdown(linha_fina, unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Avaliação Geriatric Anxiety Inventory (GAI)</h3>", unsafe_allow_html=True)
st.markdown(linha_fina, unsafe_allow_html=True)

st.write("Por favor, responda o questionário a seguir de acordo com o modo como se tem sentido durante a última semana.")
st.markdown(linha_fina, unsafe_allow_html=True)

# --- IDENTIFICAÇÃO FORA DO FORMULÁRIO (Para atualizar a marca d'água dinamicamente) ---
st.subheader("Identificação do(a) Paciente")
nome_paciente = st.text_input("Nome Completo *", value=nome_na_url)
data_nasc = st.date_input("Data de Nascimento *", value=None, format="DD/MM/YYYY", min_value=datetime(1900, 1, 1), max_value=datetime.today())

# --- ATIVA A MARCA D'ÁGUA ---
inject_watermark(nome_paciente, token_url)

st.divider()

perguntas = [
    "1. Ando preocupado(a) a maior parte do tempo.",
    "2. Tenho dificuldades em tomar decisões.",
    "3. Sinto-me inquieto(a) muitas vezes.",
    "4. Tenho dificuldade em relaxar.",
    "5. Muitas vezes não consigo apreciar as coisas por causa das minhas preocupações.",
    "6. Coisas sem importância preocupam-me bastante.",
    "7. Sinto muitas vezes um aperto no estômago.",
    "8. Vejo-me como uma pessoa preocupada.",
    "9. Não consigo evitar preocupar-me, mesmo com coisas menores.",
    "10. Sinto-me muitas vezes nervoso(a).",
    "11. Muitas vezes os meus próprios pensamentos põem-me ansioso(a).",
    "12. Fico com o estômago às voltas devido à minha preocupação constante.",
    "13. Vejo-me como uma pessoa nervosa.",
    "14. Estou sempre à espera que aconteça o pior.",
    "15. Muitas vezes sinto-me agitado(a) interiormente.",
    "16. Acho que as minhas preocupações interferem com a minha vida.",
    "17. Muitas vezes sou dominado(a) pelas minhas preocupações.",
    "18. Por vezes sinto um nó grande no estômago.",
    "19. Deixo de me envolver nas coisas por me preocupar demasiado.",
    "20. Muitas vezes sinto-me aflito(a)."
]

opcoes_respostas = ["Concordo", "Discordo"]

with st.form("form_gai"):
    respostas_coletadas = {}
    for i, p in enumerate(perguntas):
        st.write(f"**{p}**")
        respostas_coletadas[i] = st.radio(f"q_{i}", opcoes_respostas, index=None, label_visibility="collapsed")
        st.divider()

    st.markdown("<small>Fonte: Pachana, N. A., et al. (2006). Geriatric Anxiety Inventory.</small>", unsafe_allow_html=True)

    if st.form_submit_button("Enviar Avaliação"):
        if not nome_paciente or data_nasc is None or any(r is None for r in respostas_coletadas.values()):
            st.error("Por favor, preencha todos os campos e responda todas as questões.")
        else:
            hoje = datetime.today().date()
            idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
            
            if enviar_email_resultados(nome_paciente, token_url, data_nasc.strftime("%d/%m/%Y"), idade, perguntas, respostas_coletadas):
                try:
                    planilha.update_cell(linha_alvo, 5, "Respondido")
                    st.session_state.avaliacao_concluida = True
                    st.rerun()
                except:
                    st.session_state.avaliacao_concluida = True
                    st.rerun()
            else:
                st.error("Erro ao enviar.")

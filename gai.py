import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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
    return client.open("GAI").sheet1  # Aponta para a nova planilha GAI

try:
    planilha = conectar_planilha()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()
# =============================================================

def enviar_email_resultados(nome, cpf, data_nasc, idade, perguntas, respostas):
    assunto = f"Resultados GAI - Paciente: {nome}"
    
    corpo = f"Avaliação GAI concluída.\n\n"
    corpo += f"=== DADOS DO(A) PACIENTE ===\n\n"
    corpo += f"Nome Completo: {nome}\n"
    corpo += f"Data de Nascimento: {data_nasc}\n"
    corpo += f"CPF (Login): {cpf}\n"
    corpo += f"Idade Calculada: {idade} anos\n\n"
    corpo += "================ RESULTADOS ================\n\n"
    
    # Adiciona cada pergunta e a resposta do paciente logo abaixo
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

if "logado" not in st.session_state:
    st.session_state.logado = False
if "avaliacao_concluida" not in st.session_state:
    st.session_state.avaliacao_concluida = False

st.title("Clínica de Psicologia e Psicanálise Bruna Ligoski")

# ================= TELA DE LOGIN =================
if not st.session_state.logado:
    st.write("Bem-vindo(a) à Avaliação GAI.")
    
    with st.form("form_login"):
        cpf_input = st.text_input("CPF do Paciente (Apenas números)")
        senha_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            if senha_input == st.secrets["SENHA_MESTRA"]:
                try:
                    cpfs = planilha.col_values(1)
                except:
                    cpfs = []
                if cpf_input in cpfs:
                    st.error("Acesso bloqueado. CPF já registrado.")
                else:
                    st.session_state.logado = True
                    st.session_state.cpf_paciente = cpf_input
                    st.rerun()
            else:
                st.error("Senha incorreta.")

# ================= TELA FINAL =================
elif st.session_state.avaliacao_concluida:
    st.success("Avaliação concluída e enviada com sucesso! Muito obrigado pela sua colaboração.")

# ================= QUESTIONÁRIO GAI =================
else:
    st.write("Por favor, responda o questionário a seguir de acordo com o modo como se tem sentido durante a última semana.")
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
        "10. Sinto-me muitas vezes nervoso (a).",
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

    with st.form("formulario_avaliacao"):
        st.subheader("Identificação do Paciente")
        nome_paciente = st.text_input("Nome Completo *")
        
        # Calendário iniciando em branco (value=None)
        data_nasc = st.date_input("Data de Nascimento *", value=None, format="DD/MM/YYYY", min_value=datetime(1900, 1, 1), max_value=datetime.today())
        st.divider()

        respostas_coletadas = {}
        for i, p in enumerate(perguntas):
            st.write(f"**{p}**")
            respostas_coletadas[i] = st.radio(f"q_{i}", opcoes_respostas, index=None, label_visibility="collapsed")
            st.write("---")

        # Citação em letras menores no final do formulário
        st.markdown("<small>Fonte: Pachana, N. A., Byrne, G. J, Siddle, H., Koloski, N., Harley, E., & Arnold, E. (2006). Development and validation of the Geriatric Anxiety Inventory. International Psychogeriatrics, 19(1), 103-114.</small>", unsafe_allow_html=True)
        st.write("") # Espaço antes do botão

        if st.form_submit_button("Finalizar"):
            # Validação: verifica se nome e data foram preenchidos e se todas as 20 perguntas têm resposta
            if not nome_paciente or data_nasc is None or any(r is None for r in respostas_coletadas.values()):
                st.error("Preencha todos os campos e responda todas as questões.")
            else:
                hoje = datetime.today().date()
                idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
                
                # Envia o e-mail passando a lista de perguntas e o dicionário de respostas
                if enviar_email_resultados(nome_paciente, st.session_state.cpf_paciente, data_nasc.strftime("%d/%m/%Y"), idade, perguntas, respostas_coletadas):
                    try:
                        planilha.append_row([st.session_state.cpf_paciente])
                    except:
                        pass
                    st.session_state.avaliacao_concluida = True
                    st.rerun()
                else:
                    st.error("Houve um erro no envio. Avise a profissional responsável.")

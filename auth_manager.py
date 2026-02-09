
import gspread
import hashlib
import streamlit as st

def conectar_sheets():
    """Conecta ao Google Sheets e retorna a planilha principal."""
    try:
        if "gc" not in st.session_state:
            # Tenta pegar das secrets do Streamlit Cloud
            if "gcp_service_account" in st.secrets:
                credentials_dict = dict(st.secrets["gcp_service_account"])
                st.session_state.gc = gspread.service_account_from_dict(credentials_dict)
            else:
                # Fallback para arquivo local
                st.session_state.gc = gspread.service_account(filename="credenciais.json")
        sh = st.session_state.gc.open("listagem_empenhos")
        return sh
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None

def init_usuarios():
    """Inicializa a planilha de usuários se não existir."""
    sh = conectar_sheets()
    if not sh:
        return

    try:
        ws = sh.worksheet("usuarios")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="usuarios", rows=100, cols=4)
        ws.append_row(["Usuario", "Senha", "Perfil", "Departamento"])

def hash_senha(senha):
    """Retorna o hash SHA-256 da senha."""
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_login(usuario, senha):
    """Verifica se o usuário e senha correspondem."""
    sh = conectar_sheets()
    if not sh:
        return False, None, None

    init_usuarios() # Garante que a planilha existe
    ws = sh.worksheet("usuarios")
    registros = ws.get_all_records()

    senha_hash = hash_senha(senha)

    if not registros:
        return False, None, None

    # Detectar o nome correto da coluna de usuário (com ou sem acento)
    chaves = registros[0].keys()
    col_usuario = next((k for k in chaves if k.lower().strip() == "usuario" or k.lower().strip() == "usuário"), None)
    
    if not col_usuario:
        st.error("Erro na planilha: Coluna 'Usuario' ou 'Usuário' não encontrada.")
        return False, None, None

    for r in registros:
        if str(r[col_usuario]).strip() == usuario and r["Senha"] == senha_hash:
            return True, r["Perfil"], r["Departamento"]

    return False, None, None

def cadastrar_usuario(usuario, senha, perfil, departamento):
    """Cadastra um novo usuário."""
    sh = conectar_sheets()
    if not sh:
        return False, "Erro de conexão."

    init_usuarios()
    ws = sh.worksheet("usuarios")
    registros = ws.get_all_records()

    # Verificar duplicidade
    chaves = registros[0].keys() if registros else []
    col_usuario = next((k for k in chaves if k.lower().strip() == "usuario" or k.lower().strip() == "usuário"), "Usuario")

    for r in registros:
        if str(r.get(col_usuario, "")).strip() == usuario:
            return False, "Usuário já existe."

    senha_hash = hash_senha(senha)
    ws.append_row([usuario, senha_hash, perfil, departamento])
    return True, "Usuário cadastrado com sucesso!"

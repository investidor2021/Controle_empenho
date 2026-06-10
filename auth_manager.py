
import gspread
import hashlib
import streamlit as st
import io
import re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


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
        # Adicionado coluna PrimeiroAcesso
        ws = sh.add_worksheet(title="usuarios", rows=100, cols=5)
        ws.append_row(["Usuario", "Senha", "Perfil", "Departamento", "PrimeiroAcesso"])

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

    # Tentar achar a coluna PrimeiroAcesso, senao default False
    col_primeiro = next((k for k in chaves if "primeiro" in k.lower()), None)

    for r in registros:
        if str(r[col_usuario]).strip() == usuario and r["Senha"] == senha_hash:
            # Se a coluna PrimeiroAcesso não existe na planilha antiga, assume False
            primeiro_acesso = str(r.get(col_primeiro, "FALSE")).strip().upper() == "TRUE" if col_primeiro else False
            return True, r["Perfil"], r["Departamento"], primeiro_acesso

    return False, None, None, False

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
    # Por padrão, novo usuário DEVE trocar a senha
    ws.append_row([usuario, senha_hash, perfil, departamento, "TRUE"])
    return True, "Usuário cadastrado com sucesso!"

def alterar_senha(usuario, senha_antiga, senha_nova):
    """Altera a senha de um usuário existente."""
    sh = conectar_sheets()
    if not sh:
        return False, "Erro de conexão com o banco de dados."

    init_usuarios()
    ws = sh.worksheet("usuarios")
    registros = ws.get_all_records()

    if not registros:
        return False, "Nenhum usuário encontrado."

    chaves = list(registros[0].keys())
    col_usuario = next((k for k in chaves if k.lower().strip() == "usuario" or k.lower().strip() == "usuário"), "Usuario")
    
    # Encontrar o índice da coluna "Senha" (1-based para gspread)
    col_senha_idx = 0
    for i, key in enumerate(chaves):
        if key.lower().strip() == "senha":
            col_senha_idx = i + 1
            break
            
    if col_senha_idx == 0:
        return False, "Coluna 'Senha' não encontrada no banco."

    senha_antiga_hash = hash_senha(senha_antiga)
    senha_nova_hash = hash_senha(senha_nova)
    
    # Encontrar o índice da coluna "PrimeiroAcesso" (1-based para gspread)
    col_primeiro_idx = next((i + 1 for i, key in enumerate(chaves) if "primeiro" in key.lower()), 0)

    # Buscar na planilha
    for idx, r in enumerate(registros):
        if str(r.get(col_usuario, "")).strip() == usuario:
            if r.get("Senha") == senha_antiga_hash:
                try:
                    # Atualiza a célula correspondente.
                    ws.update_cell(idx + 2, col_senha_idx, senha_nova_hash)
                    
                    # Tira a flag de PrimeiroAcesso se existir
                    if col_primeiro_idx > 0:
                        ws.update_cell(idx + 2, col_primeiro_idx, "FALSE")
                        
                    return True, "Senha alterada com sucesso!"
                except Exception as e:
                    return False, f"Erro ao atualizar a senha: {e}"
            else:
                return False, "Senha atual incorreta."

    return False, "Usuário não encontrado."
    
def redefinir_senha_admin(usuario):
    """Redefine a senha de um usuário para '12345678' e força PrimeiroAcesso = TRUE."""
    sh = conectar_sheets()
    if not sh:
        return False, "Erro de conexão."

    init_usuarios()
    ws = sh.worksheet("usuarios")
    registros = ws.get_all_records()

    if not registros:
        return False, "Nenhum usuário encontrado."

    chaves = list(registros[0].keys())
    col_usuario = next((k for k in chaves if k.lower().strip() == "usuario" or k.lower().strip() == "usuário"), "Usuario")
    
    col_senha_idx = 0
    for i, key in enumerate(chaves):
        if key.lower().strip() == "senha":
            col_senha_idx = i + 1
            break
            
    col_primeiro_idx = next((i + 1 for i, key in enumerate(chaves) if "primeiro" in key.lower()), 0)

    if col_senha_idx == 0:
        return False, "Coluna 'Senha' não encontrada."

    senha_padrao_hash = hash_senha("12345678")

    for idx, r in enumerate(registros):
        if str(r.get(col_usuario, "")).strip() == usuario:
            try:
                # 1. Atualizar a senha para 12345678
                ws.update_cell(idx + 2, col_senha_idx, senha_padrao_hash)
                # 2. Forçar troca de senha no próximo login
                if col_primeiro_idx > 0:
                    ws.update_cell(idx + 2, col_primeiro_idx, "TRUE")
                else:
                    # Se achar que a coluna não existe, tenta append? Perigoso, exige migração manual do admin no sheets
                    pass
                return True, f"Senha de {usuario} redefinida para '12345678'!"
            except Exception as e:
                return False, f"Erro ao atualizar: {e}"

    return False, "Usuário não encontrado."

def get_all_users():
    """Retorna uma lista de dicionários com os dados de todos os usuários."""
    sh = conectar_sheets()
    if not sh:
        return []

    init_usuarios()
    try:
        ws = sh.worksheet("usuarios")
        return ws.get_all_records()
    except Exception as e:
        st.error(f"Erro ao buscar usuários: {e}")
        return []

def conectar_drive():
    """Conecta ao Google Drive API e retorna o serviço."""
    try:
        if "gcp_service_account" in st.secrets:
            credentials_dict = dict(st.secrets["gcp_service_account"])
            scopes = ['https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        else:
            scopes = ['https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file("credenciais.json", scopes=scopes)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Drive API: {e}")
        return None

def upload_para_drive(file_bytes, file_name, mime_type, folder_id):
    """
    Realiza o upload de um arquivo para o Google Drive.
    Retorna (link_visualizacao, erro).
    """
    service = conectar_drive()
    if not service:
        return None, "Não foi possível conectar ao Google Drive."
    
    try:
        # Remover parâmetros de query se vierem no folder_id (como ?hl no ID enviado pelo usuário)
        clean_folder_id = folder_id.split('?')[0].strip() if folder_id else ""
        
        file_metadata = {
            'name': file_name,
            'parents': [clean_folder_id]
        }
        
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        
        file_drive = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Alterar a permissão do arquivo para que qualquer pessoa com o link possa ler
        try:
            user_permission = {
                'type': 'anyone',
                'role': 'reader',
            }
            service.permissions().create(
                fileId=file_drive.get('id'),
                body=user_permission,
                fields='id',
            ).execute()
        except Exception as perm_err:
            st.warning(f"Aviso: Não foi possível definir permissões de leitura pública: {perm_err}")
            
        return file_drive.get('webViewLink'), None
    except Exception as e:
        return None, f"Erro no upload para o Drive: {str(e)}"

def deletar_do_drive(file_id):
    """Deleta um arquivo do Google Drive."""
    service = conectar_drive()
    if not service:
        return False, "Não foi possível conectar ao Google Drive."
    try:
        service.files().delete(fileId=file_id).execute()
        return True, None
    except Exception as e:
        return False, f"Erro ao deletar arquivo do Drive: {str(e)}"

def obter_configuracao(chave, default=""):
    """Recupera uma configuração persistente armazenada na aba 'configuracoes' da planilha."""
    sh = conectar_sheets()
    if not sh:
        return default
    try:
        try:
            ws = sh.worksheet("configuracoes")
        except gspread.WorksheetNotFound:
            # Se não existir a aba, criamos e retornamos o padrão
            ws = sh.add_worksheet(title="configuracoes", rows=10, cols=2)
            ws.append_row(["Chave", "Valor"])
            ws.append_row([chave, default])
            return default
            
        registros = ws.get_all_records()
        for r in registros:
            if str(r.get("Chave", "")).strip() == chave:
                return str(r.get("Valor", "")).strip()
    except Exception:
        pass
    return default

def salvar_configuracao(chave, valor):
    """Salva uma configuração persistente na aba 'configuracoes' da planilha."""
    sh = conectar_sheets()
    if not sh:
        return False
    try:
        try:
            ws = sh.worksheet("configuracoes")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="configuracoes", rows=10, cols=2)
            ws.append_row(["Chave", "Valor"])
            
        registros = ws.get_all_records()
        col_chave_idx = 1
        col_valor_idx = 2
        
        for idx, r in enumerate(registros):
            if str(r.get("Chave", "")).strip() == chave:
                row_number = idx + 2 # +1 cabeçalho, +1 index base 1
                ws.update_cell(row_number, col_valor_idx, valor)
                return True
                
        # Se não encontrou, insere uma nova linha
        ws.append_row([chave, valor])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar configuração: {e}")
        return False


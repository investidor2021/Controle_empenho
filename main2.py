import streamlit as st
import pandas as pd
import uuid
import io
import time
import gspread
from google.oauth2.service_account import Credentials
import data_processor


import auth_manager
import time


# Move page config to top (done in previous chunk)
st.set_page_config(layout="wide")

# Estilos CSS personalizados para tornar a interface mais limpa e compacta (incluindo botões de anexo)
st.markdown("""
<style>
/* Tornar o widget de upload de arquivo (st.file_uploader) super compacto e horizontal */
div[data-testid="stFileUploader"] {
    padding: 0px !important;
    margin: 0px !important;
}
div[data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] {
    padding: 4px 10px !important;
    min-height: 38px !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 8px !important;
    border-radius: 6px !important;
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px dashed rgba(255, 255, 255, 0.2) !important;
}
/* Ocultar a descrição do limite de tamanho para economizar espaço vertical */
div[data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] small {
    display: none !important;
}
/* Reduzir o tamanho da fonte do texto dentro da área de dropzone */
div[data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] div {
    font-size: 11px !important;
    margin: 0 !important;
    padding: 0 !important;
    color: rgba(255, 255, 255, 0.7) !important;
}
/* Estilizar o botão Browse Files para ficar menor e elegante */
div[data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] button {
    padding: 2px 6px !important;
    font-size: 11px !important;
    min-height: 26px !important;
    line-height: 1.2 !important;
}

/* Tornar o botão de link e os botões padrão menores e mais ajustados na tabela */
div[data-testid="stLinkButton"] a {
    padding: 4px 10px !important;
    font-size: 12px !important;
    min-height: 28px !important;
    height: 28px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 6px !important;
}
/* Botão normal (como o botão de excluir) */
div[data-testid="stBaseButton-secondary"] button {
    padding: 4px 10px !important;
    font-size: 12px !important;
    min-height: 28px !important;
    height: 28px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "perfil" not in st.session_state:
    st.session_state.perfil = None
if "departamento" not in st.session_state:
    st.session_state.departamento = None
if "primeiro_acesso" not in st.session_state:
    st.session_state.primeiro_acesso = False

# ===============================
# SIDEBAR LOGIN / CADASTRO
# ===============================
st.sidebar.title("Acesso ao Sistema")

if not st.session_state.usuario:
    st.markdown("""
    <style>
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.03); }
        100% { transform: scale(1); }
    }
    .landing-card {
        text-align: center;
        margin: 8% auto;
        max-width: 750px;
        padding: 50px;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.25);
        color: white;
        font-family: 'Inter', 'Outfit', sans-serif;
    }
    .landing-title {
        font-size: 2.6rem;
        margin-bottom: 20px;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .landing-desc {
        font-size: 1.2rem;
        opacity: 0.9;
        margin-bottom: 40px;
        font-weight: 300;
        line-height: 1.6;
    }
    .login-prompt {
        display: inline-block;
        padding: 15px 30px;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 50px;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        font-size: 1.1rem;
        font-weight: 500;
        border: 1px solid rgba(255, 255, 255, 0.25);
        box-shadow: 0 5px 15px rgba(0,0,0,0.15);
        animation: pulse 2.5s infinite ease-in-out;
    }
    </style>
    
    <div class="landing-card">
        <h1 class="landing-title">🏛️ Acompanhamento de Empenhos</h1>
        <p class="landing-desc">
            Sistema inteligente e integrado para gestão de dotações, controle de prazos de empenhos e acompanhamento de forma simplificada.
        </p>
        <div class="login-prompt">
            👈 Para acessar a ferramenta, por favor realize o login no <b>menu lateral esquerdo</b>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.title("Login")
    login_user = st.sidebar.text_input("Usuário")
    login_pass = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        sucesso, perfil, depto, p_acesso = auth_manager.verificar_login(login_user.strip(), login_pass)
        if sucesso:
            st.session_state.usuario = login_user
            st.session_state.perfil = perfil
            st.session_state.departamento = depto
            st.session_state.primeiro_acesso = p_acesso
            st.success("Login realizado!")
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos.")

    st.stop() # Para a execução se não estiver logado

# Se chegou aqui, está logado
st.sidebar.markdown(f"👤 **{st.session_state.usuario}**")
st.sidebar.markdown(f"🔹 {st.session_state.perfil}")
if st.sidebar.button("Sair"):
    st.session_state.usuario = None
    st.session_state.perfil = None
    st.session_state.departamento = None
    st.rerun()

# --- Módulo Alterar Senha ---
with st.sidebar.expander("🔑 Alterar Senha"):
    senha_atual = st.text_input("Senha Atual", type="password", key="senha_atual")
    nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha")
    confirmar_senha = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha")
    
    if st.button("Salvar Nova Senha"):
        if nova_senha and confirmar_senha and senha_atual:
            if nova_senha == confirmar_senha:
                ok, msg = auth_manager.alterar_senha(st.session_state.usuario, senha_atual, nova_senha)
                if ok:
                    st.success(msg)
                    st.session_state.primeiro_acesso = False
                    # Dá um timerzinho e reseta
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("As novas senhas não coincidem.")
        else:
            st.warning("Preencha todos os campos para alterar a senha.")

# Bloqueio de Primeiro Acesso
if st.session_state.primeiro_acesso:
    st.warning("⚠️ Bem-vindo(a) ao seu primeiro acesso! É obrigatório mudar a sua senha provisória antes de continuar utilizando o sistema.")
    st.info("Utilize o menu lateral '🔑 Alterar Senha' para configurar a sua senha definitiva.")
    st.stop() # Bloqueia o carregamento do restante da página

perfil = st.session_state.perfil
departamento_usuario = st.session_state.departamento

    
    
def conectar_sheets():
    sh = auth_manager.conectar_sheets()
    # auth_manager já retorna a planilha "listagem_empenhos" aberta
    # Precisamos da aba "emp_controle" (ou "empenhos" se for o caso - verificar original)
    # No código anterior era "emp_controle".
    try:
        ws = sh.worksheet("emp_controle")
        return ws
    except Exception as e:
        st.error(f"Erro ao acessar aba de empenhos: {e}")
        return None


def normalize_empenho(val):
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str


def get_worksheet_data(ws):
    """
    Robust alternative to ws.get_all_records().
    Retrieves all values and parses them into a list of dicts,
    ignoring empty trailing columns and avoiding duplicate header errors.
    """
    all_values = ws.get_all_values()
    if not all_values:
        return []
    
    headers = all_values[0]
    # Find last non-empty header
    last_non_empty_idx = -1
    for idx, h in enumerate(headers):
        if str(h).strip() != "":
            last_non_empty_idx = idx
            
    if last_non_empty_idx == -1:
        return []
        
    valid_headers = [str(h).strip() for h in headers[:last_non_empty_idx + 1]]
    records = []
    for row in all_values[1:]:
        row_trimmed = row[:last_non_empty_idx + 1]
        row_trimmed += [""] * (len(valid_headers) - len(row_trimmed))
        records.append(dict(zip(valid_headers, row_trimmed)))
        
    return records


@st.cache_data(ttl=60) # Cache por 60 segundos para evitar recarregar toda hora
def carregar_empenhos():
    ws = conectar_sheets()
    if ws is None:
        st.error("Erro ao conectar com o Google Sheets")
        return pd.DataFrame()
    
    try:
        dados = get_worksheet_data(ws)
        df = pd.DataFrame(dados)
        
        # Debug: mostrar informações sobre os dados carregados
        if df.empty:
            st.warning(f"⚠️ A planilha do Google Sheets está vazia. Total de linhas: {len(ws.get_all_values())}")
        else:
            st.info(f"✅ Dados carregados: {len(df)} registros, {len(df.columns)} colunas")
            
            # Debug detalhado: mostrar uma amostra dos dados
            with st.expander("🔍 Debug: Ver dados brutos do Google Sheets"):
                st.write("**Colunas:**", list(df.columns))
                st.write("**Primeiras 3 linhas:**")
                st.dataframe(df.head(3))
                
                # Mostrar tipos de dados das colunas
                st.write("**Tipos de dados:**")
                st.write(df.dtypes)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()




def format_currency(val):
    try:
        val_str = str(val).strip()
        
        # Se já tem R$, retorna como está
        if val_str.startswith("R$"):
            return val_str
        
        # Se está vazio
        if not val_str or val_str == "":
            return "R$ 0,00"
        
        # Converter para float e formatar no padrão brasileiro
        if isinstance(val, (int, float)):
            val_float = float(val)
        else:
            # Tentar converter string para float
            # Remover possíveis formatações
            val_clean = val_str.replace(" ", "").replace("R$", "")
            
            # Se tem vírgula E ponto, é formato brasileiro (1.234,56)
            if "," in val_clean and "." in val_clean:
                val_clean = val_clean.replace(".", "").replace(",", ".")
            # Se tem apenas vírgula, é formato brasileiro sem milhar (123,45)
            elif "," in val_clean:
                val_clean = val_clean.replace(",", ".")
            
            val_float = float(val_clean)
        
        # Formatar no padrão brasileiro com 2 casas decimais
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)




    
def salvar_observacao(empenho, key):
    novo_texto = st.session_state[key]
    ws = conectar_sheets()
    registros = get_worksheet_data(ws)

    if not registros:
        return

    # Detectar colunas dinamicamente
    cabecalho = list(registros[0].keys())
    
    # Achar índice da coluna de Empenho (base 1)
    col_empenho_idx = next((i for i, c in enumerate(cabecalho) if "empenho" in c.lower()), -1)
    
    # Achar índice da coluna de Observação (base 1)
    # Se não achar "Observação" exata, tenta criar ou usar a última?
    # O data_processor garante que cria "Observação", então deve existir.
    col_obs_idx = next((i for i, c in enumerate(cabecalho) if "observação" in c.lower() or "observacao" in c.lower()), -1)
    
    if col_empenho_idx == -1 or col_obs_idx == -1:
        st.error("Não foi possível encontrar as colunas necessárias.")
        return
    
    # Procurar linha do empenho
    for idx, reg in enumerate(registros):
        if normalize_empenho(reg.get(cabecalho[col_empenho_idx])) == normalize_empenho(empenho):
            row_number = idx + 2  # +1 para base 1, +1 para pular cabeçalho
            # col_letter_obs = chr(65 + col_obs_idx)  # Converter índice para letra (A, B, C...) # Not used
            
            # Adicionar timestamp à observação
            timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
            texto_com_timestamp = f"{novo_texto}\n[Atualizado em: {timestamp}]" if novo_texto.strip() else ""
            
            ws.update_cell(row_number, col_obs_idx + 1, texto_com_timestamp)
            st.success(f"Observação salva para empenho {empenho}!")
            time.sleep(1)
            st.cache_data.clear() # Limpar cache para forçar recarregamento do Google Sheets
            st.rerun()
            return
    
    st.error(f"Empenho {empenho} não encontrado.")


def extrair_id_drive(url):
    if not url:
        return None
    import re
    match = re.search(r'/d/([^/&?]+)', str(url))
    if match:
        return match.group(1)
    if len(str(url)) > 20 and "/" not in str(url):
        return str(url)
    return None

def salvar_link_anexo(empenho, link):
    ws = conectar_sheets()
    if not ws:
        return False
    try:
        registros = get_worksheet_data(ws)
    except Exception as e:
        st.error(f"Erro ao ler registros para salvar anexo: {e}")
        return False

    if not registros:
        return False

    cabecalho = list(registros[0].keys())
    col_empenho_idx = next((i for i, c in enumerate(cabecalho) if "empenho" in c.lower()), -1)
    col_anexo_idx = next((i for i, c in enumerate(cabecalho) if "anexo" in c.lower()), -1)
    
    if col_empenho_idx == -1:
        st.error("Não foi possível encontrar a coluna de Empenho.")
        return False
        
    if col_anexo_idx == -1:
        # Se não existe a coluna "Anexo", vamos adicioná-la no final do cabeçalho da planilha
        try:
            ws.update_cell(1, len(cabecalho) + 1, "Anexo")
            col_anexo_idx = len(cabecalho)
        except Exception as e:
            st.error(f"Erro ao criar coluna 'Anexo': {e}")
            return False

    # Procurar linha do empenho
    for idx, reg in enumerate(registros):
        if normalize_empenho(reg.get(cabecalho[col_empenho_idx])) == normalize_empenho(empenho):
            row_number = idx + 2  # +1 para base 1, +1 para pular cabeçalho
            try:
                ws.update_cell(row_number, col_anexo_idx + 1, link)
                st.cache_data.clear() # Limpar cache
                return True
            except Exception as e:
                st.error(f"Erro ao salvar link do anexo no Sheets: {e}")
                return False
    
    st.error(f"Empenho {empenho} não encontrado para salvar anexo.")
    return False

def salvar_anexo_process(empenho, uploaded_file):
    if uploaded_file is None:
        return
        
    folder_id = auth_manager.obter_configuracao("DRIVE_FOLDER_ID", "1qLk6PQXHtr987d6csDrQD5U2YmE74zp3")
    if not folder_id:
        st.error("Erro: A pasta do Google Drive não está configurada.")
        return
        
    nome_original = uploaded_file.name
    ext = nome_original.split('.')[-1] if '.' in nome_original else 'pdf'
    nome_arquivo_drive = f"Anexo_Empenho_{empenho}.{ext}"
    
    file_bytes = uploaded_file.read()
    mime_type = uploaded_file.type
    
    link_anexo, err = auth_manager.upload_para_drive(file_bytes, nome_arquivo_drive, mime_type, folder_id)
    
    if err:
        st.error(err)
        return
        
    if salvar_link_anexo(empenho, link_anexo):
        st.success(f"Documento anexado com sucesso para o empenho {empenho}!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

def deletar_anexo_process(empenho, url):
    file_id = extrair_id_drive(url)
    if file_id:
        success, err = auth_manager.deletar_do_drive(file_id)
        if not success:
            st.error(f"Erro ao remover do Drive: {err}. Limpando link na planilha mesmo assim...")
            
    if salvar_link_anexo(empenho, ""):
        st.success(f"Anexo removido do empenho {empenho}!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()


# ===============================
# NAVEGAÇÃO
# ===============================
if st.session_state.perfil == "Administrador":
    modo = st.sidebar.radio("Ferramenta", ["Gerador de Documentos", "Organizador de Planilhas", "Gerenciar Usuários", "Configurações"])
else:
    modo = "Gerador de Documentos" # Usuário padrão só vê isso

if modo == "Organizador de Planilhas":
    st.title("📂 Organizador de Planilhas")
    st.markdown("Extrai colunas (D, F, H, J, K, W, AJ), mapeia departamentos e verifica prazos.")
    st.markdown("O arquivo é o analitico de empenho no formato .xlsx com ponto e virgula de separação e virgula de centavos. De empenhos a pagar")
    uploaded_file = st.file_uploader("Carregue a planilha (Excel ou CSV)", type=["xlsx", "xls", "csv"])

    if uploaded_file and st.button("Processar e Salvar"):
        df_result, erro = data_processor.organize_sheet(uploaded_file)

        if erro:
            st.error(erro)
        else:
            ws = conectar_sheets()
            
            # --- Lógica de Merge Inteligente com Exclusão de Zerados ---
            try:
                # 1. Carregar dados existentes
                existing_data = get_worksheet_data(ws)
                df_existing = pd.DataFrame(existing_data)
                
                # Identificar colunas chaves no novo arquivo
                col_emp_new = next((c for c in df_result.columns if "empenho" in c.lower()), None)
                col_saldo_new = next((c for c in df_result.columns if any(x in c.lower() for x in ["saldo", "valor", "pagar"])), None)
                
                if not col_emp_new or not col_saldo_new:
                    st.error("Erro: Não foi possível identificar as colunas 'Empenho' ou 'Saldo' no arquivo enviado.")
                else:
                    # Função robusta para identificar valores zerados
                    def is_zero_value(val):
                        if pd.isna(val):
                            return True
                        if isinstance(val, (int, float)):
                            return abs(val) < 0.01
                        val_str = str(val).strip().replace("R$", "").replace(" ", "")
                        if not val_str or val_str == "0" or val_str == "0,00" or val_str == "0.00" or val_str == "":
                            return True
                        try:
                            if "," in val_str and "." in val_str:
                                val_str = val_str.replace(".", "").replace(",", ".")
                            elif "," in val_str:
                                val_str = val_str.replace(",", ".")
                            return abs(float(val_str)) < 0.01
                        except:
                            return False

                    # Separar empenhos ativos e empenhos zerados do novo upload
                    mask_zero = df_result[col_saldo_new].apply(is_zero_value)
                    df_result_active = df_result[~mask_zero].copy()
                    df_result_zero = df_result[mask_zero].copy()
                    
                    # Guardar códigos de empenhos zerados do upload para excluir da planilha
                    empenhos_a_excluir = set(normalize_empenho(emp) for emp in df_result_zero[col_emp_new].tolist())
                    
                    # PREVENÇÃO CRÍTICA DE ERROS JSON (NaN, NaT, Infinity)
                    df_result_active.columns = [str(c) if pd.notna(c) else f"Coluna_Sem_Nome_{i}" for i, c in enumerate(df_result_active.columns)]
                    df_result_active = df_result_active.fillna("")
                    import numpy as np
                    df_result_active = df_result_active.replace([np.inf, -np.inf], "")

                    if df_existing.empty:
                        # Se vazio, apenas salva os ativos (que não estão zerados)
                        ws.update([df_result_active.columns.values.tolist()] + df_result_active.values.tolist())
                        st.success("Planilha salva no Google Sheets com sucesso! (Base estava vazia, registros zerados foram descartados)")
                        df_final = df_result_active
                    else:
                        # 2. Identificar coluna de Empenho, Observação e Saldo na base existente
                        col_emp_exist = next((c for c in df_existing.columns if "empenho" in c.lower()), None)
                        col_obs_exist = next((c for c in df_existing.columns if "observação" in c.lower() or "observacao" in c.lower()), None)
                        col_saldo_exist = next((c for c in df_existing.columns if any(x in c.lower() for x in ["saldo", "valor", "pagar"])), None)
                        col_obs_new = "Observação" # data_processor garante essa coluna

                        if not col_emp_exist:
                            st.error("Erro: Não foi possível identificar a coluna 'Empenho' na planilha do Google Sheets.")
                        else:
                            # 3. Converter base existente para dicionário
                            existing_dict = {normalize_empenho(row[col_emp_exist]): row for _, row in df_existing.iterrows()}
                            
                            # Lista final combinada
                            final_rows = []
                            processed_empenhos = set()

                            # 4. Iterar sobre o df de ativos
                            for _, row_new in df_result_active.iterrows():
                                emp_val = normalize_empenho(row_new[col_emp_new])
                                processed_empenhos.add(emp_val)
                                
                                if emp_val in existing_dict:
                                    # JÁ EXISTE E ATIVO: Atualiza dados, mas PRESERVA observação antiga e anexo
                                    row_merged = row_new.to_dict()
                                    old_obs = existing_dict[emp_val].get(col_obs_exist, "")
                                    if old_obs:
                                        row_merged[col_obs_new] = old_obs
                                    
                                    col_anexo_exist = next((c for c in df_existing.columns if "anexo" in c.lower()), None)
                                    col_anexo_new = "Anexo"
                                    if col_anexo_exist:
                                        old_anexo = existing_dict[emp_val].get(col_anexo_exist, "")
                                        if old_anexo:
                                            row_merged[col_anexo_new] = old_anexo
                                    final_rows.append(row_merged)
                                else:
                                    # NOVO E ATIVO: Adiciona como está
                                    final_rows.append(row_new.to_dict())
                            
                            # 5. E os que estavam na planilha antiga mas NÃO no upload?
                            # Preservamos contanto que:
                            # - Não tenham sido atualizados por um ativo (processed_empenhos)
                            # - Não estejam nos empenhos zerados do novo upload (empenhos_a_excluir)
                            # - E não tenham saldo zerado na planilha antiga
                            for emp_val, row_old in existing_dict.items():
                                emp_val_clean = normalize_empenho(emp_val)
                                if emp_val_clean not in processed_empenhos and emp_val_clean not in empenhos_a_excluir:
                                    # Se a coluna de saldo existir na base antiga, remove se estiver zerado
                                    if col_saldo_exist:
                                        saldo_old = row_old.get(col_saldo_exist, "")
                                        if is_zero_value(saldo_old):
                                            continue  # Ignora/exclui
                                    final_rows.append(row_old)

                            # 6. Salvar de volta
                            df_final = pd.DataFrame(final_rows)
                            df_final = df_final.fillna("")
                            df_final = df_final.replace([np.inf, -np.inf], "")
                            
                            # Ajustar colunas
                            cols_order = df_result_active.columns.tolist()
                            for c in df_final.columns:
                                if c not in cols_order:
                                    cols_order.append(c)
                            df_final = df_final[cols_order]

                            # Debug e salvar no Google Sheets
                            st.info(f"📤 Salvando no Google Sheets: {len(df_final)} registros, {len(df_final.columns)} colunas")
                            
                            with st.expander("🔍 Debug: Valores antes de salvar no Google Sheets"):
                                for col in df_final.columns:
                                    if any(palavra in col.lower() for palavra in ['saldo', 'valor', 'pagar']):
                                        st.write(f"**{col}** (primeiros 3 valores):")
                                        st.write(df_final[col].head(3).tolist())
                                        st.write(f"Tipo de dados: {df_final[col].dtype}")

                            ws.clear()
                            ws.update([df_final.columns.values.tolist()] + df_final.values.tolist())
                            st.cache_data.clear() # Limpar o cache para refletir a nova planilha no acompanhamento
                            st.success(f"Planilha atualizada com sucesso! Observações preservadas e empenhos zerados foram excluídos.")
            except Exception as e:
                st.error(f"Erro ao processar atualização inteligente: {e}")
            
            # --- Fim Lógica Merge ---
            
            # Converter para Excel (usando o df_result ou df_final? O usuário baixa o que acabou de processar ou o consolidado?)
            # Geralmente quer baixar o que resultou do processamento. Vamos baixar o df_final consolidado se existir, senão o result.
            df_to_download = df_final if 'df_final' in locals() else df_result
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_to_download.to_excel(writer, index=False, sheet_name='Organizada')
                
                # Ajuste simples de largura
                worksheet = writer.sheets['Organizada']
                for i, col in enumerate(df_result.columns):
                    # Tenta estimar largura
                    width = max(len(str(col)) + 5, 15)
                    worksheet.set_column(i, i, width)
                    
            output.seek(0)
            
            st.download_button(
                label="⬇️ Baixar Planilha Organizada",
                data=output,
                file_name="planilha_organizada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if modo == "Gerenciar Usuários" and st.session_state.perfil == "Administrador":
    st.title("👤 Cadastro de Usuários")
    st.markdown("Crie novos usuários para o sistema.")
    
    with st.form("form_cadastro"):
        new_user = st.text_input("Usuário")
        new_pass = st.text_input("Senha", type="password")
        # Perfil fixo como Usuário (Admin só cria via planilha se quiser mudar depois)
        new_perfil = st.selectbox("Perfil", ["Usuário", "Administrador"]) 
        
        # Carregar departamentos do data_processor
        lista_deptos = sorted(list(data_processor.DEPARTAMENTOS.values()))
        new_deptos = st.multiselect("Departamentos", lista_deptos, placeholder="Selecione um ou mais departamentos")
        
        submitted = st.form_submit_button("Cadastrar")
        
        if submitted:
            if new_user and new_pass and new_deptos:
                depto_string = "; ".join(new_deptos)
                ok, msg = auth_manager.cadastrar_usuario(new_user.strip(), new_pass, new_perfil, depto_string)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Preencha todos os campos. Selecione ao menos um departamento.")
                
    st.divider()
    st.markdown("### 🔄 Redefinir Senha de Usuário")
    st.markdown("Força a redefinição de um usuário para a senha provisória padronizada `12345678` e o obriga a trocar no próximo login.")
    
    # Carregar usuários para o selectbox
    lista_usuarios = auth_manager.get_all_users()
    
    with st.form("form_reset"):
        if not lista_usuarios:
            st.warning("Nenhum usuário encontrado na planilha.")
            reset_user = None
            submitted_reset = st.form_submit_button("Resetar Senha para '12345678'", type="primary", disabled=True)
        else:
            opcoes_usuarios = []
            for u in lista_usuarios:
                # Buscamos as chaves independentemente de case ou espaços extras
                nome = ""
                perfil_user = ""
                for k, v in u.items():
                    if "usuario" in k.lower() or "usuário" in k.lower():
                        nome = str(v).strip()
                    elif "perfil" in k.lower():
                        perfil_user = str(v).strip()
                
                if nome:
                    opcoes_usuarios.append(f"{nome} ({perfil_user})")

            if not opcoes_usuarios:
                st.warning("As colunas 'Usuario' e 'Perfil' não foram encontradas na planilha.")
            
            usuario_selecionado = st.selectbox("Selecione o Usuário a redefinir", opcoes_usuarios)
            
            # Extrair apenas o nome do usuário antes do " ("
            reset_user = usuario_selecionado.split(" (")[0] if usuario_selecionado else None
            
            submitted_reset = st.form_submit_button("Resetar Senha para '12345678'", type="primary")

        if submitted_reset:
            if reset_user:
                ok, msg = auth_manager.redefinir_senha_admin(reset_user.strip())
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Selecione um usuário para ser redefinido.")
if modo == "Configurações" and st.session_state.perfil == "Administrador":
    st.title("⚙️ Configurações do Sistema")
    st.markdown("Gerencie as configurações globais de integração.")
    
    # Obter o ID da pasta padrão pré-configurado ou o ID enviado pelo usuário
    pasta_atual = auth_manager.obter_configuracao("DRIVE_FOLDER_ID", "1qLk6PQXHtr987d6csDrQD5U2YmE74zp3")
    
    with st.form("form_configuracoes"):
        drive_folder_id = st.text_input("ID da Pasta do Google Drive (para Anexos)", value=pasta_atual, placeholder="Cole o ID da pasta do Google Drive")
        st.caption("ℹ️ O ID da pasta do Drive é o código que aparece no final da URL ao abrir a pasta no navegador (ex: 1qLk6PQXHtr987d6csDrQD5U2YmE74zp3)")
        
        submitted_config = st.form_submit_button("Salvar Configurações")
        
        if submitted_config:
            # Limpar espaços e possíveis parâmetros de query (?hl=...)
            clean_id = drive_folder_id.split('?')[0].strip() if drive_folder_id else ""
            if clean_id:
                if auth_manager.salvar_configuracao("DRIVE_FOLDER_ID", clean_id):
                    st.success("Configurações salvas com sucesso no Google Sheets!")
                else:
                    st.error("Erro ao salvar configurações no Google Sheets.")
            else:
                st.warning("O ID da pasta do Drive não pode ser vazio.")
                
    st.stop()


# ===============================
# VISUALIZAÇÃO DE EMPENHOS
# ===============================
if st.session_state.usuario: # Só mostra se estiver logado
    st.divider()
    st.markdown("## 📋 Acompanhamento de Empenhos")

    # Separar os departamentos do usuário (suporta múltiplos separados por ponto e vírgula ou vírgula)
    deptos_usuario_raw = st.session_state.departamento or ""
    deptos_usuario = [d.strip() for d in deptos_usuario_raw.replace(",", ";").split(";") if d.strip()]
    
    if st.session_state.perfil == "Administrador":
        # Admin pode escolher qualquer departamento
        opcoes_depto = ["Todos"] + list(data_processor.DEPARTAMENTOS.values())
        departamento_selecionado = st.selectbox("Filtrar por Departamento", opcoes_depto)
    else:
        # Usuário comum
        if len(deptos_usuario) > 1:
            opcoes_depto = ["Todos os meus Deptos"] + deptos_usuario
            departamento_selecionado = st.selectbox("Filtrar por Departamento", opcoes_depto)
        else:
            departamento_selecionado = deptos_usuario[0] if deptos_usuario else ""
            st.info(f"Visualizando empenhos para: **{departamento_selecionado}**")

    # Carregar e filtrar dados
    df = carregar_empenhos()
    
    # ---------------------------
    # FILTROS AVANÇADOS (SIDEBAR)
    # ---------------------------
    st.sidebar.divider()
    
    # Botão para recarregar dados limpando cache
    if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.sidebar.markdown("### 🔍 Filtros")
    
    filtro_empenho = st.sidebar.text_input("Empenho", placeholder="Ex: 1234")
    filtro_fornecedor = st.sidebar.text_input("Fornecedor", placeholder="Nome ou Trecho")
    
    # Filtro de Data (Emissão)
    # Tenta achar colunas de data
    col_emissao_filter = next((c for c in df.columns if any(x in c.lower() for x in ["emissao", "emissão", "data"])), None)
    filter_data_inicio, filter_data_fim = None, None
    
    if col_emissao_filter:
        col1, col2 = st.sidebar.columns(2)
        filter_data_inicio = col1.date_input("De", value=None)
        filter_data_fim = col2.date_input("Até", value=None)

    # ---------------------------
    # APLICAÇÃO DOS FILTROS
    # ---------------------------
    
    # 1. Filtro de Departamento
    if "Departamento (De/Para)" in df.columns:
        if st.session_state.perfil == "Administrador":
            if departamento_selecionado != "Todos":
                df = df[df["Departamento (De/Para)"] == departamento_selecionado]
        else:
            # Usuário comum
            if departamento_selecionado == "Todos os meus Deptos":
                df = df[df["Departamento (De/Para)"].isin(deptos_usuario)]
            elif departamento_selecionado != "":
                df = df[df["Departamento (De/Para)"] == departamento_selecionado]
    else:
        st.warning("⚠️ A coluna 'Departamento (De/Para)' não foi encontrada. Faça upload da planilha pelo 'Organizador de Planilhas' primeiro.")

    # Detectar colunas para evitar KeyError (necessário antes de filtrar por elas)
    col_emissao = next((c for c in df.columns if any(x in c.lower() for x in ["emissao", "emissão", "data"])), None)
    col_empenho = next((c for c in df.columns if "empenho" in c.lower()), None)
    col_cod_forn = next((c for c in df.columns if any(x in c.lower() for x in ["código", "codigo", "cod."])), None)
    col_fornecedor = next((c for c in df.columns if any(x in c.lower() for x in ["nome", "razão", "fornecedor", "credor"]) and "código" not in c.lower() and "cod" not in c.lower()), None)
    col_historico = next((c for c in df.columns if any(x in c.lower() for x in ["historico", "histórico", "descrição"])), None)
    
    # Evita que col_saldo coincida com 'valorEmpenho' (excluindo 'valor' da busca se 'saldo' ou 'pagar' estiver presente)
    col_saldo = next((c for c in df.columns if any(x in c.lower() for x in ["saldo", "pagar"])), None)
    if not col_saldo:
        col_saldo = next((c for c in df.columns if "valor" in c.lower() and "empenho" not in c.lower()), None)
        
    col_valor = next((c for c in df.columns if "valor" in c.lower() and "empenho" in c.lower()), None)
    col_status = next((c for c in df.columns if "status" in c.lower()), None)
    col_obs = next((c for c in df.columns if "observação" in c.lower() or "observacao" in c.lower()), None)
    col_anexo = next((c for c in df.columns if "anexo" in c.lower()), None)



    # fallback se não achar específico
    if not col_fornecedor: 
        col_fornecedor = next((c for c in df.columns if "fornecedor" in c.lower()), None)

    cols_found = [col_empenho, col_status] # Mínimo vital
    if not all(cols_found):
        st.error(f"Erro: Colunas principais não encontradas. Cabeçalhos disponíveis: {list(df.columns)}")
        st.stop()

    # 2. Filtro de Empenho
    if filtro_empenho:
        df = df[df[col_empenho].astype(str).str.contains(filtro_empenho, case=False, na=False)]
        
    # 3. Filtro de Fornecedor
    if filtro_fornecedor and col_fornecedor:
        df = df[df[col_fornecedor].astype(str).str.contains(filtro_fornecedor, case=False, na=False)]
        
    # 4. Filtro de Data
    if col_emissao and (filter_data_inicio or filter_data_fim):
        # Converter para datetime se não for
        try:
             # Assume formato DD/MM/YYYY do GSheets/Excel ou tenta parsear
            df["temp_data"] = pd.to_datetime(df[col_emissao], dayfirst=True, errors='coerce')
            
            if filter_data_inicio:
                df = df[df["temp_data"].dt.date >= filter_data_inicio]
            if filter_data_fim:
                df = df[df["temp_data"].dt.date <= filter_data_fim]
                
            # Limpar coluna temp
            df = df.drop(columns=["temp_data"])
        except Exception as e:
            st.sidebar.warning(f"Não foi possível filtrar por data: {e}")

    # ---------------------------
    # ORDENAÇÃO POR PRIORIDADE
    # ---------------------------
    
    # Criar coluna auxiliar para ordenação por prioridade
    def get_priority(status):
        """Retorna prioridade numérica para ordenação (menor = mais urgente)"""
        if pd.isna(status) or status == "":
            return 999
        status_str = str(status).lower()
        if "vencido" in status_str:
            return 1  # Mais urgente
        elif "vence em" in status_str:
            # Extrair número de dias
            try:
                dias = int(''.join(filter(str.isdigit, status_str)))
                return 10 + dias  # 10-15 para "vence em 0-5 dias"
            except:
                return 20
        elif "em execução" in status_str:
            return 50  # Prioridade intermediária para em execução
        elif "no prazo" in status_str:
            return 100  # Menos urgente
        else:
            return 200
    
    df["_prioridade"] = df[col_status].apply(get_priority) if col_status else 999
    
    # Ordenar: primeiro por prioridade, depois por número de empenho
    if col_empenho and "_prioridade" in df.columns:
        df = df.sort_values(["_prioridade", col_empenho], ascending=[True, True])
        df = df.drop(columns=["_prioridade"])  # Remover coluna auxiliar
    
    # ---------------------------
    # DASHBOARD DE RESUMO
    # ---------------------------
    
    st.markdown("### 📊 Resumo Geral")
    
    # Calcular estatísticas
    total_empenhos = len(df)
    
    vencidos = df[df[col_status].str.contains("Vencido", case=False, na=False)] if col_status else pd.DataFrame()
    a_vencer = df[df[col_status].str.contains("Vence em|Em execução", case=False, na=False)] if col_status else pd.DataFrame()
    no_prazo = df[df[col_status].str.contains("No Prazo", case=False, na=False)] if col_status else pd.DataFrame()
    
    qtd_vencidos = len(vencidos)
    qtd_a_vencer = len(a_vencer)
    qtd_no_prazo = len(no_prazo)
    
    # Calcular valores totais (se houver coluna de saldo)
    if col_saldo:
        def extract_value(val):
            """Extrai valor numérico de string formatada ou número"""
            if pd.isna(val):
                return 0
            if isinstance(val, (int, float)):
                return float(val)
            # Se é string, tentar converter
            try:
                val_str = str(val).replace("R$", "").replace(".", "").replace(",", ".").strip()
                return float(val_str)
            except:
                return 0
        
        valor_vencidos = vencidos[col_saldo].apply(extract_value).sum() if len(vencidos) > 0 else 0
        valor_a_vencer = a_vencer[col_saldo].apply(extract_value).sum() if len(a_vencer) > 0 else 0
        valor_no_prazo = no_prazo[col_saldo].apply(extract_value).sum() if len(no_prazo) > 0 else 0
    else:
        valor_vencidos = valor_a_vencer = valor_no_prazo = 0
    
    # Exibir cards de resumo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Empenhos", total_empenhos, delta="R$ 0,00", delta_color="off")
        if st.button("📋 Ver Todos", key="btn_todos", use_container_width=True):
            st.session_state["filtro_status"] = "Todos"
            st.rerun()
    
    with col2:
        st.metric("🔴 Vencidos", qtd_vencidos, 
                  delta=f"R$ {valor_vencidos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                  delta_color="inverse" if valor_vencidos > 0 else "off")
        if st.button("🔍 Filtrar", key="btn_vencidos", use_container_width=True, disabled=qtd_vencidos == 0):
            st.session_state["filtro_status"] = "Vencido"
            st.rerun()
    
    with col3:
        st.metric("⚠️ Em Execução / A Vencer", qtd_a_vencer,
                  delta=f"R$ {valor_a_vencer:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                  delta_color="off")
        if st.button("🔍 Filtrar", key="btn_a_vencer", use_container_width=True, disabled=qtd_a_vencer == 0):
            st.session_state["filtro_status"] = "Vence em|Em execução"
            st.rerun()
    
    with col4:
        st.metric("✅ No Prazo", qtd_no_prazo,
                  delta=f"R$ {valor_no_prazo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                  delta_color="normal" if valor_no_prazo > 0 else "off")
        if st.button("🔍 Filtrar", key="btn_no_prazo", use_container_width=True, disabled=qtd_no_prazo == 0):
            st.session_state["filtro_status"] = "No Prazo"
            st.rerun()
    
    # Aplicar filtro de status se houver
    if "filtro_status" in st.session_state and st.session_state["filtro_status"] != "Todos":
        filtro = st.session_state["filtro_status"]
        if col_status:
            df_original_count = len(df)
            df = df[df[col_status].str.contains(filtro, case=False, na=False)]
            st.info(f"🔍 Filtrando por: **{filtro}** ({len(df)} de {df_original_count} registros)")
    
    # ---------------------------
    # ALERTAS DE PRAZO
    # ---------------------------
    
    if qtd_vencidos > 0 or qtd_a_vencer > 0:
        st.markdown("---")
        if qtd_vencidos > 0 and qtd_a_vencer > 0:
            st.error(f"⚠️ **ATENÇÃO:** {qtd_vencidos} empenho(s) vencido(s) e {qtd_a_vencer} vencendo em até 5 dias!")
        elif qtd_vencidos > 0:
            st.error(f"🔴 **ATENÇÃO:** {qtd_vencidos} empenho(s) vencido(s)!")
        else:
            st.warning(f"⚠️ **ATENÇÃO:** {qtd_a_vencer} empenho(s) vencendo em até 5 dias!")
    
    st.markdown("---")
    
    # ---------------------------
    # EXPORTAÇÃO PARA EXCEL
    # ---------------------------
    
    # Botão de exportação
    col_export1, col_export2 = st.columns([3, 1])
    
    with col_export2:
        if st.button("📥 Exportar para Excel", use_container_width=True):
            # Preparar dados para exportação
            df_export = df.copy()
            
            # Formatar valores monetários para Excel
            if col_saldo:
                df_export[col_saldo] = df_export[col_saldo].apply(extract_value)
            
            # Criar arquivo Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Empenhos')
            
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="⬇️ Baixar Arquivo",
                data=output,
                file_name=f"empenhos_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    st.markdown("---")
    
    # ---------------------------
    # TABELA COM DESTAQUE VISUAL
    # ---------------------------
    
    st.markdown("### 📋 Lista de Empenhos")
    
    # PAGINAÇÃO
    total_items = len(df)
    items_per_page = 50
    total_pages = max(1, (total_items // items_per_page) + (1 if total_items % items_per_page > 0 else 0))
    
    st.caption(f"Total de registros encontrados: {total_items}")
    
    if total_pages > 1:
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        df_display = df.iloc[start_idx:end_idx]
    else:
        df_display = df

    if df_display.empty:
        st.warning("Nenhum empenho encontrado com os filtros selecionados.")
        st.stop()
    else:
        # Cabeçalho da Tabela
        st.markdown("---")
        # Layout: Emissao(1.0), Empenho(0.7), Cod(0.7), Nome(1.6), Hist(2.5), Valor(0.9), Saldo(0.9), Prazo(0.9), Status(0.9)
        cols_spec = [1.0, 0.7, 0.7, 1.6, 2.5, 0.9, 0.9, 0.9, 0.9]
        cols = st.columns(cols_spec)
        
        cols[0].markdown("**Emissão**")
        cols[1].markdown("**Emp.**")
        cols[2].markdown("**Cód.**")
        cols[3].markdown("**Fornecedor**")
        cols[4].markdown("**Histórico**")
        cols[5].markdown("**Valor**")
        cols[6].markdown("**Saldo a Pagar**")
        cols[7].markdown("**Prazo**")
        cols[8].markdown("**Status**")
        
        st.markdown("---")

        with st.container(height=600):
            for _, row in df_display.iterrows():
                empenho_val = row[col_empenho]
                
                cols = st.columns(cols_spec)
                
                # 1. Data Emissão
                cols[0].caption(str(row.get(col_emissao, "-")))
                
                # 2. Empenho
                cols[1].write(f"{empenho_val}")
                
                # 3. Código Fornecedor
                cols[2].caption(str(row.get(col_cod_forn, "-")))
                
                # 4. Nome Fornecedor
                cols[3].caption(str(row.get(col_fornecedor, "-")))
                
                # 5. Histórico (Scrollable)
                hist_text = str(row.get(col_historico, "-"))
                cols[4].markdown(
                    f"""<div style="height: 50px; overflow-y: auto; font-size: 12px; background-color: rgba(255, 255, 255, 0.05); padding: 5px; border-radius: 4px;">{hist_text}</div>""",
                    unsafe_allow_html=True
                )
                
                # 6. Valor Original (Formatado)
                valor_raw = row.get(col_valor, "-") if col_valor else "-"
                cols[5].caption(format_currency(valor_raw))
                
                # 7. Saldo (Formatado)
                saldo_raw = row.get(col_saldo, "-")
                cols[6].caption(format_currency(saldo_raw))
    
                # 8. Prazo
                cols[7].caption(str(row.get("Prazo (90 dias)", "-")))
    
                # 9. Status
                status_val = row[col_status]
                if status_val == "Vencido":
                    cols[8].error(status_val)
                elif "Vence em" in str(status_val) or status_val == "Em execução":
                    cols[8].warning(status_val)
                else:
                    cols[8].success(status_val)
                    
                # Linha de baixo: Pedido de Compra, Observação e Anexo
                col_sub1, col_sub2, col_sub3 = st.columns([2.5, 6.0, 2.5])
                
                pedido_compra = row.get("Pedido de Compra", "")
                if pedido_compra and str(pedido_compra).strip() != "" and str(pedido_compra).strip().lower() != "nan":
                    col_sub1.markdown(f"📦 **Pedido de Compra:** {pedido_compra}")
                else:
                    col_sub1.markdown("")
                    
                obs_key = f"obs_{empenho_val}_ext"
                obs_val = row.get(col_obs, "") if col_obs else ""
                
                # Input de texto para observação com placeholder explicativo
                col_sub2.text_input(
                    "Observação",
                    value=obs_val,
                    key=obs_key,
                    label_visibility="collapsed",
                    placeholder="Clique aqui para digitar uma observação sobre este empenho...",
                    on_change=lambda k=obs_key, e=empenho_val: salvar_observacao(e, k),
                )
                
                # Lógica do Anexo (Upload / Visualização)
                anexo_val = row.get(col_anexo, "") if col_anexo else ""
                
                if anexo_val and str(anexo_val).strip() != "" and str(anexo_val).strip().lower() != "nan":
                    c_link, c_del = col_sub3.columns([4, 1])
                    c_link.link_button("📄 Ver Anexo", str(anexo_val), use_container_width=True)
                    if c_del.button("❌", key=f"del_anexo_{empenho_val}", help="Remover Anexo"):
                        deletar_anexo_process(empenho_val, anexo_val)
                else:
                    upload_key = f"upload_{empenho_val}"
                    uploaded_file = col_sub3.file_uploader(
                        "Anexar Nota/PDF",
                        type=["pdf", "png", "jpg", "jpeg"],
                        key=upload_key,
                        label_visibility="collapsed",
                    )
                    col_sub3.markdown("<div style='font-size: 11px; opacity: 0.7; text-align: center; margin-top: -6px;'>Lembrete: notas, memorando</div>", unsafe_allow_html=True)
                    if uploaded_file:
                        salvar_anexo_process(empenho_val, uploaded_file)
                
                st.divider()
    
    st.stop() # Interrompe aqui para não carregar o resto do app

st.title("🏛️ Gerador de Projetos, Leis e Decretos")
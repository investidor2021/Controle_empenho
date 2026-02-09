import streamlit as st
import pandas as pd
import uuid
import io
import gspread
from google.oauth2.service_account import Credentials
import data_processor


import auth_manager
import time


# Move page config to top (done in previous chunk)
st.set_page_config(layout="wide")

if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "perfil" not in st.session_state:
    st.session_state.perfil = None
if "departamento" not in st.session_state:
    st.session_state.departamento = None

# ===============================
# SIDEBAR LOGIN / CADASTRO
# ===============================
st.sidebar.title("Acesso ao Sistema")

if not st.session_state.usuario:
    st.sidebar.title("Login")
    login_user = st.sidebar.text_input("Usuário")
    login_pass = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        sucesso, perfil, depto = auth_manager.verificar_login(login_user.strip(), login_pass)
        if sucesso:
            st.session_state.usuario = login_user
            st.session_state.perfil = perfil
            st.session_state.departamento = depto
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


@st.cache_data(ttl=60) # Cache por 60 segundos para evitar recarregar toda hora
def carregar_empenhos():
    ws = conectar_sheets()
    if ws is None:
        st.error("Erro ao conectar com o Google Sheets")
        return pd.DataFrame()
    
    try:
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        
        # Debug: mostrar informações sobre os dados carregados
        if df.empty:
            st.warning(f"⚠️ A planilha do Google Sheets está vazia. Total de linhas: {len(ws.get_all_values())}")
        else:
            st.info(f"✅ Dados carregados: {len(df)} registros, {len(df.columns)} colunas")
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()




def format_currency(val):
    try:
        if isinstance(val, (int, float)):
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Handle string values with Brazilian format
        val_str = str(val).replace("R$", "").strip()
        
        # If it contains comma, assume Brazilian format (1.234,56)
        if "," in val_str:
            # Remove thousand separators (dots) and replace comma with dot
            val_str = val_str.replace(".", "").replace(",", ".")
        
        val_float = float(val_str)
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)


    
def salvar_observacao(empenho, key):
    novo_texto = st.session_state[key]
    ws = conectar_sheets()
    registros = ws.get_all_records()

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
        st.error("Erro ao salvar: colunas não identificadas na planilha.")
        return

    # Iterar manualmente e atualizar (gspread update_cell usa índice 1-based)
    # Linha 1 é cabeçalho, dados começam na 2.
    for i, r in enumerate(registros, start=2):
        if str(r[cabecalho[col_empenho_idx]]) == str(empenho):
            ws.update_cell(i, col_obs_idx + 1, novo_texto)
            break    


# ===============================
# NAVEGAÇÃO
# ===============================
if st.session_state.perfil == "Administrador":
    modo = st.sidebar.radio("Ferramenta", ["Gerador de Documentos", "Organizador de Planilhas", "Gerenciar Usuários"])
else:
    modo = "Gerador de Documentos" # Usuário padrão só vê isso

if modo == "Organizador de Planilhas":
    st.title("📂 Organizador de Planilhas")
    st.markdown("Extrai colunas (D, F, H, J, K, W, AJ), mapeia departamentos e verifica prazos.")
    
    uploaded_file = st.file_uploader("Carregue a planilha (Excel ou CSV)", type=["xlsx", "xls", "csv"])

    if uploaded_file and st.button("Processar e Salvar"):
        df_result, erro = data_processor.organize_sheet(uploaded_file)

        if erro:
            st.error(erro)
        else:
            ws = conectar_sheets()
            
            # --- Lógica de Merge Inteligente ---
            try:
                # 1. Carregar dados existentes
                existing_data = ws.get_all_records()
                df_existing = pd.DataFrame(existing_data)
                
                if df_existing.empty:
                    # Se vazio, apenas sobrescreve
                    ws.update([df_result.columns.values.tolist()] + df_result.values.tolist())
                    st.success("Planilha salva no Google Sheets com sucesso! (Base estava vazia)")
                else:
                    # 2. Identificar coluna de Empenho e Observação na base existente
                    col_emp_exist = next((c for c in df_existing.columns if "empenho" in c.lower()), None)
                    col_obs_exist = next((c for c in df_existing.columns if "observação" in c.lower() or "observacao" in c.lower()), None)
                    
                    # Identificar coluna de Empenho no novo upload (df_result)
                    col_emp_new = next((c for c in df_result.columns if "empenho" in c.lower()), None)
                    col_obs_new = "Observação" # data_processor garante essa coluna

                    if not col_emp_exist or not col_emp_new:
                        st.error("Erro: Não foi possível identificar a coluna 'Empenho' para fazer a mesclagem.")
                    else:
                        # 3. Converter para dicionários para fácil acesso
                        # Chave: Empenho, Valor: Linha completa
                        existing_dict = {str(row[col_emp_exist]): row for _, row in df_existing.iterrows()}
                        
                        # Lista final combinada
                        final_rows = []
                        
                        # Conjunto para rastrear quais empenhos já processamos do arquivo novo
                        processed_empenhos = set()

                        # 4. Iterar sobre o NOVO df
                        for _, row_new in df_result.iterrows():
                            emp_val = str(row_new[col_emp_new])
                            processed_empenhos.add(emp_val)
                            
                            if emp_val in existing_dict:
                                # JÁ EXISTE: Atualiza dados, mas PRESERVA observação antiga
                                row_merged = row_new.to_dict()
                                
                                # Tenta pegar observação antiga
                                old_obs = existing_dict[emp_val].get(col_obs_exist, "")
                                if old_obs:
                                    row_merged[col_obs_new] = old_obs
                                    
                                final_rows.append(row_merged)
                            else:
                                # NOVO: Adiciona como está
                                final_rows.append(row_new.to_dict())
                        
                        # 5. E os que estavam na planilha antiga mas NÃO no upload?
                        # O usuário não especificou remover. Por segurança no "acompanhamento", MANTÉM.
                        for emp_val, row_old in existing_dict.items():
                            if emp_val not in processed_empenhos:
                                final_rows.append(row_old)

                        # 6. Salvar de volta
                        df_final = pd.DataFrame(final_rows)
                        
                        # Garantir que as colunas chaves estejam presentes e na ordem preferida (opcional, mas bom manter padrão)
                        # Vamos usar as colunas do df_result como base para a ordem, adicionando extras se houver
                        cols_order = df_result.columns.tolist()
                        for c in df_final.columns:
                            if c not in cols_order:
                                cols_order.append(c)
                                
                        df_final = df_final[cols_order]

                        # Debug: mostrar o que será salvo
                        st.info(f"📤 Salvando no Google Sheets: {len(df_final)} registros, {len(df_final.columns)} colunas")
                        st.write("Colunas:", list(df_final.columns))

                        ws.clear()
                        ws.update([df_final.columns.values.tolist()] + df_final.values.tolist())
                        st.success(f"Planilha atualizada com sucesso! {len(df_result)} registros processados. Observações preservadas.")

            except Exception as e:
                st.error(f"Erro ao processar atualização inteligente: {e}")
                # Fallback: pergunta se quer sobrescrever? Melhor não arriscar dados.
            
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
        new_depto = st.selectbox("Departamento", lista_deptos)
        
        submitted = st.form_submit_button("Cadastrar")
        
        if submitted:
            if new_user and new_pass:
                ok, msg = auth_manager.cadastrar_usuario(new_user.strip(), new_pass, new_perfil, new_depto)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Preencha todos os campos.")
                    
                    
# ===============================
# VISUALIZAÇÃO DE EMPENHOS
# ===============================
if st.session_state.usuario: # Só mostra se estiver logado
    st.divider()
    st.markdown("## 📋 Acompanhamento de Empenhos")

    if st.session_state.perfil == "Administrador":
        # Admin pode escolher qualquer departamento
        opcoes_depto = ["Todos"] + list(data_processor.DEPARTAMENTOS.values())
        departamento_selecionado = st.selectbox("Filtrar por Departamento", opcoes_depto)
    else:
        # Usuário vê apenas o seu
        departamento_selecionado = st.session_state.departamento
        st.info(f"Visualizando empenhos para: **{departamento_selecionado}**")

    # Carregar e filtrar dados
    df = carregar_empenhos()
    
    # ---------------------------
    # FILTROS AVANÇADOS (SIDEBAR)
    # ---------------------------
    st.sidebar.divider()
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
    
    # 1. Filtro de Departamento (Já existente)
    if departamento_selecionado != "Todos":
        df = df[df["Departamento (De/Para)"] == departamento_selecionado]

    # Detectar colunas para evitar KeyError (necessário antes de filtrar por elas)
    col_emissao = next((c for c in df.columns if any(x in c.lower() for x in ["emissao", "emissão", "data"])), None)
    col_empenho = next((c for c in df.columns if "empenho" in c.lower()), None)
    col_cod_forn = next((c for c in df.columns if any(x in c.lower() for x in ["código", "codigo", "cod."])), None)
    col_fornecedor = next((c for c in df.columns if any(x in c.lower() for x in ["nome", "razão", "fornecedor", "credor"]) and "código" not in c.lower() and "cod" not in c.lower()), None)
    col_historico = next((c for c in df.columns if any(x in c.lower() for x in ["historico", "histórico", "descrição"])), None)
    col_saldo = next((c for c in df.columns if any(x in c.lower() for x in ["saldo", "valor", "pagar"])), None)
    col_status = next((c for c in df.columns if "status" in c.lower()), None)

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
        # Layout: Emissao(1), Empenho(0.8), Cod(0.8), Nome(2), Hist(2.5), Saldo(1), Prazo(1), Status(1), Obs(1.5)
        cols_spec = [1, 0.7, 0.7, 1.5, 2.5, 0.8, 0.8, 0.8, 1.2]
        cols = st.columns(cols_spec)
        
        cols[0].markdown("**Emissão**")
        cols[1].markdown("**Emp.**")
        cols[2].markdown("**Cód.**")
        cols[3].markdown("**Fornecedor**")
        cols[4].markdown("**Histórico**")
        cols[5].markdown("**Saldo**")
        cols[6].markdown("**Prazo**")
        cols[7].markdown("**Status**")
        cols[8].markdown("**Observação**")
        
        st.markdown("---")

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
            
            # 6. Saldo (Formatado)
            saldo_raw = row.get(col_saldo, "-")
            cols[5].caption(format_currency(saldo_raw))

            # 7. Prazo
            cols[6].caption(str(row.get("Prazo (90 dias)", "-")))

            # 8. Status
            status_val = row[col_status]
            if status_val == "Vencido":
                cols[7].error(status_val)
            elif "Vence em" in str(status_val):
                cols[7].warning(status_val)
            else:
                cols[7].success(status_val)
                
            # 9. Observação
            obs_key = f"obs_{empenho_val}_ext"
            cols[8].text_input(
                "Obs",
                value=row.get("Observação", ""),
                key=obs_key,
                label_visibility="collapsed",
                on_change=lambda k=obs_key, e=empenho_val: salvar_observacao(e, k),
            )
            
            st.divider()
    
    st.stop() # Interrompe aqui para não carregar o resto do app

st.title("🏛️ Gerador de Projetos, Leis e Decretos")
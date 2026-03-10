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
        st.error("Não foi possível encontrar as colunas necessárias.")
        return
    
    # Procurar linha do empenho
    for idx, reg in enumerate(registros):
        if str(reg.get(cabecalho[col_empenho_idx])) == str(empenho):
            row_number = idx + 2  # +1 para base 1, +1 para pular cabeçalho
            # col_letter_obs = chr(65 + col_obs_idx)  # Converter índice para letra (A, B, C...) # Not used
            
            # Adicionar timestamp à observação
            timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
            texto_com_timestamp = f"{novo_texto}\n[Atualizado em: {timestamp}]" if novo_texto.strip() else ""
            
            ws.update_cell(row_number, col_obs_idx + 1, texto_com_timestamp)
            st.success(f"Observação salva para empenho {empenho}!")
            time.sleep(1)
            st.rerun()
            return
    
    st.error(f"Empenho {empenho} não encontrado.")


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
    st.markdown("O arquivo é o analitico de empenho no formato .xlsx com ponto e virgula de separação e virgula de centavos.")
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
                
                # PREVENÇÃO CRÍTICA DE ERROS JSON (NaN, NaT, Infinity)
                # Garante que as colunas são textos válidos
                df_result.columns = [str(c) if pd.notna(c) else f"Coluna_Sem_Nome_{i}" for i, c in enumerate(df_result.columns)]
                # Converte todas as variáveis nulas do Pandas para string vazia
                df_result = df_result.fillna("")
                import numpy as np
                df_result = df_result.replace([np.inf, -np.inf], "")

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
                        df_final = df_final.fillna("")
                        df_final = df_final.replace([np.inf, -np.inf], "")
                        
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
                        
                        # Debug detalhado: mostrar valores de exemplo das colunas monetárias
                        with st.expander("🔍 Debug: Valores antes de salvar no Google Sheets"):
                            # Encontrar colunas que parecem monetárias
                            for col in df_final.columns:
                                if any(palavra in col.lower() for palavra in ['saldo', 'valor', 'pagar']):
                                    st.write(f"**{col}** (primeiros 3 valores):")
                                    st.write(df_final[col].head(3).tolist())
                                    st.write(f"Tipo de dados: {df_final[col].dtype}")

                        ws.clear()
                        # Substitui valores NaN (Not a Number) e NaT (Not a Time) por string vazia para as regras do JSON
                        df_final = df_final.fillna("")
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
        # Verificar se a coluna existe antes de filtrar
        if "Departamento (De/Para)" in df.columns:
            df = df[df["Departamento (De/Para)"] == departamento_selecionado]
        else:
            st.warning("⚠️ A coluna 'Departamento (De/Para)' não foi encontrada. Faça upload da planilha pelo 'Organizador de Planilhas' primeiro.")

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
    a_vencer = df[df[col_status].str.contains("Vence em", case=False, na=False)] if col_status else pd.DataFrame()
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
        st.metric("Total de Empenhos", total_empenhos)
        if st.button("📋 Ver Todos", key="btn_todos", use_container_width=True):
            st.session_state["filtro_status"] = "Todos"
            st.rerun()
    
    with col2:
        st.metric("🔴 Vencidos", qtd_vencidos, 
                  delta=f"R$ {valor_vencidos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor_vencidos > 0 else None,
                  delta_color="inverse")
        if st.button("🔍 Filtrar", key="btn_vencidos", use_container_width=True, disabled=qtd_vencidos == 0):
            st.session_state["filtro_status"] = "Vencido"
            st.rerun()
    
    with col3:
        st.metric("⚠️ A Vencer (≤5 dias)", qtd_a_vencer,
                  delta=f"R$ {valor_a_vencer:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor_a_vencer > 0 else None,
                  delta_color="off")
        if st.button("🔍 Filtrar", key="btn_a_vencer", use_container_width=True, disabled=qtd_a_vencer == 0):
            st.session_state["filtro_status"] = "Vence em"
            st.rerun()
    
    with col4:
        st.metric("✅ No Prazo", qtd_no_prazo,
                  delta=f"R$ {valor_no_prazo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor_no_prazo > 0 else None,
                  delta_color="normal")
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
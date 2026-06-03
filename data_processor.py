import pandas as pd
from datetime import datetime, timedelta

DEPARTAMENTOS = {
    "01.02.01": "GABINETE PREFEITO DEPENDÊNCIAS",
    "01.02.02": "PROCURADORIA JURIDICA",
    "01.02.03": "DEPTO DE ADMINISTRACÃO",
    "01.02.04": "DEPTO DE ALMOXARIFADO E PATRIMONIO",
    "01.02.05": "DEPTO DE FINANÇAS",
    "01.02.06": "DEPTO DE LICITAÇÃO E COMPRAS",
    "01.02.07": "DEPTO DE CONVÊNIOS",
    "01.02.08": "DEPTO DE PLANEJAMENTO",
    "01.02.09": "DEPTO DE DESENV. ECONOM. E DO TRABALHO",
    "01.02.10": "DEPTO DE OBRAS",
    "01.02.11": "DEPTO DE SERVIÇOS URBANOS E RURAIS",
    "01.02.12": "DEPTO DA AGRICULTURA E MEIO AMBIENTE",
    "01.02.13": "DEPTO DE SEGURANÇA E TRÂNSITO",
    "01.02.14": "DEPTO DE EDUCAÇÃO - ENSINO BASICO",
    "01.02.15": "DEPTO DE EDUCAÇÃO FUNDEB MAGISTERIO",
    "01.02.16": "DEPTO DE EDUCAÇÃO FUNDEB - OTS DESPESAS",
    "01.02.17": "DEPTO DE EDUCAÇÃO - MERENDA ESCOLAR",
    "01.02.18": "DEPTO DE CULTURA E TURISMO",
    "01.02.19": "DEPTO DE ESPORTES E LAZER",
    "01.02.20": "FUNDO MUNICIPAL DE SAUDE",
    "01.02.21": "DEPTO DE AÇÃO SOCIAL",
    "01.02.22": "ENCARGOS GERAIS DO MUNICIPIO",
    "01.02.23": "DEPTO DE TECNOLOGIA DA INFORMAÇÃO E INOVAÇÃO",
    "01.02.24": "DEPTO DE ADMINISTRAÇÃO TRIBUTÁRIA",
    "01.02.99": "RESERVA DE CONTIGÊNCIA",
    "02.01.01": "CÂMARA MUNICIPAL",
    "04.04.01": "DEPARTAMENTO COMERCIAL",
    "04.04.02": "DEPARTAMENTO DE OBRAS E SERVIÇOS",
    "04.04.03": "DEPARTAMENTO DE CAPTAÇÃOO E TRATAMENTO DE AGUA",
    "04.04.04": "DEPARTAMENTO DE TRATAMENTO DE ESGOTO",
    "05.05.01": "FUNDO DE PREVIDÊNCIA DOS SERVIDORES MUNICIPAIS"
}

def get_department_name(code):
    """
    Returns the department name based on the code.
    """
    clean_code = str(code).strip()
    prefix = clean_code[:8]
    return DEPARTAMENTOS.get(prefix, f"DEP-{prefix}")

def organize_sheet(file):
    """
    Reads an Excel or CSV file, extracts specific columns, 
    adds Department mapping, and calculates deadlines.
    """
    try:
        # Load data
        if file.name.endswith('.csv'):
            # Tentativa robusta de leitura com diferentes encodings e separadores
            success = False
            for enc in ['utf-8', 'iso-8859-1', 'windows-1252']:
                for separator in [';', ',', '\t']:
                    try:
                        file.seek(0)
                        # Usa on_bad_lines='skip' se versões mais novas do pandas, mas error no antigo. Vamos focar no sep.
                        df_temp = pd.read_csv(file, dtype=str, encoding=enc, sep=separator)
                        if len(df_temp.columns) > 1:  # Se achou mais de uma coluna, o delimitador está correto
                            df = df_temp
                            success = True
                            break
                    except Exception:
                        continue
                if success:
                    break
            
            if not success:
                # Fallback final tentando auto-detect com a engine do Python
                file.seek(0)
                try:
                    df = pd.read_csv(file, dtype=str, encoding='iso-8859-1', sep=None, engine='python')
                except Exception as e:
                    return None, f"Erro crítico na leitura do CSV. Verifique se o formato está correto. Detalhe: {e}"
        else:
            # Ler Excel como strings para preservar formatação brasileira (vírgula decimal)
            df = pd.read_excel(file, dtype=str, engine='openpyxl')
        
        # Define target columns by Excel letter (0-indexed)
        # D=3, F=5, H=7, J=9, K=10, W=22, AJ=35
        # We assume the user means the columns in the source file are at these positions.
        
        # Check if file has enough columns
        max_col_idx = 35
        if df.shape[1] <= max_col_idx:
            return None, f"Erro: A planilha tem apenas {df.shape[1]} colunas, mas precisamos da coluna AJ (índice 35)."

        # Extract specific columns using iloc
        # We start with D (3)
        col_indices = [3, 5, 7, 8, 9, 10, 22, 27, 35]
        
        # Select data
        result_df = df.iloc[:, col_indices].copy()
        
        # CRÍTICO: Converter valores com vírgula decimal (formato brasileiro) para float
        # O Excel salva valores como "18500,51" ou "13412,43" (strings com vírgula decimal)
        # Precisamos converter vírgula para ponto ANTES de converter para float
        
        # Lista para debug
        debug_conversions = []
        
        def convert_brazilian_decimal(val):
            """Converte valores do formato brasileiro (vírgula) ou americano (ponto) para float"""
            if pd.isna(val):
                return val
            
            original_val = val  # Guardar para debug
            
            # Se já é número, retorna como está
            if isinstance(val, (int, float)):
                return float(val)
            
            # Se é string, tenta converter
            if isinstance(val, str):
                val_clean = val.strip()
                
                # Se tem vírgula, é formato brasileiro com vírgula como separador decimal
                if ',' in val_clean:
                    # Se tem PONTO: formato "1.234,56" (ponto=milhar, vírgula=decimal)
                    if '.' in val_clean:
                        # Remove pontos (separador de milhar) e troca vírgula por ponto
                        val_clean = val_clean.replace('.', '').replace(',', '.')
                    # Se tem APENAS VÍRGULA: formato "18500,51" (vírgula=decimal)
                    else:
                        # Apenas troca vírgula por ponto (NÃO remove nada!)
                        val_clean = val_clean.replace(',', '.')
                
                # Tenta converter para float
                try:
                    result = float(val_clean)
                    # Debug: registrar conversões de valores monetários
                    if result > 100:  # Provavelmente valor monetário
                        debug_conversions.append(f"{original_val} → {result}")
                    return result
                except ValueError:
                    return val  # Se não conseguir converter, retorna original
            
            return val
        
        # Aplicar conversão apenas nas colunas que não são identificadores, texto ou data
        for col in result_df.columns:
            col_lower = col.lower()
            
            # Pular colunas de texto/data claras
            if any(palavra in col_lower for palavra in ['data', 'prazo', 'status', 'departamento', 'observação', 'observacao', 'nome', 'histórico', 'historico', 'atividade', 'tipoempenho']):
                continue
                
            # Pular identificadores/códigos (ex: número do empenho, código do fornecedor)
            # Mas não se for valor/saldo do empenho
            if "valor" not in col_lower and "saldo" not in col_lower and any(palavra in col_lower for palavra in ['empenho', 'emp.', 'emp', 'código', 'codigo', 'cod.', 'nº', 'numero', 'número']):
                # Garantir que identificadores sejam strings limpas (ex: "164" em vez de "164.0")
                def clean_id_val(val):
                    if pd.isna(val):
                        return ""
                    val_str = str(val).strip()
                    if val_str.endswith(".0"):
                        val_str = val_str[:-2]
                    return val_str
                result_df[col] = result_df[col].apply(clean_id_val)
                continue
                
            # Aplicar conversão brasileira decimal para float
            result_df[col] = result_df[col].apply(convert_brazilian_decimal)
        
        # Mostrar conversões realizadas
        if debug_conversions:
            print("🔍 DEBUG - Conversões realizadas:")
            for conv in debug_conversions[:10]:  # Mostrar primeiras 10
                print(f"  {conv}")
        
        # Insert "De/Para" (Department) after Column D (which is now at index 0 in result_df)
        # Column D is at result_df.columns[0]
        col_d_name = result_df.columns[0]
        col_f_name = result_df.columns[1] # F is at index 1 initially
        
        # Apply mapping
        department_names = result_df[col_d_name].apply(get_department_name)
        
        # Insert "Departamento (De/Para)" at index 1 (after the Code column), keeping the code column
        result_df.insert(1, "Departamento (De/Para)", department_names)
        
        # Date Logic (Column F)
        # result_df now has: Code(0), Dept(1), F(2), H(3)...
        # So col_f_name (which we grabbed before) is still valid as a reference to the source Series name.
        
        # Convert to datetime
        result_df[col_f_name] = pd.to_datetime(result_df[col_f_name], errors='coerce')
        
        # Calculate +90 days
        result_df["Prazo (90 dias)"] = result_df[col_f_name] + timedelta(days=90)
        
        # Status Check
        today = datetime.now()
        
        col_tipo_name = result_df.columns[4]
        col_valor_name = result_df.columns[8]
        col_saldo_name = result_df.columns[9]
        
        def determine_status(row):
            def parse_to_float(val):
                if pd.isna(val) or val == "":
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                try:
                    val_str = str(val).strip().replace("R$", "").replace(" ", "")
                    if "," in val_str and "." in val_str:
                        val_str = val_str.replace(".", "").replace(",", ".")
                    elif "," in val_str:
                        val_str = val_str.replace(",", ".")
                    return float(val_str)
                except:
                    return 0.0

            saldo_val = parse_to_float(row[col_saldo_name])
            valor_val = parse_to_float(row[col_valor_name])
            
            # Se o saldo do empenho comparado com o valor do empenho original 
            # for diferente de zero e diferentes entre si, coloque em execução
            if saldo_val > 0.01 and abs(saldo_val - valor_val) > 0.01:
                return "Em execução"
            
            # Caso contrário, segue a lógica de 90 dias
            deadline = row["Prazo (90 dias)"]
            if pd.isna(deadline):
                return "Data Inválida"
            
            days_remaining = (deadline - today).days
            
            if days_remaining < 0:
                return "Vencido"
            elif days_remaining <= 5: # Warning threshold
                return f"Vence em {days_remaining} dias"
            else:
                return "No Prazo"

        result_df["Status"] = result_df.apply(determine_status, axis=1)
        
        # Formatting Date Columns for display
        result_df[col_f_name] = result_df[col_f_name].dt.strftime('%d/%m/%Y')
        result_df["Prazo (90 dias)"] = result_df["Prazo (90 dias)"].dt.strftime('%d/%m/%Y')

        # Garantir que colunas monetárias sejam números (float) para o Google Sheets
        # NÃO formatar como string aqui - deixar a formatação para a exibição no Streamlit
        for col in result_df.columns:
            col_lower = col.lower()
            
            # Pular colunas que não são monetárias
            if any(palavra in col_lower for palavra in ['data', 'prazo', 'status', 'departamento', 'observa']):
                continue
            
            # Pular colunas que são identificadores (números inteiros, não valores monetários)
            # Ex: Número do Empenho, Código do Fornecedor (mas não se for valor/saldo!)
            if "valor" not in col_lower and "saldo" not in col_lower and any(palavra in col_lower for palavra in ['empenho', 'emp.', 'emp', 'código', 'codigo', 'cod.', 'nº', 'numero', 'número']):
                continue
                
            # Verificar se é uma coluna numérica ou se contém palavras-chave que indicam valores monetários
            # Isso é necessário porque CSVs são lidos como strings (dtype 'object')
            is_monetary = any(palavra in col_lower for palavra in ['valor', 'saldo', 'pago', 'pagar', 'liquidado', 'empenhado'])
            if pd.api.types.is_numeric_dtype(result_df[col]) or is_monetary:
                try:
                    # Apenas garantir que é numérico (float) - NÃO converter para string
                    result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
                    # Arredondar para 2 casas decimais
                    result_df[col] = result_df[col].round(2)
                except Exception:
                    pass  # Se der erro, mantém o valor original


        if "Observação" not in result_df.columns:
            # Garantir coluna Observação
            result_df["Observação"] = ""
            
        return result_df, None


    except Exception as e:
        return None, f"Erro ao processar planilha: {str(e)}"



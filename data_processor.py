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
    TODO: Update this dictionary with the actual 'De/Para' rules from the user.
    """
    
    # Return the mapped name or the code formatted as "DEP-{code}" if not found.
    # User requested to use the first 8 chars (which matches the "01.02.01" pattern) to identify the department.
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
            df = pd.read_csv(file, dtype=str)  # Ler como string para não perder formatação
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
        col_indices = [3, 5, 7, 9, 10, 22, 35]
        
        # Select data
        result_df = df.iloc[:, col_indices].copy()
        
        # CRÍTICO: Converter valores com vírgula decimal (formato brasileiro) para float
        # O Excel salva valores como "18500,51" ou "13412,43" (strings com vírgula decimal)
        # Precisamos converter vírgula para ponto ANTES de converter para float
        
        # Lista para debug
        debug_conversions = []
        
        def convert_brazilian_decimal(val):
            """Converte valores do formato brasileiro (vírgula) para float"""
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
                    # Se tem PONTO E VÍRGULA: formato "1.234,56" (ponto=milhar, vírgula=decimal)
                    if '.' in val_clean:
                        # Remove pontos (separador de milhar) e troca vírgula por ponto
                        val_clean = val_clean.replace('.', '').replace(',', '.')
                    # Se tem APENAS VÍRGULA: formato "18500,51" (vírgula=decimal)
                    else:
                        # Apenas troca vírgula por ponto (NÃO remove nada!)
                        val_clean = val_clean.replace(',', '.')
                    
                    try:
                        result = float(val_clean)
                        # Debug: registrar conversões de valores monetários
                        if result > 100:  # Provavelmente valor monetário
                            debug_conversions.append(f"{original_val} → {result}")
                        return result
                    except ValueError:
                        return val  # Se não conseguir converter, retorna original
            
            return val
        
        # Aplicar conversão em todas as colunas
        for col in result_df.columns:
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
        
        def check_status(deadline):
            if pd.isna(deadline):
                return "Data Inválida"
            
            days_remaining = (deadline - today).days
            
            if days_remaining < 0:
                return "Vencido"
            elif days_remaining <= 5: # Warning threshold
                return f"Vence em {days_remaining} dias"
            else:
                return "No Prazo"

        result_df["Status"] = result_df["Prazo (90 dias)"].apply(check_status)
        
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
            # Ex: Número do Empenho, Código do Fornecedor
            if any(palavra in col_lower for palavra in ['empenho', 'emp.', 'emp', 'código', 'codigo', 'cod.', 'nº', 'numero', 'número']):
                continue
                
            # Verificar se é uma coluna numérica que provavelmente contém valores monetários
            if pd.api.types.is_numeric_dtype(result_df[col]):
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



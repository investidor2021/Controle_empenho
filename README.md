# Acompanhamento de Empenhos

Sistema em Python com Streamlit para acompanhamento e gestão de empenhos, integrado ao Google Sheets.

## Funcionalidades

- **Login e Cadastro**: Sistema de autenticação com perfis de "Administrador" e "Usuário".
- **Visualização de Empenhos**:
  - Filtros por Departamento (automático para usuários comuns).
  - Filtros avançados por Data, Fornecedor e Número de Empenho.
  - Visualização em tabela com histórico rolável.
  - Edição de observações em tempo real.
- **Upload Inteligente (Admin)**:
  - Upload de planilhas (.xlsx, .csv).
  - Mesclagem inteligente: atualiza valores de empenhos existentes mas preserva as observações antigas.
- **Performance**: Paginação e cache de dados.

## Como Configurar

1.  **Instale as dependências**:
    ```bash
    pip install streamlit pandas gspread google-auth
    ```

2.  **Configuração do Google Sheets**:
    -   Você precisa de um arquivo `credenciais.json` de uma Service Account do Google.
    -   Coloque este arquivo na raiz do projeto.
    -   **Importante**: NÃO suba este arquivo para o GitHub.

3.  **Executar**:
    ```bash
    streamlit run main2.py
    ```

## Estrutura do Projeto

- `main2.py`: Aplicação principal Streamlit.
- `auth_manager.py`: Gerenciamento de usuários e autenticação.
- `data_processor.py`: Lógica de processamento de dados e planilhas.

## Como subir para o GitHub Desktop

1.  Abra o **GitHub Desktop**.
2.  Vá em **File** > **Add Local Repository**.
3.  Escolha a pasta deste projeto: `c:\projetos GitHub\acompanhamento de empenhos`.
4.  Ele vai perguntar se você quer criar um repositório. Clique em **create a repository**.
5.  Em **Git Ignore**, selecione **None** (pois já criamos o arquivo `.gitignore` manualmente).
6.  Clique em **Create Repository**.
7.  Clique no botão azul **Publish repository** no topo.
8.  **Importante**: Verifique se o arquivo `credenciais.json` NÃO aparece na lista de arquivos sendo enviados. (Ele deve ser ignorado).
9.  Clique em **Publish**.

## Como Publicar no Streamlit Cloud

1.  Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com seu GitHub.
2.  Clique em **New app**.
3.  Selecione o repositório que você acabou de criar.
4.  **Main file path**: `main2.py`.
5.  Clique em **Advanced settings...** (Isso é muito importante!).
6.  Na caixa **Secrets**, você deve colar o conteúdo do seu arquivo `credenciais.json` no seguinte formato:

    ```toml
    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "..."
    client_email = "..."
    client_id = "..."
    auth_uri = "..."
    token_uri = "..."
    auth_provider_x509_cert_url = "..."
    client_x509_cert_url = "..."
    ```

    *Copie tudo que está dentro das chaves `{ }` do seu `credenciais.json` e cole logo abaixo de `[gcp_service_account]` (ajustando para formato TOML, ou seja, sem as chaves externas e com chaves = valores).*
    
    **Dica**: O jeito mais fácil é copiar o conteúdo do `credenciais.json` e adaptar. O Streamlit precisa que fique no formato TOML mostrado acima.
    
7.  Clique em **Save**.
7.  Clique em **Save**.
8.  Clique em **Deploy!**.

## FAQ: GitHub

### Como enviar os arquivos (Push)?
Se você já configurou o repositório no GitHub Desktop conforme o passo "Como subir para o GitHub Desktop":
1.  Qualquer alteração que você fizer na pasta, aparecerá no **GitHub Desktop** na aba esquerda.
2.  Digite um "Summary" (ex: "Atualização inicial") na caixinha inferior esquerda.
3.  Clique em **Commit to main**.
4.  Clique no botão **Push origin** no topo direito para enviar para o site.

### Como mudar para Público?
1.  Vá na página do seu repositório no site do GitHub.
2.  Clique na aba **Settings** (Engrenagem no topo).
3.  Role a página até o final, na seção "Danger Zone".
4.  Procure por **Change repository visibility**.
5.  Clique em **Change visibility**, selecione **Make public** e confirme.
    *   **CUIDADO**: Se o repositório for público, qualquer um vê seu código. Certifique-se que o `credenciais.json` NÃO está lá! (O arquivo `.gitignore` deve prevenir isso).

## Execução no Windows / VS Code

### 1. Pré-requisitos

Antes de executar o projeto, é necessário ter instalado:

- **Python 3.10 ou superior**
- **Visual Studio Code**
- **Bibliotecas Python do projeto**, incluindo Streamlit e Pandas

O Python pode ser obtido em https://www.python.org/downloads/.

### 2. Criar o ambiente virtual

Abra a pasta do projeto `cp3-sers` no VS Code e execute no terminal:

```powershell
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se a ativação for bloqueada pelo PowerShell, utilize o Python do ambiente virtual diretamente nos comandos seguintes.

### 3. Instalar as dependências

**Esta etapa é obrigatória na primeira execução do projeto.**

```powershell
python -m pip install -r requirements.txt
```

O comando instala automaticamente as bibliotecas especificadas no arquivo `requirements.txt`, incluindo o Streamlit.

Caso o Streamlit não seja instalado, execute:

```powershell
python -m pip install streamlit pandas
```

### 4. Executar a aplicação

Após instalar as dependências, execute:

```powershell
python -m streamlit run app.py
```

O Streamlit disponibilizará um endereço semelhante a:

```text
Local URL: http://localhost:8501
```

Abra http://localhost:8501 no navegador.

**Importante:** não execute `python app.py`, pois a aplicação utiliza recursos do Streamlit que precisam ser iniciados pelo comando `streamlit run`.

### 5. Executar os testes automatizados

Instale o Pytest:

```powershell
python -m pip install pytest
```

Execute os testes:

```powershell
python -m pytest -q
```

### 6. Persistência dos dados

Os cadastros e dimensionamentos realizados são armazenados em:

`dados/projetos.json`

O arquivo é criado automaticamente e permite recuperar os dados em execuções posteriores.

### 7. Quadro Trello

O acompanhamento das User Stories e Tasks da Sprint 3 está disponível no quadro:

https://trello.com/b/Mxqypg7H/cp3-sers
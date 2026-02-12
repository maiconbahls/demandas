# Flow - Sistema de Gestão Inteligente de Demandas ✨

Este é um sistema robusto desenvolvido em **Streamlit** para gestão estratégica de demandas, atividades e acompanhamento de projetos.

## 🚀 Funcionalidades

- **Painel Estratégico**: Visualização de KPIs e indicadores de performance.
- **Quadros (Kanban/Categorias)**: Gestão visual de tarefas por status e temas.
- **Integração com Google Sheets**: Sincronização em tempo real com a nuvem.
- **Página de Categorias**: Nova visualização agrupada por temas (Bolsas, Educação, Estágio, etc.).
- **Follow-Up e Cronograma**: Ferramentas para acompanhamento detalhado de prazos e feedbacks.
- **Gestão de RC/PO**: Controle de requisições de compra e pedidos.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Streamlit**: Framework para a interface web.
- **Pandas**: Manipulação de dados.
- **Plotly**: Gráficos interativos.
- **Google Sheets API (gspread)**: Armazenamento persistente na nuvem.

## 📦 Como Instalar e Rodar

1. Clone o repositório:
   ```bash
   git clone https://github.com/maiconbahls/demandas.git
   cd demandas
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute a aplicação:
   ```bash
   streamlit run app.py
   ```

## 🔐 Configuração do Google Sheets

Para usar a integração com a nuvem, você deve configurar os segredos no Streamlit (`.streamlit/secrets.toml` localmente ou no Cloud):

```toml
[gcp_service_account]
type = "service_account"
project_id = "seu-projeto"
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
# ... outros campos da service account

SHEET_NAME = "NomeDaSuaPlanilha"
USER_EMAIL = "seu-email@exemplo.com"
```

---
*Desenvolvido por Maicon Bahls*

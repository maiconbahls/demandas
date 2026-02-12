"""
Flow - Sistema de Gestão Inteligente de Demandas
Versão: 7.0 - Updates por Atividade + Painel Estratégico
Autor: Maicon Bahls
Data: 06/01/2026
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass, field, asdict
import json
import os
import time
import calendar
import textwrap
import base64

# ==========================================
# CONFIGURAÇÕES E CONSTANTES
# ==========================================

PAGE_CONFIG = {
    "page_title": "Flow • Gestão Inteligente",
    "page_icon": "✨",
    "layout": "wide",
    "initial_sidebar_state": "collapsed"
}

DATA_FILE = "flow_data.json"
UPDATES_FILE = "flow_updates.json"

STATUS_CONFIG = {
    'Pendente':     {'color': '#c4c4c4', 'bg': '#414361', 'text': '#ffffff'},
    'Em Andamento': {'color': '#fdab3d', 'bg': '#5a4a2a', 'text': '#fdab3d'},
    'Para Revisão': {'color': '#00c875', 'bg': '#1f4a3c', 'text': '#00c875'},
    'Concluído':    {'color': '#00ca72', 'bg': '#1f4a3c', 'text': '#00ca72'}
}

PRIORITY_CONFIG = {
    'Baixa':   {'color': '#579bfc', 'bg': '#2a3d5a'},
    'Média':   {'color': '#fdab3d', 'bg': '#5a4a2a'},
    'Alta':    {'color': '#e44258', 'bg': '#4a2a2f'},
    'Urgente': {'color': '#df2f4a', 'bg': '#4a2a2f'}
}

DEFAULT_CATEGORY_OPTIONS = {
    "📚 Bolsas de Estudos": {
        "color": "#fdab3d", "icon": "📚", "name": "Bolsas de Estudos", "bg": "#5a4a2a"
    },
    "🎓 Incentivo à Educação (ETEC)": {
        "color": "#e44258", "icon": "🎓", "name": "Incentivo à Educação (ETEC)", "bg": "#4a2a2f"
    },
    "💼 Programa de Estágio": {
        "color": "#00c875", "icon": "💼", "name": "Programa de Estágio", "bg": "#1f4a3c"
    },
    "📊 Indicadores da Área": {
        "color": "#00d9ff", "icon": "📊", "name": "Indicadores da Área", "bg": "#1f3d4a"
    },
    "⚙️ Projeto de Desenvolvimento": {
        "color": "#579bfc", "icon": "⚙️", "name": "Projeto de Desenvolvimento", "bg": "#2a3d5a"
    },
    "🤝 Relacionamento com Instituições": {
        "color": "#a25ddc", "icon": "🤝", "name": "Relacionamento com Instituições", "bg": "#3d2a5a"
    },
    "🏢 Deskbee": {
        "color": "#00cd8e", "icon": "🏢", "name": "Deskbee", "bg": "#1f4a3c"
    },
    "👥 Pessoas/Atendimentos": {
        "color": "#ff5ac4", "icon": "👥", "name": "Pessoas/Atendimentos", "bg": "#4a2a4a"
    },
    "📋 Outros": {
        "color": "#9699a6", "icon": "📋", "name": "Outros", "bg": "#3d3d4a"
    }
}

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ==========================================
# MODELO DE DADOS
# ==========================================

@dataclass
class TaskUpdate:
    task_id: int
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user: str = "Maicon"
    id: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict, index: int = 0) -> "TaskUpdate":
        # Compatibilidade com dados antigos sem ID - usar hash único
        if 'id' not in data:
            # Gerar ID único baseado no conteúdo + timestamp + index
            unique_str = f"{data.get('task_id', 0)}_{data.get('timestamp', '')}_{data.get('content', '')[:20]}_{index}"
            data['id'] = hash(unique_str) & 0x7FFFFFFF  # Garante positivo
        return cls(**data)


@dataclass
class Task:
    title: str
    responsible: str
    category: str
    priority: str
    status: str
    due_date: str
    description: str = ""
    attachments: List[str] = field(default_factory=list)
    collaborators: List[str] = field(default_factory=list)  # Colaboradores mencionados
    manager_feedback: str = "" # Feedback da gestão
    id: int = field(default_factory=lambda: int(time.time() * 1000))
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def __post_init__(self):
        if not self.title or not self.title.strip():
            raise ValueError("Título é obrigatório")
        if isinstance(self.due_date, (datetime, date)):
            self.due_date = self.due_date.strftime("%Y-%m-%d")
        # Garantir que collaborators seja uma lista
        if self.collaborators is None:
            self.collaborators = []
        if isinstance(self.collaborators, str):
            try:
                import ast
                self.collaborators = ast.literal_eval(self.collaborators) if self.collaborators else []
            except:
                self.collaborators = []
        
        # Sanitização preventiva dos dados
        import re
        import html
        
        def clean_val(text):
            if not text: return ""
            # Unescape e remover tags
            txt = html.unescape(str(text))
            txt = re.sub(r'<[^>]*>', '', txt)
            return txt.strip()
            
        self.title = clean_val(self.title)
        
        if self.collaborators and isinstance(self.collaborators, list):
             self.collaborators = [clean_val(c) for c in self.collaborators if clean_val(c)]
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["dueDate"] = data.pop("due_date")
        data["createdAt"] = data.pop("created_at")
        # Converter lista de collaborators para string para salvar no Sheets
        if "collaborators" in data and isinstance(data["collaborators"], list):
            data["collaborators"] = str(data["collaborators"])
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        # Converter collaborators de string para lista
        collabs = data.get("collaborators", [])
        if isinstance(collabs, str):
            try:
                import ast
                collabs = ast.literal_eval(collabs) if collabs else []
            except:
                collabs = []
        
        return cls(
            title=data.get("title", ""),
            responsible=data.get("responsible", "Maicon"),
            category=data.get("category", "Outros"),
            priority=data.get("priority", "Média"),
            status=data.get("status", "Pendente"),
            due_date=data.get("dueDate", datetime.now().strftime("%Y-%m-%d")),
            description=data.get("description", ""),
            attachments=data.get("attachments", []),
            collaborators=collabs,
            id=data.get("id", int(time.time() * 1000)),
            created_at=data.get("createdAt", datetime.now().strftime("%Y-%m-%d")),
            manager_feedback=data.get("manager_feedback", "")
        )
    
    def is_urgent_today(self) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.priority == "Urgente" and self.status != "Concluído" and self.due_date == today
    
    def get_category_info(self) -> Dict:
        # Use session state categories if available, else default
        cats = st.session_state.get("categories", DEFAULT_CATEGORY_OPTIONS)
        for key, info in cats.items():
            if info["name"] == self.category or key == self.category:
                return info
        return cats.get("📋 Outros", DEFAULT_CATEGORY_OPTIONS["📋 Outros"])

@dataclass
class RequestRC:
    subelement: str = "RC"
    date_opening: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    description: str = ""
    rc_code: str = ""
    buyer: str = ""
    situation: str = "Pendente"
    attachments: List[str] = field(default_factory=list)
    po_number: str = ""
    nf_tracking: str = "Aguardando recebimento"
    nf_attachments: List[str] = field(default_factory=list)
    id: int = field(default_factory=lambda: int(time.time() * 1000))
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RequestRC":
        return cls(**data)


# ==========================================
# GERENCIADOR DE DADOS
# ==========================================

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Cache da conexão do Google Sheets (para evitar reconexões lentas)
@st.cache_resource(ttl=600)  # Cache por 10 minutos
def get_sheets_connection():
    """Retorna a conexão cacheada com o Google Sheets"""
    try:
        if "gcp_service_account" not in st.secrets:
            return None, None
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        service_account_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        
        sheet_name = st.secrets.get("SHEET_NAME", "FlowData")
        try:
            sh = gc.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(sheet_name)
            user_email = st.secrets.get("USER_EMAIL")
            if user_email:
                sh.share(user_email, perm_type='user', role='writer')
        
        return gc, sh
    except Exception as e:
        print(f"Erro ao conectar com Google Sheets: {e}")
        return None, None

# Helper function para obter o DataManager do session_state (singleton)
def get_data_manager():
    """Retorna o DataManager singleton do session_state"""
    if "data_manager_instance" not in st.session_state:
        st.session_state.data_manager_instance = DataManager()
    return st.session_state.data_manager_instance

# ==========================================
# GERENCIADOR DE DADOS
# ==========================================

class DataManager:
    def __init__(self, file_path: str = None):
        # Identificar usuário atual para isolamento de dados
        user_id = st.session_state.get("current_user", "2949400") # Padrão: Maicon
        self.user_id = user_id
        
        # Paths locais (Legacy/Fallback)
        if user_id == "2949400":
            self.file_path = DATA_FILE
            self.updates_path = UPDATES_FILE
            self.categories_path = "flow_categories.json"
            self.requests_path = "flow_requests.json"
        else:
            self.file_path = f"flow_data_{user_id}.json"
            self.updates_path = f"flow_updates_{user_id}.json"
            self.categories_path = f"flow_categories_{user_id}.json"
            self.requests_path = f"flow_requests_{user_id}.json"
            
        if file_path:
            self.file_path = file_path

        # Usar conexão cacheada do Google Sheets (MUITO MAIS RÁPIDO!)
        self.use_sheets = False
        self.gc = None
        self.sh = None
        
        gc, sh = get_sheets_connection()
        if gc is not None and sh is not None:
            self.use_sheets = True
            self.gc = gc
            self.sh = sh
    
    def _connect_sheets(self):
        # Método mantido para compatibilidade, mas agora usa cache
        gc, sh = get_sheets_connection()
        if gc is not None:
            self.gc = gc
            self.sh = sh
            self.use_sheets = True
        else:
            self.use_sheets = False

    def _get_worksheet(self, name: str):
        if not self.use_sheets: return None
        try:
            return self.sh.worksheet(name)
        except:
            # Se não existir a aba, cria
            return self.sh.add_worksheet(title=name, rows=1000, cols=10)

    # ---- Categorias ----
    def load_categories(self) -> Dict:
        # Se usar Sheets
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Categories")
                records = ws.get_all_records()
                # Converter lista de registros para Dict estrturado
                cats = {}
                for row in records:
                    key = row.get("key")
                    if key:
                         cats[key] = {
                             "color": row.get("color"),
                             "icon": row.get("icon"),
                             "name": row.get("name"),
                             "bg": row.get("bg")
                         }
                if not cats: return DEFAULT_CATEGORY_OPTIONS.copy()
                return cats
            except:
                return DEFAULT_CATEGORY_OPTIONS.copy()

        # Fallback Local
        user_id = st.session_state.get("current_user", "2949400")
        is_admin = user_id in ["2949400", "2484901", "GESTAO"]
        
        if not os.path.exists(self.categories_path):
            if is_admin: return DEFAULT_CATEGORY_OPTIONS.copy()
            else: return {}
        try:
            with open(self.categories_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
             return DEFAULT_CATEGORY_OPTIONS.copy() if is_admin else {}

    def save_categories(self, categories: Dict) -> bool:
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Categories")
                # Flatten dict to list of dicts for sheet
                data = []
                for key, val in categories.items():
                    item = val.copy()
                    item['key'] = key
                    data.append(item)
                
                if data:
                    ws.clear()
                    ws.append_row(list(data[0].keys()))
                    rows = [list(d.values()) for d in data]
                    ws.append_rows(rows)
                else:
                    ws.clear()
                return True
            except Exception as e:
                st.error(f"Erro ao salvar categorias na nuvem: {e}")
                return False

        # Local
        try:
            with open(self.categories_path, "w", encoding="utf-8") as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar categorias localmente: {e}")
            return False

    # ---- Requisições (RC/PO) ----
    def load_requests(self) -> List[RequestRC]:
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Requests")
                records = ws.get_all_records()
                # Filtrar por usuário se não for admin (implementar lógica de admin aqui se necessário)
                return [RequestRC.from_dict({k: v for k, v in r.items() if k != 'attachments_str' and k in RequestRC.__annotations__}) for r in records]
            except:
                return []

        # Local
        user_id = st.session_state.get("current_user", "2949400")
        if user_id in ["GESTAO", "2484901"]:
            # Logic for reading all files for admin... (Simplificado para manter o foco)
            pass 
        
        if not os.path.exists(self.requests_path): return []
        try:
            with open(self.requests_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [RequestRC.from_dict(item) for item in data]
        except: return []

    def save_requests(self, requests: List[RequestRC]) -> bool:
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Requests")
                data = [r.to_dict() for r in requests]
                # Para sheets, precisamos garantir que listas virem strings
                formatted_data = []
                for item in data:
                    new_item = item.copy()
                    new_item['attachments'] = str(item['attachments']) # Flatten list
                    new_item['nf_attachments'] = str(item['nf_attachments'])
                    formatted_data.append(new_item)
                
                # Update full sheet
                if formatted_data:
                    ws.clear()
                    # Headers
                    ws.append_row(list(formatted_data[0].keys()))
                    # Rows
                    rows = [list(d.values()) for d in formatted_data]
                    ws.append_rows(rows)
                else:
                    ws.clear()
                return True
            except Exception as e:
                st.error(f"Erro Cloud: {e}")
                return False

        # Local
        try:
            with open(self.requests_path, "w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
            return True
        except: return False

    # ---- Tarefas ----
    def load_tasks(self) -> List[Task]:
        # --- GOOGLE SHEETS ---
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Tasks")
                records = ws.get_all_records()
                
                tasks = []
                for r in records:
                    # Converter string de list de volta para list
                    if 'attachments' in r and isinstance(r['attachments'], str):
                        try:
                            r['attachments'] = eval(r['attachments'])
                        except:
                            r['attachments'] = []
                    
                    # Garantir campos obrigatórios
                    if 'id' in r:
                         tasks.append(Task.from_dict(r))
                return tasks
            except Exception as e:
                # Se falhar conexão ou aba vazia
                return []

        # --- LOCAL FILES ---
        user_id = st.session_state.get("current_user", "2949400")
        
        # "Gestão" must see ALL tasks from ALL files
        if user_id in ["GESTAO", "2484901"]:
            all_tasks = []
            seen_ids = set()
            files_to_load = [DATA_FILE]
            if os.path.exists("."):
                for f in os.listdir("."):
                    if f.startswith("flow_data_") and f.endswith(".json"):
                        files_to_load.append(f)
            for fpath in files_to_load:
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            for item in data:
                                t = Task.from_dict(item)
                                if t.id not in seen_ids:
                                    all_tasks.append(t)
                                    seen_ids.add(t.id)
                    except: pass
            return all_tasks

        if not os.path.exists(self.file_path):
            return self._create_initial_data()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tasks = [Task.from_dict(item) for item in data]
            return tasks
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return []
    
    def save_tasks(self, tasks: List[Task]) -> bool:
        # --- GOOGLE SHEETS ---
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Tasks")
                data = [t.to_dict() for t in tasks]
                
                 # Formatar para Sheet (Listas viram strings)
                formatted_data = []
                headers = []
                if data:
                    headers = list(data[0].keys())
                
                for item in data:
                    new_item = item.copy()
                    if 'attachments' in new_item:
                         new_item['attachments'] = str(new_item['attachments'])
                    formatted_data.append(new_item)

                ws.clear()
                if headers:
                    ws.append_row(headers)
                    rows = [list(d.values()) for d in formatted_data]
                    ws.append_rows(rows)
                return True
            except Exception as e:
                st.error(f"Erro ao salvar na nuvem: {e}")
                return False

        # --- LOCAL ---
        try:
            data = [t.to_dict() for t in tasks]
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar dados dados: {e}")
            return False
    
    def _create_initial_data(self) -> List[Task]:
        # Para Maicon (ou fallback)
        base_id = int(time.time() * 1000)
        initial_tasks = [
            Task(title="Exemplo de Tarefa", responsible="Maicon", category="Outros", priority="Média", status="Pendente", due_date=datetime.now().strftime("%Y-%m-%d"), id=base_id)
        ]
        self.save_tasks(initial_tasks)
        return initial_tasks
    
    # ---- Updates ----
    def load_updates(self) -> List[TaskUpdate]:
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Updates")
                records = ws.get_all_records()
                # Converter para obj
                return [TaskUpdate.from_dict(r) for r in records]
            except:
                return []

        if not os.path.exists(self.updates_path): return []
        try:
            with open(self.updates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [TaskUpdate.from_dict(item, idx) for idx, item in enumerate(data)]
        except: return []
    
    def save_updates(self, updates: List[TaskUpdate]) -> bool:
        if self.use_sheets:
            try:
                ws = self._get_worksheet("Updates")
                data = [u.to_dict() for u in updates]
                
                ws.clear()
                if data:
                    ws.append_row(list(data[0].keys()))
                    rows = [list(d.values()) for d in data]
                    ws.append_rows(rows)
                return True
            except: return False

        try:
            data = [u.to_dict() for u in updates]
            with open(self.updates_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except: return False
    
    def add_update(self, update: TaskUpdate) -> None:
        updates = self.load_updates()
        updates.append(update)
        self.save_updates(updates)
    
    def get_task_updates(self, task_id: int) -> List[TaskUpdate]:
        return [u for u in self.load_updates() if u.task_id == task_id]
    
    def delete_update(self, update_id: int) -> bool:
        updates = self.load_updates()
        updates = [u for u in updates if u.id != update_id]
        return self.save_updates(updates)
    
    def edit_update(self, update_id: int, new_content: str) -> bool:
        updates = self.load_updates()
        for u in updates:
            if u.id == update_id:
                u.content = new_content
                u.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (editado)"
                break
        return self.save_updates(updates)

# ==========================================
# FUNÇÃO PARA BUSCAR COLABORADOR
# ==========================================

GESTORES_FILE = "gestores.xlsx"

@st.cache_data(ttl=3600, show_spinner=False)
def load_gestores_data():
    if not os.path.exists(GESTORES_FILE):
        return pd.DataFrame()
    return pd.read_excel(GESTORES_FILE)

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_colaborador_por_matricula(matricula: str) -> Dict:
    """Busca dados do colaborador no arquivo gestores.xlsx pela matrícula."""
    if not matricula or not matricula.strip():
        return {}
    
    try:
        # Limpar matrícula
        matricula_clean = str(matricula).strip()
        
        df = load_gestores_data()
        if df.empty:
            return {}
        
        # Buscar pela matrícula (pode ser número ou string)
        df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
        resultado = df[df['MATRICULA'] == matricula_clean]
        
        if resultado.empty:
            # Tentar como número
            try:
                matricula_num = int(float(matricula_clean))
                df['MATRICULA_NUM'] = pd.to_numeric(df['MATRICULA'], errors='coerce')
                resultado = df[df['MATRICULA_NUM'] == matricula_num]
            except:
                pass
        
        if resultado.empty:
            return {}
        
        row = resultado.iloc[0]
        return {
            'nome': str(row.get('COLABORADOR', '')).strip() if pd.notna(row.get('COLABORADOR')) else '',
            'telefone': str(row.get('TELEFONE', '')).strip() if pd.notna(row.get('TELEFONE')) else '',
            'diretoria': str(row.get('DIRETORIA', '')).strip() if pd.notna(row.get('DIRETORIA')) else '',
            'cargo': str(row.get('DESCRIÇÃO CARGO', row.get('DESCRI\xc7O CARGO', row.get('DESCRIÇÃO CARGO', '')))).strip() if pd.notna(row.get('DESCRIÇÃO CARGO', row.get('DESCRI\xc7O CARGO', row.get('DESCRIÇÃO CARGO', '')))) else '',
            'email': str(row.get('EMAIL PARTICULAR', '')).strip() if pd.notna(row.get('EMAIL PARTICULAR')) else '',
            'matricula': matricula_clean
        }
    except Exception as e:
        return {}

# ==========================================
# COMPONENTES DE UI
# ==========================================

class UIComponents:
    @staticmethod
    def render_kpi_card(label: str, value: int, icon: str, gradient: str, main_color: str) -> None:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon-container" style="background: {main_color}22; border: 1px solid {main_color}44;">
                    <span class="kpi-icon">{icon}</span>
                </div>
                <div class="kpi-content">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value-container">
                        <span class="kpi-value" style="background: {gradient}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; color: {main_color};">
                            {value}
                        </span>
                    </div>
                </div>
                <div class="kpi-glow" style="background: {main_color}; opacity: 0.1;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def render_page_header(title: str, subtitle: str = "Controle Pessoal • Maicon Bahls") -> None:
        st.markdown(
            f"""
            <div class="page-header">
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ==========================================
# NAVEGAÇÃO + FILTROS
# ==========================================

class NavigationSystem:
    NAV_OPTIONS = {
        "Painel": "📊",
        "Quadros": "📋",
        "Calendário": "📅",
        "Categorias": "📂",
        "Cronograma": "📑",
        "Acompanhamento": "📅",
        "Follow-Up": "💼",
    }
    
    @classmethod
    def render(cls) -> Tuple[str, str, str]:
        if "selected_page" not in st.session_state:
            st.session_state.selected_page = "Quadros"
        
        # CSS para Navegação Premium
        st.markdown("""
        <style>
        /* Container de Navegação */
        /* REMOVER: Isso causava desalinhamento em outras colunas do dashboard
        div[data-testid="stHorizontalBlock"] {
            align-items: center !important;
        } 
        */
        
        /* Estilização Geral de Botões de Nav */
        /* Estilização Geral de Botões de Nav */
        div.stButton > button {
            color: white !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
            background: rgba(255,255,255,0.03) !important;
            transition: all 0.3s ease !important;
            height: 42px !important;
            padding: 0 2px !important; /* Minimal padding */
            font-size: 0.8rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            white-space: nowrap !important;
            overflow: hidden !important;
        }
        
        /* Forçar texto em uma linha e com reticências */
        div.stButton > button p, div.stButton > button div {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            font-size: 0.8rem !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: normal !important;
            display: inline-block !important;
            max-width: 100% !important;
        }

        div.stButton > button:hover {
            background: rgba(255,255,255,0.12) !important;
            border-color: rgba(99, 102, 241, 0.8) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
            z-index: 10 !important;
        }
        
        /* Botão Ativo */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.5) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
        }

        /* Inputs (Select e Text) */
        div[data-testid="stSelectbox"] > div > div, 
        div[data-testid="stTextInput"] > div > div {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
            border-radius: 12px !important;
            height: 42px !important;
            color: white !important;
        }
        
        div[data-testid="stSelectbox"] div, 
        div[data-testid="stTextInput"] input {
            color: white !important;
        }
        
        div[data-testid="stSelectbox"] > div > div:hover,
        div[data-testid="stTextInput"] > div > div:hover {
            border-color: rgba(99, 102, 241, 0.6) !important;
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.2) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 8. Nova Button (Check for Manager first)
        current_user = st.session_state.get("current_user", "")
        is_manager = (current_user == "2484901" or current_user == "GESTAO")
        
        # Adjust layout based on role
        if is_manager:
            # 9 slots: 7 Nav + Search + Nova
            # Reorganize Cols: Navs (7) | Gestão (1) | Search+Nova (Combined or separate?)
            # Let's use 9 columns
            # [1, 1, 1, 1, 1, 1, 1.2, 2, 0.8] approx
            # [1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.4, 2, 1] approx
             cols = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.4, 2, 1])
        else:
             cols = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 2, 0.8])
        
        # ... Render standard buttons 0-5 ...
        with cols[0]:
            if st.button("📊 Painel", key="nav_Painel", use_container_width=True, type="primary" if st.session_state.selected_page == "Painel" else "secondary"):
                st.session_state.selected_page = "Painel"
                st.rerun()
        with cols[1]:
            if st.button("📋 Quadros", key="nav_Quadros", use_container_width=True, type="primary" if st.session_state.selected_page == "Quadros" else "secondary"):
                st.session_state.selected_page = "Quadros"
                st.rerun()
        with cols[2]:
            if st.button("📅 Calendário", key="nav_Calendário", use_container_width=True, type="primary" if st.session_state.selected_page == "Calendário" else "secondary"):
                st.session_state.selected_page = "Calendário"
                st.rerun()
        with cols[3]:
            if st.button("📂 Categorias", key="nav_Categorias", use_container_width=True, type="primary" if st.session_state.selected_page == "Categorias" else "secondary"):
                st.session_state.selected_page = "Categorias"
                st.rerun()
        with cols[4]:
            if st.button("📑 Cronograma", key="nav_Cronograma", use_container_width=True, type="primary" if st.session_state.selected_page == "Cronograma" else "secondary"):
                st.session_state.selected_page = "Cronograma"
                st.rerun()
        with cols[5]:
            if st.button("💼 Follow-Up", key="nav_Follow-Up", use_container_width=True, type="primary" if st.session_state.selected_page == "Follow-Up" else "secondary"):
                st.session_state.selected_page = "Follow-Up"
                st.rerun()
        
        # Manager Tab
        next_col_idx = 6
        if is_manager:
            with cols[6]:
                if st.button("👩‍💼 Gestão", key="nav_Gestao", use_container_width=True, type="primary" if st.session_state.selected_page == "Gestão" else "secondary"):
                    st.session_state.selected_page = "Gestão"
                    st.rerun()
            next_col_idx = 7

        # Search
        with cols[next_col_idx]:
            search_query = st.text_input("Pesquisar", placeholder="🔍 Buscar...", label_visibility="collapsed", key="search_input")
        
        # Nova Button
        with cols[next_col_idx + 1]:
            if st.button("➕ Nova", type="primary", use_container_width=True, key="btn_nav_new_task"):
                st.session_state.show_modal = True
                st.session_state.show_category_modal = False # Evitar conflito
        
        return search_query, st.session_state.selected_page


class DashboardView:
    @staticmethod
    def calculate_stats(tasks: List[Task]) -> Dict[str, int]:
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return {
            "total": len(tasks),
            "completed": len([t for t in tasks if t.status == "Concluído"]),
            "in_progress": len([t for t in tasks if t.status == "Em Andamento"]),
            "urgent": len([t for t in tasks if t.priority in ["Alta", "Urgente"]]),
            "overdue": len([t for t in tasks if t.due_date < today.strftime("%Y-%m-%d") and t.status != "Concluído"]),
            "this_week": len([t for t in tasks if week_start.strftime("%Y-%m-%d") <= t.due_date <= week_end.strftime("%Y-%m-%d")]),
        }
    
    @classmethod
    def render_kpis(cls, tasks: List[Task]) -> None:
        stats = cls.calculate_stats(tasks)
        cols = st.columns(5)
        
        kpi_data = [
            {"label": "TOTAL", "value": stats["total"], "icon": "📊", "color": "#6366f1", "grad": "linear-gradient(135deg, #6366f1, #a855f7)"},
            {"label": "CONCLUÍDAS", "value": stats["completed"], "icon": "🎯", "color": "#10b981", "grad": "linear-gradient(135deg, #10b981, #34d399)"},
            {"label": "URGENTES", "value": stats["urgent"], "icon": "🔔", "color": "#ef4444", "grad": "linear-gradient(135deg, #ef4444, #f87171)"},
            {"label": "ATRASADAS", "value": stats["overdue"], "icon": "⚠️", "color": "#ec4899", "grad": "linear-gradient(135deg, #ec4899, #f472b6)"},
            {"label": "ESTA SEMANA", "value": stats["this_week"], "icon": "📅", "color": "#64748b", "grad": "linear-gradient(135deg, #64748b, #94a3b8)"},
        ]

        for i, data in enumerate(kpi_data):
            with cols[i]:
                UIComponents.render_kpi_card(
                    label=data["label"],
                    value=data["value"],
                    icon=data["icon"],
                    gradient=data["grad"],
                    main_color=data["color"]
                )
    
    @staticmethod
    def render_status_chart(df: pd.DataFrame) -> None:
        if df.empty:
            return
        
            
        counts = df["status"].value_counts()
        total = counts.sum()
        
        colors = {
            'Concluído': '#10b981',      
            'Em Andamento': '#6366f1',   
            'Pendente': '#64748b',       
            'Para Revisão': '#a855f7'    
        }
        
        fig = px.pie(
            values=counts.values,
            names=counts.index,
            hole=0.6,
            color=counts.index,
            color_discrete_map=colors
        )
        
        fig.update_traces(
            textposition="none", 
            marker=dict(line=dict(color="#0f172a", width=0)),
            hovertemplate="<b>%{label}</b><br>%{value} tarefas<extra></extra>"
        )
        
        # Central text with total
        fig.add_annotation(
            text=f"<span style='font-size:24px; font-weight:800; color:white;'>{total}</span><br><span style='font-size:12px; color:#94a3b8;'>Tarefas</span>",
            showarrow=False,
            x=0.5, y=0.5
        )

        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h", 
                yanchor="bottom", y=-0.15, 
                xanchor="center", x=0.5, 
                font=dict(color="#94a3b8", size=10)
            ),
            margin=dict(t=10, b=30, l=10, r=10),
            height=340,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", family="Plus Jakarta Sans"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    @staticmethod
    def render_category_chart(df: pd.DataFrame) -> None:
        if df.empty:
            return
        
        
        counts = df["category"].value_counts()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=counts.values,
            y=counts.index,
            orientation='h',
            marker=dict(
                color=counts.values,
                colorscale=[[0, "#6366f1"], [1, "#10b981"]], # Indigo to Emerald
                line=dict(width=0),
            ),
            text=counts.values,
            textposition="outside",
            textfont=dict(color="white", size=11, weight="bold"),
            hovertemplate="<b>%{y}</b><br>%{x} atividades<extra></extra>"
        ))
        
        fig.update_layout(
            showlegend=False,
            margin=dict(t=20, b=30, l=10, r=40),
            height=340,
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)", tickfont=dict(color="#94a3b8", size=10), title=None),
            yaxis=dict(showgrid=False, tickfont=dict(color="white", size=11), title=None, automargin=True),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif")
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    @staticmethod
    def render_priority_chart(df: pd.DataFrame) -> None:
        if df.empty:
            return
        
            
        counts = df["priority"].value_counts().reindex(["Baixa", "Média", "Alta", "Urgente"], fill_value=0)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=counts.index,
            y=counts.values,
            marker=dict(
                color=["#6366f1", "#f59e0b", "#ef4444", "#7f1d1d"],
                line=dict(width=0),
            ),
            text=counts.values,
            textposition="outside",
            textfont=dict(color="white", size=12, weight="bold"),
            hovertemplate="<b>%{x}</b><br>%{y} tarefas<extra></extra>"
        ))
        
        fig.update_layout(
            margin=dict(t=20, b=10, l=0, r=0),
            height=360,
            xaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8", size=11), title=None),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#64748b", size=10), title=None),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif"),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


    
    @staticmethod
    def render_timeline_chart(tasks: List[Task]) -> None:
        if not tasks:
            return
        
        
        today = datetime.now()
        days = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
        counts = [len([t for t in tasks if t.due_date == d]) for d in days]
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in days]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=counts,
            mode='lines',
            line=dict(width=4, color='#6366f1', shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(99, 102, 241, 0.15)',
            hovertemplate="<b>%{x|%d/%m}</b><br>%{y} entregas<extra></extra>"
        ))
        
        fig.update_layout(
            margin=dict(t=10, b=10, l=0, r=0),
            height=280,
            hovermode="x unified",
            xaxis=dict(showgrid=False, tickfont=dict(color="#64748b", size=10), tickformat="%d/%m", showline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#64748b", size=10), title=None),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
        
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        cls.render_kpis(tasks)
        st.markdown("<div style='margin: 0.5rem 0;'></div>", unsafe_allow_html=True)
        df = pd.DataFrame([t.to_dict() for t in tasks])
        
        # --- LINHA 1: PRIORIDADE E RESUMO (MOVIDO PARA CIMA) ---
        c3, c4 = st.columns([0.4, 0.6])
        with c3:
            with st.container(border=True):
                st.markdown("""<div class="chart-header"><span class="chart-icon">⚠️</span><span class="chart-title">Prioridades</span></div>""", unsafe_allow_html=True)
                cls.render_priority_chart(df)
        
        with c4:
            with st.container(border=True):
                st.markdown("""<div class="chart-header"><span class="chart-icon">📅</span><span class="chart-title">Próximos Prazos Críticos</span></div>""", unsafe_allow_html=True)
                
                # Container interno com scroll para as tarefas críticas
                urgent_tasks = [t for t in tasks if t.status != "Concluído"]
                urgent_tasks.sort(key=lambda x: x.due_date)
                
                if not urgent_tasks:
                    st.write("✨ Tudo em dia!")
                else:
                    html_content = '<div style="height: 320px; overflow-y: auto; padding-right: 5px;">'
                    for t in urgent_tasks[:10]:
                        info = t.get_category_info()
                        color = info['color']
                        due_date = datetime.strptime(t.due_date, "%Y-%m-%d").strftime("%d/%m")
                        
                        # Build HTML without indentation to avoid code-block rendering
                        html_content += f"<div style='display: flex; align-items: center; gap: 12px; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 10px; margin-bottom: 8px; border-left: 3px solid {color};'>"
                        html_content += f"<div style='font-weight: 700; color: {color}; min-width: 45px;'>{due_date}</div>"
                        html_content += f"<div style='flex: 1; color: #f8fafc; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{t.title}</div>"
                        html_content += f"<div style='font-size: 0.7rem; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 4px;'>{t.status}</div>"
                        html_content += "</div>"
                        
                    html_content += '</div>'
                    st.markdown(html_content, unsafe_allow_html=True)

        # --- LINHA 2: VISÃO GERAL (TEMA E STATUS) ---
        c1, c2 = st.columns([0.65, 0.35])
        
        with c1:
            with st.container(border=True):
                st.markdown("""<div class="chart-header"><span class="chart-icon">📍</span><span class="chart-title">Distribuição por Tema</span></div>""", unsafe_allow_html=True)
                cls.render_category_chart(df)

        with c2:
            with st.container(border=True):
                st.markdown("""<div class="chart-header"><span class="chart-icon">📊</span><span class="chart-title">Status Global</span></div>""", unsafe_allow_html=True)
                cls.render_status_chart(df)
            
        # --- LINHA 3: FLUXO TEMPORAL ---
        with st.container(border=True):
            st.markdown("""<div class="chart-header"><span class="chart-icon">📈</span><span class="chart-title">Timeline de Entregas</span></div>""", unsafe_allow_html=True)
            cls.render_timeline_chart(tasks)

# ==========================================
# QUADROS (MONDAY STYLE + UPDATES)
# ==========================================

class BoardsView:
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        if not tasks:
            st.info("📋 Nenhuma tarefa encontrada. Crie sua primeira atividade!")
            return
        
        # Limpeza de estados não usados
        if "selected_tasks" in st.session_state:
            del st.session_state.selected_tasks
        
        if "expanded_task_updates" not in st.session_state:
            st.session_state.expanded_task_updates = set()
        
        dm = st.session_state.data_manager
        
        # CSS Refinado: Moderno, Compacto e Minimalista + Cards
        st.markdown(
            """
            <style>
            /* Ajuste de Alinhamento apenas para colunas do Footer de tarefas */
            .task-footer-columns div[data-testid="column"] { 
                display: flex !important; 
                flex-direction: column !important; 
                justify-content: center !important; 
                height: 38px !important; 
                margin: 0 !important;
                padding: 0 !important;
            }
            
            /* Selectbox Badge Moderno */
            .task-footer-columns div[data-testid="stSelectbox"] {
                margin-top: -32px !important;
                height: 38px !important;
                display: flex !important;
                align-items: center !important;
            }
            
            .task-footer-columns div[data-testid="stSelectbox"] > div > div {
                height: 38px !important;
            }
            
            /* Badges de informação no rodapé */
            .footer-badge {
                display: flex;
                align-items: center;
                gap: 8px;
                background: rgba(45, 212, 191, 0.12);
                border: 1px solid rgba(45, 212, 191, 0.2);
                padding: 4px 10px;
                border-radius: 8px;
                height: 38px;
                font-size: 0.8rem;
                color: #2dd4bf;
                font-weight: 700;
            }

            div[data-testid="stSelectbox"] > div > div:hover {
                background-color: rgba(255, 255, 255, 0.1) !important;
                border-color: rgba(255,255,255,0.2) !important;
            }

            div[data-testid="stSelectbox"] svg {
                fill: #aaa !important;
            }

            /* SUPERNOVA LOCAL FIX: TASK CARD BORDER & BUTTONS */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border: 2px solid #ffffff !important;
                background-color: rgba(30, 41, 59, 0.4) !important;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
                margin-bottom: 12px !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
                background-color: #0f172a !important;
                color: #ffffff !important;
                border: 1px solid rgba(255, 255, 255, 0.5) !important;
            }
            
            div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover {
                background-color: #6366f1 !important;
                border-color: #ffffff !important;
                transform: scale(1.05);
            }
            
            /* Melhoria visual para raias do Kanban */
            .kanban-card-hover:hover {
                background: rgba(255,255,255,0.06) !important;
                border-color: rgba(255,255,255,0.12) !important;
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def _clean_html(text: str) -> str:
        if not text: return ""
        import html
        import re
        
        # 1. Converter entities para caracteres reais (&lt; -> <) para o regex funcionar
        clean = html.unescape(str(text))
        
        # 2. Remover tags HTML específicas que costumam dar problema (case insensitive)
        # Remove divs, spans, p, br com qualquer atributo
        patterns = [
            r'</?div[^>]*>', 
            r'</?span[^>]*>', 
            r'</?p[^>]*>', 
            r'<br\s*/?>'
        ]
        for pattern in patterns:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)
        
        # 3. Remover qualquer outra tag HTML remanescente
        clean = re.sub(r'<[^>]*>', '', clean)
        
        # 4. Limpar espaços extras
        return re.sub(r'\s+', ' ', clean).strip()

    @classmethod
    def _process_description(cls, task: Task, info: Dict) -> str:
        if not task.description:
            return ""
        
        desc_clean = cls._clean_html(task.description)
        
        if not desc_clean:
            return ""
        
        # Lógica para DADOS DO COLABORADOR e ATENDIMENTO
        if "DADOS DO COLABORADOR" in desc_clean or "DADOS DO ATENDIMENTO" in desc_clean:
            lines = desc_clean.split('\n')
            current_section = None
            section_buffer = []

            def flush_buffer(buffer, section_name, color):
                if not buffer: return ""
                header = ""
                if section_name:
                    header = f"<div style='font-size:0.75rem;color:{color};font-weight:800;margin-bottom:4px;text-transform:uppercase;'>{section_name}</div>"
                
                html_out = header
                html_out += "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;'>"
                for item in buffer:
                    html_out += f"<span style='background:rgba(226, 232, 240, 0.1);padding:4px 10px;border-radius:6px;font-size:0.75rem;color:#f8fafc;border:1px solid rgba(255,255,255,0.1);'>{item}</span>"
                html_out += "</div>"
                return html_out

            final_html = ""
            for line in lines:
                line = line.strip()
                if not line or line.startswith('═'): continue
                if '📋' in line and 'DADOS' in line.upper(): 
                    final_html += flush_buffer(section_buffer, current_section, info['color'])
                    current_section = "📋 DADOS ATEND."
                    section_buffer = []
                elif '👤' in line and 'DADOS' in line.upper():
                    final_html += flush_buffer(section_buffer, current_section, info['color'])
                    current_section = "👤 DADOS COLAB."
                    section_buffer = []
                elif line.startswith('📂 Categoria:'): continue
                elif line:
                    cleaned = line.lstrip().lstrip('•').strip()
                    section_buffer.append(cleaned)
            
            final_html += flush_buffer(section_buffer, current_section, info['color'])
            return f"<div style='background:rgba(148, 163, 184, 0.1); padding:16px; border-radius:12px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.08);'>{final_html}</div>"
        
        # Escapar HTML na descrição normal para evitar quebras
        import html
        desc_escaped = html.escape(desc_clean)
        return f"<div style='background:rgba(148, 163, 184, 0.12); padding:12px; border-radius:8px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.1);'><div style=\"color:#f8fafc;font-size:0.85rem;line-height:1.4;\">{desc_escaped}</div></div>"

    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        if not tasks:
            st.info("📋 Nenhuma tarefa encontrada. Crie sua primeira atividade!")
            return
        
        # Limpeza de estados não usados
        if "selected_tasks" in st.session_state:
            del st.session_state.selected_tasks
        
        if "expanded_task_updates" not in st.session_state:
            st.session_state.expanded_task_updates = set()
        
        dm = st.session_state.data_manager
        
        # Filtros e Agrupamento
        grouped: Dict[str, Dict] = {}
        for task in tasks:
            info = task.get_category_info()
            name = info["name"]
            if name not in grouped:
                grouped[name] = {"info": info, "tasks": []}
            grouped[name]["tasks"].append(task)
        
        for cat_name in sorted(grouped.keys()):
            data = grouped[cat_name]
            info = data["info"]
            cat_tasks = data["tasks"]
            total = len(cat_tasks)
            done = len([t for t in cat_tasks if t.status == "Concluído"])
            
            st.markdown(
                f"""
                <div class="monday-group">
                    <div class="monday-group-header" style="background:{info['bg']};border-left:4px solid {info['color']};">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <span style="font-size:1.3rem;">{info['icon']}</span>
                            <span style="background:{info['color']};color:#ffffff;font-weight:800;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.5px;padding:4px 12px;border-radius:6px;">
                                {cat_name}
                            </span>
                            <span style="color:#cbd5e1;font-size:0.85rem;">
                                {total} atividades
                            </span>
                        </div>
                        <div style="color:#cbd5e1;font-size:0.85rem;">
                            {done}/{total} concluídas
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            for task in cat_tasks:
                info = task.get_category_info()
                due_str = datetime.strptime(task.due_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                
                # Container do Card usando o componente nativo do Streamlit para agrupar widgets
                with st.container(border=True):
                    # Container Colorido (Tema Suave) - Ajustado para cobrir o topo do card
                    # Montar string de colaboradores se houver (filtrar listas vazias)
                    collabs_html = ""
                    task_collabs = getattr(task, 'collaborators', None)
                    
                    # Tratar caso onde collaborators é uma string "[]" ou similar
                    if isinstance(task_collabs, str):
                        try:
                            import ast
                            # Usar literal_eval é mais seguro e robusto para listas simples
                            task_collabs = ast.literal_eval(task_collabs) if task_collabs else []
                            if not isinstance(task_collabs, list): task_collabs = []
                        except:
                            task_collabs = []
                    
                    if task_collabs and isinstance(task_collabs, list) and len(task_collabs) > 0:
                        # Filtrar strings vazias e LIMPAR HTML de cada nome
                        valid_collabs = []
                        for c in task_collabs:
                            c_clean = cls._clean_html(str(c))
                            if c_clean and c_clean != '[]':
                                valid_collabs.append(c_clean)
                        
                        if valid_collabs:
                            collabs_str = ", ".join(valid_collabs)
                            collabs_html = f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:6px;"><span style="color:#a78bfa;">👥</span> Com: {collabs_str}</div>'
                    
                    # Sanitizar título (remover HTML que possa ter sido salvo incorretamente)
                    import html as html_module
                    safe_title = cls._clean_html(task.title)
                    safe_title = html_module.escape(safe_title)
                    
                    st.markdown(
                        f"""<div style="margin-bottom:10px;">
<div style="display:flex;align-items:flex-start;gap:12px;">
<span style="font-size:1.5rem;line-height:1;">{info['icon']}</span>
<div style="flex:1;">
<div style="color:{info['color']};font-size:0.75rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">{info['name']}</div>
<div style="color:var(--text-main);font-size:1.1rem;font-weight:700;line-height:1.2;">{safe_title}</div>
{collabs_html}
</div>
</div>
</div>""",
                        unsafe_allow_html=True
                    )

                    # Descrição (Dentro do box colorido se houver)
                    if task.description:
                        desc_html = cls._process_description(task, info)
                        st.markdown(desc_html, unsafe_allow_html=True)
                    
                    if not task.description:
                         st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

                    # Área Interativa (Widgets Streamlit)
                    c_resp, c_date, c_stat, c_prio, c_acts = st.columns([0.15, 0.15, 0.18, 0.18, 0.34])
                    
                    with c_resp:
                        st.markdown(f'<div class="footer-badge">👤 {task.responsible}</div>', unsafe_allow_html=True)
                    
                    with c_date:
                        st.markdown(f'<div class="footer-badge">📅 {due_str[:5]}</div>', unsafe_allow_html=True)

                    with c_stat:
                        new_status = st.selectbox("Status", list(STATUS_CONFIG.keys()), index=list(STATUS_CONFIG.keys()).index(task.status), key=f"st_{task.id}", label_visibility="collapsed")
                        if new_status != task.status:
                            task.status = new_status
                            st.session_state.data_manager.save_tasks(st.session_state.tasks)
                            st.rerun()

                    with c_prio:
                        new_prio = st.selectbox("Prioridade", list(PRIORITY_CONFIG.keys()), index=list(PRIORITY_CONFIG.keys()).index(task.priority), key=f"pr_{task.id}", label_visibility="collapsed")
                        if new_prio != task.priority:
                            task.priority = new_prio
                            st.session_state.data_manager.save_tasks(st.session_state.tasks)
                            st.rerun()

                    with c_acts:
                         col_del, col_edit, col_exp = st.columns([0.33, 0.33, 0.34])
                         with col_del:
                             if st.button("🗑️", key=f"del_{task.id}", help="Excluir", use_container_width=True):
                                 st.session_state.tasks = [t for t in st.session_state.tasks if t.id != task.id]
                                 st.session_state.data_manager.save_tasks(st.session_state.tasks)
                                 st.rerun()
                         with col_edit:
                             if st.button("✏️", key=f"edit_btn_{task.id}", help="Editar Cadastro", use_container_width=True):
                                 st.session_state.editing_task_id = task.id
                                 st.rerun()
                         with col_exp:
                             is_expanded = task.id in st.session_state.expanded_task_updates
                             btn_icon = "▼" if is_expanded else "▶"
                             if st.button(btn_icon, key=f"upd_btn_{task.id}", help="Histórico", use_container_width=True):
                                 if is_expanded: st.session_state.expanded_task_updates.discard(task.id)
                                 else: st.session_state.expanded_task_updates.add(task.id)
                                 st.rerun()
                
                # --- INLINE EDIT FORM (RENDERIZADO LOGO ABAIXO DO CARD) ---
                if st.session_state.get("editing_task_id") == task.id:
                    st.markdown(
                        """
                        <div style="background: rgba(30, 41, 59, 0.95); padding: 20px; border-radius: 12px; border: 1px solid #6366f1; margin-top: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
                            <div style="color: #818cf8; font-weight: 700; margin-bottom: 12px; font-size: 0.9rem;">✏️ Editando: <span style="color: white;">{}</span></div>
                        </div>
                        """.format(task.title), unsafe_allow_html=True
                    )
                    
                    with st.container():
                         with st.form(key=f"inline_edit_{task.id}"):
                             ie_title = st.text_input("Título", value=task.title)
                             ie_desc = st.text_area("Descrição", value=task.description, height=100)
                             
                             iec1, iec2 = st.columns(2)
                             with iec1:
                                 ie_prio = st.selectbox("Prioridade", list(PRIORITY_CONFIG.keys()), index=list(PRIORITY_CONFIG.keys()).index(task.priority), key=f"ie_p_{task.id}")
                             with iec2:
                                 current_due_dt = datetime.strptime(task.due_date, "%Y-%m-%d")
                                 ie_due = st.date_input("Prazo", value=current_due_dt, format="DD/MM/YYYY", key=f"ie_d_{task.id}")
                             
                             mark_completed = st.checkbox("✅ Marcar como Concluída", value=(task.status == "Concluída"))
                             
                             st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                             icol1, icol2 = st.columns([0.4, 0.4])
                             
                             with icol1:
                                 if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                                     # Salvar lógica
                                     task.title = ie_title
                                     task.description = ie_desc
                                     task.priority = ie_prio
                                     task.due_date = ie_due.strftime("%Y-%m-%d")
                                     if mark_completed:
                                         task.status = "Concluída"
                                     elif task.status == "Concluída" and not mark_completed:
                                          task.status = "Pendente"
                                     
                                     st.session_state.data_manager.save_tasks(st.session_state.tasks)
                                     st.session_state.editing_task_id = None
                                     st.toast("Tarefa atualizada!", icon="✅")
                                     time.sleep(0.5)
                                     st.rerun()
                             
                             with icol2:
                                 if st.form_submit_button("❌ Fechar Edição", use_container_width=True):
                                     st.session_state.editing_task_id = None
                                     st.rerun()
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                
                if task.id in st.session_state.expanded_task_updates:
                    # Seção de Anexos
                    if task.attachments:
                        st.markdown(
                            """
                            <div style='background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;margin:12px 0;border:1px solid rgba(255,255,255,0.08);'>
                                <div style='display:flex;align-items:center;gap:8px;color:#94a3b8;font-size:0.75rem;font-weight:800;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;'>
                                    <span style='font-size:1rem;'>📎</span> Arquivos Anexados
                                </div>
                                <div style='display:grid;grid-template-columns:repeat(auto-fill, minmax(200px, 1fr));gap:10px;'>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        for idx, att_path in enumerate(task.attachments):
                            if os.path.exists(att_path):
                                file_name = os.path.basename(att_path)
                                # Limpar nome do arquivo (remover timestamp)
                                display_name = file_name.split('_', 1)[1] if '_' in file_name else file_name
                                with open(att_path, "rb") as f:
                                    st.download_button(
                                        label=f"📄 {display_name}",
                                        data=f,
                                        file_name=display_name,
                                        mime="application/octet-stream",
                                        key=f"dl_{task.id}_{file_name}",
                                        use_container_width=True
                                    )
                            else:
                                st.warning(f"Arquivo não encontrado: {att_path}")
                        
                        st.markdown("</div></div>", unsafe_allow_html=True)

                    updates = sorted(dm.get_task_updates(task.id), key=lambda u: u.timestamp, reverse=True)
                    if "editing_update_id" not in st.session_state:
                        st.session_state.editing_update_id = None
                    
                    st.markdown(
                        f"""
                        <div class='updates-section'>
                            <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;'>
                                <span style='color:#ffffff;font-weight:700;font-size:1rem;'>
                                    💬 Histórico • {task.title[:35]}{'...' if len(task.title) > 35 else ''}
                                </span>
                                <span style='color:#b8b9c0;font-size:0.82rem;background:rgba(255,255,255,0.08);padding:4px 10px;border-radius:12px;'>
                                    {len(updates)} registro(s)
                                </span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    with st.container():
                        with st.form(f"form_inline_update_{task.id}"):
                            new_update_content = st.text_area(
                                "Novo update",
                                placeholder="Descreva o que aconteceu nesta atividade...",
                                height=80,
                                key=f"txt_upd_{task.id}",
                                label_visibility="collapsed"
                            )
                            col_submit, col_close = st.columns([0.7, 0.3])
                            with col_submit:
                                submitted = st.form_submit_button("📤 Publicar", type="primary", use_container_width=True)
                            with col_close:
                                close_btn = st.form_submit_button("▲ Fechar", use_container_width=True)
                            
                            if submitted and new_update_content.strip():
                                upd = TaskUpdate(task_id=task.id, content=new_update_content.strip())
                                dm.add_update(upd)
                                st.success("Update adicionado!")
                                time.sleep(0.3)
                                st.rerun()
                            
                            if close_btn:
                                st.session_state.expanded_task_updates.discard(task.id)
                                st.rerun()
                        
                        if updates:
                            for u in updates:
                                ts_raw = u.timestamp.replace(" (editado)", "")
                                edited_tag = " (editado)" if "(editado)" in u.timestamp else ""
                                try:
                                    ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") + edited_tag
                                except:
                                    ts = u.timestamp
                                
                                if st.session_state.editing_update_id == u.id:
                                    with st.form(f"edit_form_{u.id}"):
                                        edited_content = st.text_area(
                                            "Editar update",
                                            value=u.content,
                                            height=80,
                                            key=f"edit_txt_{u.id}",
                                            label_visibility="collapsed"
                                        )
                                        col_save, col_cancel = st.columns(2)
                                        with col_save:
                                            if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                                                if edited_content.strip():
                                                    dm.edit_update(u.id, edited_content.strip())
                                                    st.session_state.editing_update_id = None
                                                    st.success("Update editado!")
                                                    time.sleep(0.3)
                                                    st.rerun()
                                        with col_cancel:
                                            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                                st.session_state.editing_update_id = None
                                                st.rerun()
                                else:
                                    col_content, col_actions = st.columns([0.88, 0.12])
                                    with col_content:
                                        st.markdown(
                                            f"""
                                            <div class='update-item'>
                                                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
                                                    <span style='color:#579bfc;font-weight:700;font-size:0.88rem;'>👤 {u.user}</span>
                                                    <span style='color:#9699a6;font-size:0.75rem;'>📅 {ts}</span>
                                                </div>
                                                <div style='color:#ffffff;font-size:0.9rem;line-height:1.5;'>{u.content}</div>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )
                                    with col_actions:
                                        btn_col1, btn_col2 = st.columns(2)
                                        with btn_col1:
                                            if st.button("✏️", key=f"edit_{u.id}", help="Editar", use_container_width=True):
                                                st.session_state.editing_update_id = u.id
                                                st.rerun()
                                        with btn_col2:
                                            if st.button("🗑️", key=f"del_{u.id}", help="Excluir", use_container_width=True):
                                                dm.delete_update(u.id)
                                                st.success("Update excluído!")
                                                time.sleep(0.3)
                                                st.rerun()
                        else:
                            st.markdown(
                                """
                                <div style='text-align:center;padding:20px;color:#9699a6;'>
                                    <p style='margin:0;font-size:0.85rem;'>Nenhum update ainda. Seja o primeiro a comentar!</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
            
            st.markdown("<div style='margin-bottom:30px;'></div>", unsafe_allow_html=True)


# ==========================================
# CALENDÁRIO / KANBAN / LINHA DO TEMPO
# ==========================================

class CalendarView:
    @staticmethod
    def _month_matrix(year: int, month: int) -> List[List[int]]:
        return calendar.monthcalendar(year, month)
    
    @staticmethod
    def _tasks_on(tasks: List[Task], d: str) -> List[Task]:
        return [t for t in tasks if t.due_date == d]
    
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        now = datetime.now()
        c1, c2, _ = st.columns([2, 2, 8])
        with c1:
            month = st.selectbox("Mês", list(range(1, 13)), index=now.month - 1, format_func=lambda x: MESES_PT[x])
        with c2:
            year = st.number_input("Ano", min_value=2020, max_value=2030, value=now.year)
        
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        now = datetime.now()
        c1, c2, _ = st.columns([2, 2, 8])
        with c1:
            month = st.selectbox("Mês", list(range(1, 13)), index=now.month - 1, format_func=lambda x: MESES_PT[x])
        with c2:
            year = st.number_input("Ano", min_value=2020, max_value=2030, value=now.year)
        
        # Legenda de Prioridade
        st.markdown(
            """
            <div style='display:flex;gap:20px;margin:15px 0;padding:12px 18px;background:var(--monday-bg-light);
                        border-radius:8px;border:1px solid var(--monday-border);'>
                <span style='color:#9699a6;font-weight:600;font-size:0.85rem;'>Prioridade:</span>
                <div style='display:flex;align-items:center;gap:6px;'>
                    <span style='width:12px;height:12px;background:#579bfc;border-radius:3px;'></span>
                    <span style='color:#579bfc;font-size:0.8rem;font-weight:600;'>Baixa</span>
                </div>
                <div style='display:flex;align-items:center;gap:6px;'>
                    <span style='width:12px;height:12px;background:#fdab3d;border-radius:3px;'></span>
                    <span style='color:#fdab3d;font-size:0.8rem;font-weight:600;'>Média</span>
                </div>
                <div style='display:flex;align-items:center;gap:6px;'>
                    <span style='width:12px;height:12px;background:#e44258;border-radius:3px;'></span>
                    <span style='color:#e44258;font-size:0.8rem;font-weight:600;'>Alta</span>
                </div>
                <div style='display:flex;align-items:center;gap:6px;'>
                    <span style='width:12px;height:12px;background:#df2f4a;border-radius:3px;'></span>
                    <span style='color:#df2f4a;font-size:0.8rem;font-weight:600;'>Urgente</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        matrix = cls._month_matrix(year, month)
        weekdays = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]
        
        html = "<div class='monday-calendar'><div class='calendar-header'>"
        for d in weekdays:
            html += f"<div class='day-header'>{d}</div>"
        html += "</div><div class='calendar-grid'>"
        
        today = datetime.now()
        
        for week in matrix:
            for day in week:
                if day == 0:
                    html += "<div class='calendar-day empty'></div>"
                    continue
                d_str = f"{year}-{month:02d}-{day:02d}"
                day_tasks = cls._tasks_on(tasks, d_str)
                is_today = day == today.day and month == today.month and year == today.year
                t_class = "today" if is_today else ""
                has_many = len(day_tasks) > 3
                hover_class = "has-many" if has_many else ""
                html += f"<div class='calendar-day {t_class} {hover_class}'>"
                html += f"<div class='day-number {t_class}'>{day}</div>"
                
                # Detectar se é administrador/gestor para exibir o analista
                current_mat = st.session_state.get("current_user", "2949400")
                is_admin_mode = current_mat in ["2949400", "2484901", "GESTAO"]

                # Container de tarefas visíveis (primeiras 3)
                html += "<div class='calendar-tasks-visible'>"
                for t in day_tasks[:3]:
                    info = t.get_category_info()
                    prio_color = PRIORITY_CONFIG[t.priority]['color']
                    title = t.title[:20] + "..." if len(t.title) > 20 else t.title
                    
                    # Badge do Analista (3 Primeiras Letras) para Gestão
                    ans_badge = ""
                    if is_admin_mode:
                        display_name = t.responsible[:3].upper()
                        ans_badge = f"<span style='background:rgba(255,255,255,0.15);padding:1px 4px;border-radius:3px;margin-right:5px;font-size:0.55rem;font-weight:800;color:#fff;border:1px solid rgba(255,255,255,0.1);'>{display_name}</span>"
                    
                    html += f"<div class='task-item' style='border-left-color:{prio_color};background:{PRIORITY_CONFIG[t.priority]['bg']};'>{ans_badge}{info['icon']} {title}</div>"
                if has_many:
                    html += f"<div class='task-more'>+{len(day_tasks)-3} mais ⤵</div>"
                html += "</div>"
                
                # Tooltip expandido com todas as tarefas (só aparece no hover)
                if has_many:
                    html += "<div class='calendar-tooltip'>"
                    html += f"<div class='tooltip-header'>📅 {day:02d}/{month:02d} - {len(day_tasks)} atividades</div>"
                    for t in day_tasks:
                        info = t.get_category_info()
                        prio_color = PRIORITY_CONFIG[t.priority]['color']
                        title = t.title[:35] + "..." if len(t.title) > 35 else t.title
                        status = t.status
                        
                        # Label do Analista no Tooltip
                        ans_label = f"<span style='font-size:0.65rem;color:#94a3b8;margin-right:6px;font-weight:700;'>[{t.responsible.split()[0].upper()}]</span>" if is_admin_mode else ""
                        
                        html += f"<div class='tooltip-task' style='border-left-color:{prio_color};'>"
                        html += f"<span class='tooltip-icon'>{info['icon']}</span>"
                        html += f"<span class='tooltip-title'>{ans_label}{title}</span>"
                        html += f"<span class='tooltip-status' style='color:{STATUS_CONFIG[status]['color']};'>{status}</span>"
                        html += "</div>"
                    html += "</div>"
                
                html += "</div>"
        
        html += "</div></div>"
        st.markdown(html, unsafe_allow_html=True)


class CategoryListView:
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        # === CSS EXCLUSIVO DA PÁGINA ===
        st.markdown("""
        <style>
        .cat-page-header {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
            border-radius: 20px; padding: 28px 32px; margin-bottom: 28px;
            border: 1px solid rgba(99, 102, 241, 0.25);
            position: relative; overflow: hidden;
        }
        .cat-page-header::before {
            content: ''; position: absolute; top: -50%; right: -20%; width: 300px; height: 300px;
            background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
            border-radius: 50%;
        }
        .cat-page-header h2 { color: #f8fafc; margin: 0 0 6px 0; font-size: 1.4rem; font-weight: 800; position: relative; z-index: 1; }
        .cat-page-header p { color: #a5b4fc; margin: 0; font-size: 0.88rem; position: relative; z-index: 1; }
        .cat-kpi-row { display: flex; gap: 16px; margin-bottom: 28px; }
        .cat-kpi-item {
            flex: 1; background: rgba(30, 27, 75, 0.5); border-radius: 14px; padding: 18px 20px;
            border: 1px solid rgba(99, 102, 241, 0.12); text-align: center;
            transition: all 0.3s ease;
        }
        .cat-kpi-item:hover { border-color: rgba(99, 102, 241, 0.4); transform: translateY(-2px); box-shadow: 0 8px 25px rgba(99,102,241,0.15); }
        .cat-kpi-number { font-size: 1.8rem; font-weight: 800; line-height: 1; margin-bottom: 4px; }
        .cat-kpi-label { font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
        .cat-section {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
            border-radius: 16px; margin-bottom: 20px; overflow: hidden;
            border: 1px solid rgba(255,255,255,0.06);
            transition: all 0.3s ease;
        }
        .cat-section:hover { border-color: rgba(255,255,255,0.12); box-shadow: 0 8px 30px rgba(0,0,0,0.2); }
        .cat-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 24px; cursor: pointer;
        }
        .cat-header-left { display: flex; align-items: center; gap: 14px; }
        .cat-icon-box {
            width: 42px; height: 42px; border-radius: 12px; display: flex;
            align-items: center; justify-content: center; font-size: 1.2rem;
        }
        .cat-name { color: #f1f5f9; font-weight: 700; font-size: 1.05rem; }
        .cat-header-right { display: flex; align-items: center; gap: 12px; }
        .cat-badge {
            padding: 4px 12px; border-radius: 20px; font-size: 0.72rem;
            font-weight: 700; letter-spacing: 0.5px;
        }
        .cat-progress-bar {
            width: 120px; height: 6px; background: rgba(255,255,255,0.08);
            border-radius: 3px; overflow: hidden;
        }
        .cat-progress-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
        .cat-body { padding: 0 24px 20px 24px; }
        .cat-task-item {
            display: flex; align-items: center; gap: 14px; padding: 14px 16px;
            background: rgba(255,255,255,0.025); border-radius: 12px;
            margin-bottom: 10px; border-left: 4px solid transparent;
            transition: all 0.2s ease;
        }
        .cat-task-item:hover { background: rgba(255,255,255,0.05); transform: translateX(4px); }
        .cat-task-status-dot {
            width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
        }
        .cat-task-info { flex: 1; min-width: 0; }
        .cat-task-title {
            color: #e2e8f0; font-size: 0.88rem; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .cat-task-meta {
            display: flex; gap: 10px; align-items: center; margin-top: 4px;
        }
        .cat-task-meta span {
            font-size: 0.72rem; color: #64748b; font-weight: 500;
        }
        .cat-task-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
        .cat-prio-tag {
            padding: 3px 10px; border-radius: 6px; font-size: 0.65rem;
            font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .cat-date-tag {
            color: #94a3b8; font-size: 0.78rem; font-weight: 600;
        }
        .cat-empty {
            text-align: center; padding: 30px 20px; color: #475569;
            font-size: 0.85rem; font-style: italic;
        }
        .cat-empty-icon { font-size: 2rem; margin-bottom: 8px; display: block; }
        .cat-history-item {
            display: flex; align-items: center; gap: 12px; padding: 10px 14px;
            background: rgba(16, 185, 129, 0.05); border-radius: 10px;
            margin-bottom: 6px; border-left: 3px solid #10b981;
        }
        .cat-history-title {
            color: #94a3b8; font-size: 0.82rem; text-decoration: line-through;
            flex: 1;
        }
        .cat-history-date { color: #475569; font-size: 0.72rem; font-weight: 500; }
        .cat-filter-bar {
            display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;
        }
        </style>
        """, unsafe_allow_html=True)

        # === DADOS ===
        cats = st.session_state.get("categories", DEFAULT_CATEGORY_OPTIONS)
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        # Agrupar tarefas por categoria
        tasks_by_cat: Dict[str, List[Task]] = {}
        for cat_key, cat_info in cats.items():
            cat_name = cat_info["name"]
            tasks_by_cat[cat_name] = [t for t in tasks if t.category == cat_name or t.category == cat_key]

        # Stats globais
        total_pending = len([t for t in tasks if t.status in ["Pendente", "Em Andamento", "Para Revisão"]])
        total_done = len([t for t in tasks if t.status == "Concluído"])
        total_overdue = len([t for t in tasks if t.due_date < today_str and t.status != "Concluído"])
        cats_with_pending = len([c for c, tl in tasks_by_cat.items() if any(t.status != "Concluído" for t in tl)])

        # === HEADER ===
        st.markdown(f"""
        <div class="cat-page-header">
            <h2>📂 Visão por Categorias</h2>
            <p>Gerencie suas atividades organizadas por tema — ideal para acompanhamento com a gestão</p>
        </div>
        """, unsafe_allow_html=True)

        # === KPIs ===
        st.markdown(f"""
        <div class="cat-kpi-row">
            <div class="cat-kpi-item">
                <div class="cat-kpi-number" style="color: #818cf8;">{len(cats)}</div>
                <div class="cat-kpi-label">Categorias</div>
            </div>
            <div class="cat-kpi-item">
                <div class="cat-kpi-number" style="color: #fbbf24;">{total_pending}</div>
                <div class="cat-kpi-label">Pendentes</div>
            </div>
            <div class="cat-kpi-item">
                <div class="cat-kpi-number" style="color: #f87171;">{total_overdue}</div>
                <div class="cat-kpi-label">Atrasadas</div>
            </div>
            <div class="cat-kpi-item">
                <div class="cat-kpi-number" style="color: #34d399;">{total_done}</div>
                <div class="cat-kpi-label">Concluídas</div>
            </div>
            <div class="cat-kpi-item">
                <div class="cat-kpi-number" style="color: #fb923c;">{cats_with_pending}</div>
                <div class="cat-kpi-label">Temas Ativos</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # === FILTRO DE VISUALIZAÇÃO ===
        fc1, fc2, fc3 = st.columns([0.3, 0.3, 0.4])
        with fc1:
            view_mode = st.selectbox(
                "Exibir", ["⏳ Pendentes & Em Andamento", "📋 Todas", "✅ Apenas Concluídas"],
                index=0, label_visibility="collapsed", key="cat_view_mode"
            )
        with fc2:
            sort_mode = st.selectbox(
                "Ordenar", ["📊 Mais pendentes primeiro", "🔤 Nome A-Z", "🔥 Mais atrasadas"],
                index=0, label_visibility="collapsed", key="cat_sort_mode"
            )

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # === RENDERIZAÇÃO DAS CATEGORIAS ===
        # Preparar lista ordenada
        cat_list = []
        for cat_key, cat_info in cats.items():
            cat_name = cat_info["name"]
            cat_tasks = tasks_by_cat.get(cat_name, [])
            pending = [t for t in cat_tasks if t.status in ["Pendente", "Em Andamento", "Para Revisão"]]
            done = [t for t in cat_tasks if t.status == "Concluído"]
            overdue = [t for t in pending if t.due_date < today_str]
            cat_list.append({
                "key": cat_key, "info": cat_info, "name": cat_name,
                "tasks": cat_tasks, "pending": pending, "done": done, "overdue": overdue
            })

        # Ordenar
        if "Mais pendentes" in sort_mode:
            cat_list.sort(key=lambda c: len(c["pending"]), reverse=True)
        elif "Nome" in sort_mode:
            cat_list.sort(key=lambda c: c["name"])
        elif "atrasadas" in sort_mode:
            cat_list.sort(key=lambda c: len(c["overdue"]), reverse=True)

        for cat_data in cat_list:
            info = cat_data["info"]
            cat_name = cat_data["name"]
            cat_tasks = cat_data["tasks"]
            pending = cat_data["pending"]
            done = cat_data["done"]
            overdue = cat_data["overdue"]
            color = info.get("color", "#6366f1")
            icon = info.get("icon", "📋")
            bg = info.get("bg", "#2a3d5a")

            total_cat = len(cat_tasks)
            done_count = len(done)
            pend_count = len(pending)
            progress_pct = int((done_count / total_cat * 100)) if total_cat > 0 else 0

            # Filtrar tarefas visíveis com base no modo
            if "Pendentes" in view_mode:
                visible_tasks = sorted(pending, key=lambda t: (0 if t.priority == "Urgente" else 1 if t.priority == "Alta" else 2 if t.priority == "Média" else 3, t.due_date))
                show_history = False
            elif "Concluídas" in view_mode:
                visible_tasks = []
                show_history = True
            else:
                visible_tasks = sorted(cat_tasks, key=lambda t: (0 if t.status != "Concluído" else 1, t.due_date))
                show_history = False

            # Badge de status
            if pend_count == 0:
                badge_html = f'<span class="cat-badge" style="background: rgba(16,185,129,0.15); color: #34d399;">✅ Em dia</span>'
            elif len(overdue) > 0:
                badge_html = f'<span class="cat-badge" style="background: rgba(239,68,68,0.15); color: #f87171;">🔴 {len(overdue)} atrasada{"s" if len(overdue) > 1 else ""}</span>'
            else:
                badge_html = f'<span class="cat-badge" style="background: rgba(251,191,36,0.15); color: #fbbf24;">⏳ {pend_count} pendente{"s" if pend_count > 1 else ""}</span>'

            # Progress bar color
            prog_color = "#10b981" if progress_pct >= 70 else "#f59e0b" if progress_pct >= 30 else "#6366f1"

            # === HEADER DA CATEGORIA (HTML) ===
            header_html = f"""
            <div class="cat-section">
                <div class="cat-header">
                    <div class="cat-header-left">
                        <div class="cat-icon-box" style="background: {color}20; border: 1px solid {color}40;">
                            {icon}
                        </div>
                        <div>
                            <div class="cat-name">{cat_name}</div>
                            <div style="font-size: 0.72rem; color: #64748b; margin-top: 2px;">
                                {total_cat} atividade{"s" if total_cat != 1 else ""} • {done_count} concluída{"s" if done_count != 1 else ""}
                            </div>
                        </div>
                    </div>
                    <div class="cat-header-right">
                        {badge_html}
                        <div class="cat-progress-bar">
                            <div class="cat-progress-fill" style="width: {progress_pct}%; background: {prog_color};"></div>
                        </div>
                        <span style="color: #64748b; font-size: 0.72rem; font-weight: 700; min-width: 35px; text-align: right;">{progress_pct}%</span>
                    </div>
                </div>
            """

            # === CORPO: TAREFAS ===
            if visible_tasks:
                header_html += '<div class="cat-body">'
                for t in visible_tasks:
                    pc = PRIORITY_CONFIG.get(t.priority, {'color': '#94a3b8', 'bg': '#3d3d4a'})
                    sc = STATUS_CONFIG.get(t.status, {'text': '#94a3b8', 'bg': '#3d3d4a'})
                    due_dt = datetime.strptime(t.due_date, "%Y-%m-%d")
                    due_str = due_dt.strftime("%d/%m")
                    days_diff = (due_dt - today).days

                    # Status dot color
                    dot_colors = {"Pendente": "#64748b", "Em Andamento": "#6366f1", "Para Revisão": "#a855f7", "Concluído": "#10b981"}
                    dot_color = dot_colors.get(t.status, "#64748b")

                    # Date urgency styling
                    if t.status == "Concluído":
                        date_color = "#10b981"
                        date_label = "✅"
                    elif days_diff < 0:
                        date_color = "#ef4444"
                        date_label = f"🔴 {abs(days_diff)}d atrás"
                    elif days_diff == 0:
                        date_color = "#f59e0b"
                        date_label = "⚡ Hoje"
                    elif days_diff <= 3:
                        date_color = "#fb923c"
                        date_label = f"⏰ {days_diff}d"
                    else:
                        date_color = "#94a3b8"
                        date_label = f"📅 {due_str}"

                    header_html += f"""
                    <div class="cat-task-item" style="border-left-color: {color};">
                        <div class="cat-task-status-dot" style="background: {dot_color}; box-shadow: 0 0 8px {dot_color}60;"></div>
                        <div class="cat-task-info">
                            <div class="cat-task-title">{t.title}</div>
                            <div class="cat-task-meta">
                                <span>👤 {t.responsible.split()[0] if t.responsible else 'N/A'}</span>
                                <span>•</span>
                                <span style="color: {sc.get('text', '#94a3b8')};">{t.status}</span>
                            </div>
                        </div>
                        <div class="cat-task-right">
                            <span class="cat-prio-tag" style="background: {pc['color']}15; color: {pc['color']}; border: 1px solid {pc['color']}30;">{t.priority}</span>
                            <span class="cat-date-tag" style="color: {date_color};">{date_label}</span>
                        </div>
                    </div>
                    """
                header_html += '</div>'
            elif not show_history:
                header_html += f"""
                <div class="cat-body">
                    <div class="cat-empty">
                        <span class="cat-empty-icon">🎉</span>
                        Tudo em dia nesta categoria!
                    </div>
                </div>
                """

            header_html += '</div>'  # close cat-section
            st.markdown(header_html, unsafe_allow_html=True)

            # === BOTÕES INTERATIVOS (Streamlit widgets) ===
            btn_cols = st.columns([0.25, 0.25, 0.5])
            with btn_cols[0]:
                if st.button(f"➕ Nova Atividade", key=f"cat_add_{cat_data['key']}", use_container_width=True):
                    st.session_state.show_modal = True
                    st.session_state.prefill_category = cat_name
            with btn_cols[1]:
                hist_key = f"cat_hist_{cat_data['key']}"
                if hist_key not in st.session_state:
                    st.session_state[hist_key] = False
                if st.button(
                    f"{'🔽 Fechar' if st.session_state[hist_key] else '📜 Histórico'} ({done_count})",
                    key=f"cat_hist_btn_{cat_data['key']}",
                    use_container_width=True
                ):
                    st.session_state[hist_key] = not st.session_state[hist_key]
                    st.rerun()

            # === HISTÓRICO (Concluídas) ===
            if st.session_state.get(f"cat_hist_{cat_data['key']}", False) and done:
                hist_html = '<div style="padding: 0 0 16px 0;">'
                for t in sorted(done, key=lambda x: x.due_date, reverse=True)[:10]:
                    due_str = datetime.strptime(t.due_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                    hist_html += f"""
                    <div class="cat-history-item">
                        <span style="color: #10b981; font-size: 0.9rem;">✅</span>
                        <span class="cat-history-title">{t.title}</span>
                        <span class="cat-history-date">👤 {t.responsible.split()[0] if t.responsible else ''} • {due_str}</span>
                    </div>
                    """
                if len(done) > 10:
                    hist_html += f'<div style="text-align: center; color: #475569; font-size: 0.75rem; padding: 8px;">... e mais {len(done) - 10} concluídas</div>'
                hist_html += '</div>'
                st.markdown(hist_html, unsafe_allow_html=True)

            st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)




class RequisiçõesView:
    @staticmethod
    def load_data():
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.join(base_dir, "BASE.BOLSAS", "Cronograma_Bolsas_Com_Subetapas.xlsx")
        
        if not os.path.exists(abs_path):
            st.warning(f"Arquivo não encontrado: {abs_path}")
            return pd.DataFrame()
        try:
            df = pd.read_excel(abs_path)
            df.columns = [c.strip().upper() for c in df.columns]
            
            # Normalizar nome da coluna Etapa caso o usuário tenha renomeado
            if 'ETAPA / SUB-ETAPA' in df.columns:
                df = df.rename(columns={'ETAPA / SUB-ETAPA': 'ETAPA'})
            
            if 'ETAPA' in df.columns:
                df['ETAPA'] = df['ETAPA'].ffill()
            return df
        except Exception as e:
            st.error(f"Erro ao ler o arquivo Excel: {e}")
            return pd.DataFrame()

    @staticmethod
    def save_data(new_row):
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.join(base_dir, "BASE.BOLSAS", "Cronograma_Bolsas_Com_Subetapas.xlsx")
        
        try:
            if os.path.exists(abs_path):
                df = pd.read_excel(abs_path)
            else:
                df = pd.DataFrame(columns=['Tema / Quadro', 'ETAPA', 'Descrição / Sub-etapa', 'Início', 'Fim'])
            
            # Formatar datas para o padrão Excel esperado (string ou datetime)
            # Vamos manter como string d/m/Y se for o padrão do usuário ou deixar o pandas lidar
            
            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            new_df.to_excel(abs_path, index=False)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar no Excel: {e}")
            return False

    @classmethod
    def render(cls, tasks=None):
        df = cls.load_data()
        st.markdown("""
        <style>
        .timeline-header-premium {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
            color: white; padding: 25px 35px; border-radius: 20px;
            margin-bottom: 30px; display: flex; flex-direction: column; gap: 20px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2); border: 1px solid rgba(255,255,255,0.08);
        }
        .header-top-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
        .progress-container-strategic { width: 100%; background: rgba(255,255,255,0.05); height: 8px; border-radius: 10px; overflow: hidden; margin-top: 5px; }
        .progress-bar-strategic { height: 100%; background: linear-gradient(90deg, #6366f1, #a855f7); border-radius: 10px; transition: width 1s ease-in-out; }
        .progress-label-strategic { font-size: 0.75rem; color: #94a3b8; font-weight: 700; margin-top: 10px; display: flex; justify-content: space-between; }
        
        .month-card-premium {
            background: #ffffff; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05);
            overflow: hidden; border: 1px solid #f1f5f9; margin-bottom: 30px; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .month-card-premium:hover { transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .month-card-header {
            background: #0f172a; color: #f8fafc; padding: 16px 24px;
            display: flex; justify-content: space-between; align-items: center; font-weight: 800;
            text-transform: uppercase; font-size: 0.95rem; letter-spacing: 1px;
        }
        .calendar-table-premium { width: 100%; border-collapse: collapse; background: white; table-layout: fixed; }
        .calendar-table-premium th { padding: 15px 5px; text-align: center; color: #64748b; font-size: 0.7rem; font-weight: 800; border-bottom: 2px solid #f8fafc; text-transform: uppercase; }
        .calendar-table-premium td { height: 125px; border: 1px solid #f1f5f9; vertical-align: top; padding: 10px; position: relative; transition: background 0.2s; }
        .calendar-table-premium td:hover { background: #fcfdfe; }
        .day-label { color: #94a3b8; font-size: 0.9rem; font-weight: 800; margin-bottom: 8px; display: block; }
        .today-cell { background: #f0f7ff !important; }
        .today-cell .day-label { color: #3b82f6; }
        
        .timeline-bar-premium {
            height: 22px; border-radius: 6px; margin-bottom: 5px; color: white;
            font-size: 0.5rem; font-weight: 700; padding: 0 8px; 
            display: block; line-height: 22px; text-align: center; cursor: pointer;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            border: 1px solid rgba(255,255,255,0.1);
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative; z-index: 1;
        }
        .timeline-bar-premium:hover {
            transform: scale(1.05);
            z-index: 100 !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        }
        .bg-green { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .bg-blue { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
        .bg-indigo { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }
        .bg-orange { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        .bg-purple { background: linear-gradient(135deg, #a855f7 0%, #9333ea 100%); }
        .bg-rose { background: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%); }
        
        /* OTIMIZAÇÃO PARA PDF E IMPRESSÃO PAISAGEM */
        @media print {
            @page { size: landscape; margin: 10mm; }
            
            /* Esconder elementos de interface */
            header, footer, [data-testid="stSidebar"], .stButton, .stRadio, .stSelectbox, .stToggle, 
            [data-testid="stHeader"], .stMarkdown button, [data-testid="stVerticalBlock"] > div:has(button) {
                display: none !important;
            }
            
            /* Ajustar containers */
            .main .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
            
            /* Cabeçalho de Progresso (Dashboard) */
            .timeline-header-premium { 
                box-shadow: none !important; 
                border: 2px solid #1e293b !important;
                background: #0f172a !important; 
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                width: 100% !important;
                margin-bottom: 20px !important;
                page-break-inside: avoid;
            }
            
            /* Forçar cores nas barras */
            .timeline-bar-premium, .progress-bar-strategic, [style*="background"] { 
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            
            /* Ajustar Grade de Meses para Paisagem */
            [data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                gap: 10px !important;
            }
            
            .month-card-premium { 
                break-inside: avoid;
                box-shadow: none !important;
                border: 1px solid #e2e8f0 !important;
                width: 100% !important;
                margin-bottom: 15px !important;
            }
            
            .calendar-table-premium th { padding: 8px 4px !important; font-size: 0.6rem !important; }
            .calendar-table-premium td { height: auto !important; min-height: 80px !important; padding: 8px !important; }
            .day-label { font-size: 0.8rem !important; margin-bottom: 4px !important; }
            .timeline-bar-premium { font-size: 0.5rem !important; height: 18px !important; line-height: 18px !important; padding: 0 8px !important; margin-bottom: 4px !important; }
            .month-card-header { padding: 12px 20px !important; font-size: 0.85rem !important; }
            
            body { background: white !important; color: black !important; }
        }
        </style>
        """, unsafe_allow_html=True)
        
        now = datetime.now().date()
        
        if df.empty:
            st.warning("⚠️ Planilha não encontrada ou vazia em BASE.BOLSAS.")
            return

        # Filtro de Programa
        program_col = 'TEMA / QUADRO'
        # Limpar emojis de programas existentes no Excel para manter padrão
        def clean_emoji(t):
            import re
            return re.sub(r'[^\w\s\(\)\[\]\-\/\.\,]', '', str(t)).strip()
        
        df[program_col] = df[program_col].apply(clean_emoji)
        programs = ["Todos"] + sorted(df[program_col].dropna().unique().tolist())
        
        c_filter, c_mode, c_focus, c_btn = st.columns([0.2, 0.25, 0.15, 0.4])
        with c_filter:
            selected_program = st.selectbox("🎯 Filtrar", programs, index=0)
        
        display_mode = "Calendário Unificado"
        resumo_mode = False
        if selected_program == "Todos":
            with c_mode:
                display_mode = st.radio("📊 Modo", ["Unificado", "Lista", "Resumo"], horizontal=True, help="Unificado: Grid de meses | Lista: Um programa por vez | Resumo: Apenas etapas principais")
                if display_mode == "Resumo":
                    resumo_mode = True
                    display_mode = "Calendário Unificado"
        
        with c_focus:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            focus_mode = st.toggle("🔍 Ampliar", value=False, help="Maximiza o calendário para ver detalhes")

        with c_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Cadastrar", use_container_width=True, type="primary"):
                    cls.show_cadastrar_modal([p for p in programs if p != "Todos"])
            with col2:
                if st.button("✏️ Gerenciar", use_container_width=True):
                    cls.show_manage_modal(df)
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("📄 Gerar PDF / Imprimir", use_container_width=True):
                st.components.v1.html(
                    """
                    <script>
                        window.parent.print();
                    </script>
                    """,
                    height=0,
                    width=0
                )

        # Filtrar o DF para o programa selecionado
        if selected_program == "Todos":
            prog_df = df.copy()
            active_title = "Visão Geral Estratégica"
        else:
            prog_df = df[df[program_col] == selected_program].copy()
            active_title = selected_program

        prog_df['dt_inicio'] = pd.to_datetime(prog_df['INÍCIO'], dayfirst=True).dt.date
        prog_df['dt_fim'] = pd.to_datetime(prog_df['FIM'], dayfirst=True).dt.date
        
        # Cálculo de Progresso (Geral e Individual)
        progresso_por_programa = []
        total_p = 0
        
        if not df.empty:
            # Calcular progresso individual para cada programa
            unique_progs = sorted(df[program_col].dropna().unique().tolist())
            for p_name in unique_progs:
                p_df = df[df[program_col] == p_name].copy()
                p_df['dt_inicio'] = pd.to_datetime(p_df['INÍCIO'], dayfirst=True).dt.date
                p_df['dt_fim'] = pd.to_datetime(p_df['FIM'], dayfirst=True).dt.date
                
                ps_start = p_df['dt_inicio'].min()
                ps_end = p_df['dt_fim'].max()
                
                p_percent = 0
                if ps_start and ps_end:
                    p_total_days = (ps_end - ps_start).days
                    p_elapsed = (now - ps_start).days
                    if p_total_days > 0:
                        p_percent = max(0, min(100, int((p_elapsed / p_total_days) * 100)))
                    elif now >= ps_end:
                        p_percent = 100
                
                # Definir cor da barra
                p_color = "#10b981" if "Bolsas" in p_name else ("#3b82f6" if "Incentivo" in p_name else ("#4f46e5" if "Estágio" in p_name else "#6366f1"))
                progresso_por_programa.append({"nome": p_name, "percent": p_percent, "color": p_color})

            # Calcular progresso geral (do que está sendo exibido)
            p_start = prog_df['dt_inicio'].min()
            p_end = prog_df['dt_fim'].max()
            if p_start and p_end:
                total_days = (p_end - p_start).days
                elapsed_days = (now - p_start).days
                if total_days > 0:
                    total_p = max(0, min(100, int((elapsed_days / total_days) * 100)))
                elif now >= p_end:
                    total_p = 100

        # Render Header com Progresso
        mes_atual_extenso = MESES_PT[datetime.now().month]
        data_brasileira = f"{datetime.now().day} de {mes_atual_extenso}, {datetime.now().year}"

        # Título dinâmico
        if selected_program == "Todos":
            title_html = f"""<div>
<h2 style="margin: 0; color: white; font-size: 1.4rem; font-weight: 900; letter-spacing: -0.5px;">Cronograma Consolidado</h2>
<p style="margin: 0; color: #94a3b8; font-size: 0.9rem; font-weight: 500;">Monitoramento múltiplo de programas estratégico</p>
</div>"""
            # Gerar barras de progresso múltiplas
            bars_html = ""
            for p_info in progresso_por_programa:
                bars_html += f"""
<div style="margin-bottom: 12px;">
    <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #cbd5e1; font-weight: 800; margin-bottom: 4px;">
        <span>{p_info['nome'].upper()}</span>
        <span>{p_info['percent']}%</span>
    </div>
    <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden;">
        <div style="width: {p_info['percent']}%; height: 100%; background: {p_info['color']}; border-radius: 10px; transition: width 0.8s ease;"></div>
    </div>
</div>"""
            progress_section = f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px 30px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">{bars_html}</div>'
        else:
            title_html = f"""<div>
<h2 style="margin: 0; color: white; font-size: 1.8rem; font-weight: 900; letter-spacing: -0.5px;">{active_title}</h2>
<p style="margin: 0; color: #94a3b8; font-size: 1rem; font-weight: 500;">Cronograma Individual de Programa</p>
</div>"""
            progress_section = f"""
<div style="width: 100%; margin-top: 15px;">
    <div class="progress-label-strategic">
        <span>STATUS DE FINALIZAÇÃO</span>
        <span>{total_p}% CONCLUÍDO</span>
    </div>
    <div class="progress-container-strategic">
        <div class="progress-bar-strategic" style="width: {total_p}%;"></div>
    </div>
</div>"""

        st.markdown(f"""<div class="timeline-header-premium">
<div class="header-top-row">
    <div style="display: flex; align-items: center; gap: 20px;">
        <div style="background: white; padding: 10px; border-radius: 14px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">
            <img src="https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png" width="32">
        </div>
        {title_html}
    </div>
    <div style="text-align: right;">
        <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.2); padding: 8px 20px; border-radius: 25px;">
            <span style="color: #818cf8; font-size: 0.9rem; font-weight: 800;">{data_brasileira}</span>
        </div>
    </div>
</div>
{progress_section}

<!-- LEGENDA DE CORES DINÂMICA -->
<div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #10b981;"></div>
        <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">Bolsas</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #3b82f6;"></div>
        <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">Incentivo</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #4f46e5;"></div>
        <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">Estágio</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #ea580c;"></div>
        <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">Indicadores</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #7c3aed;"></div>
        <span style="color: #94a3b8; font-size: 0.7rem; font-weight: 600;">Desenvolvimento</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #e11d48;"></div>
        <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">Instituições</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
        <div style="width: 12px; height: 12px; border-radius: 3px; background: #6b7280;"></div>
        <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">Deskbee</span>
    </div>
</div>
</div>""", unsafe_allow_html=True)

        # Renderizar conforme o modo selecionado
        if display_mode == "Lista":
            # Agrupar por programa e mostrar CALENDÁRIOS completos um embaixo do outro
            st.markdown("<br>", unsafe_allow_html=True)
            for prog_name in sorted(prog_df[program_col].unique()):
                sub_df = prog_df[prog_df[program_col] == prog_name].copy()
                
                st.markdown(f"### {prog_name}")
                
                # Para cada programa, mostrar seu próprio conjunto de meses
                sub_dates = pd.concat([sub_df['dt_inicio'], sub_df['dt_fim']])
                s_min, s_max = sub_dates.min(), sub_dates.max()
                
                s_months = []
                s_curr = s_min.replace(day=1)
                while s_curr <= s_max.replace(day=1):
                    s_months.append((s_curr.year, s_curr.month))
                    if s_curr.month == 12: s_curr = s_curr.replace(year=s_curr.year + 1, month=1)
                    else: s_curr = s_curr.replace(month=s_curr.month + 1)
                
                # Renderizar meses deste programa específico
                step = 1 if focus_mode else 2
                for i in range(0, len(s_months), step):
                    cols = st.columns(step)
                    for j in range(step):
                        if i + j < len(s_months):
                            y, m = s_months[i+j]
                            with cols[j]: 
                                cls.render_month_premium(y, m, sub_df, focus_mode, hide_substeps=resumo_mode)
                st.markdown("---")
        else:
            # MODO CALENDÁRIO UNIFICADO (GRID)
            all_dates = pd.concat([pd.to_datetime(prog_df['INÍCIO'], dayfirst=True), pd.to_datetime(prog_df['FIM'], dayfirst=True)])
            min_date, max_date = all_dates.min(), all_dates.max()
            
            display_months = []
            curr = min_date.replace(day=1)
            while curr <= max_date.replace(day=1):
                display_months.append((curr.year, curr.month))
                if curr.month == 12: curr = curr.replace(year=curr.year + 1, month=1)
                else: curr = curr.replace(month=curr.month + 1)
            
            # Se focus_mode, mostrar 1 por linha, senão 2 por linha
            step = 1 if focus_mode else 2
            for i in range(0, len(display_months), step):
                cols = st.columns(step)
                for j in range(step):
                    if i + j < len(display_months):
                        y, m = display_months[i+j]
                        with cols[j]: 
                            cls.render_month_premium(y, m, prog_df, focus_mode, hide_substeps=resumo_mode)

    @classmethod
    @st.dialog("Gerenciar Atividades", width="large")
    def show_manage_modal(cls, df):
        st.markdown("### ✏️ Editar ou Excluir Atividades")
        
        if df.empty:
            st.info("Nenhuma atividade cadastrada para gerenciar.")
            return

        # Lista de atividades formatada para o selectbox
        activity_options = []
        for idx, row in df.iterrows():
            label = f"[{row['TEMA / QUADRO']}] {row['DESCRIÇÃO / SUB-ETAPA']} ({row['INÍCIO']} - {row['FIM']})"
            activity_options.append((label, idx))
        
        selected_label = st.selectbox("Selecione a atividade para modificar:", [o[0] for o in activity_options])
        selected_idx = next(o[1] for o in activity_options if o[0] == selected_label)
        
        row = df.loc[selected_idx]
        
        with st.form("form_editar_cronograma"):
            col1, col2 = st.columns(2)
            with col1:
                new_prog = st.text_input("Programa:", value=row['TEMA / QUADRO'])
                etapas_validas = ["Etapa 1", "Etapa 2", "Etapa 3", "Etapa 4", "Etapa 5"]
                current_etapa = str(row['ETAPA']).title()
                idx_etapa = etapas_validas.index(current_etapa) if current_etapa in etapas_validas else 0
                new_etapa = st.selectbox("Etapa:", etapas_validas, index=idx_etapa)
            with col2:
                new_desc = st.text_input("Descrição / Sub-etapa:", value=row['DESCRIÇÃO / SUB-ETAPA'])
                c_data1, c_data2 = st.columns(2)
                with c_data1:
                    new_ini = st.date_input("Novo Início:", value=pd.to_datetime(row['INÍCIO'], dayfirst=True).date())
                with c_data2:
                    new_fim = st.date_input("Novo Fim:", value=pd.to_datetime(row['FIM'], dayfirst=True).date())
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                submit_edit = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            with btn_col2:
                submit_delete = st.form_submit_button("🗑️ EXCLUIR ATIVIDADE", use_container_width=True)

            if submit_edit:
                # Carregar o Excel original para manter formatação se possível (ou usar df atual)
                excel_path = os.path.join("BASE.BOLSAS", "Cronograma_Bolsas_Com_Subetapas.xlsx")
                df_full = pd.read_excel(excel_path)
                
                # Atualizar valores
                df_full.loc[selected_idx, 'TEMA / QUADRO'] = new_prog
                df_full.loc[selected_idx, 'ETAPA'] = new_etapa
                df_full.loc[selected_idx, 'DESCRIÇÃO / SUB-ETAPA'] = new_desc
                df_full.loc[selected_idx, 'INÍCIO'] = new_ini.strftime('%d/%m/%Y')
                df_full.loc[selected_idx, 'FIM'] = new_fim.strftime('%d/%m/%Y')
                
                df_full.to_excel(excel_path, index=False)
                st.success("✅ Atividade atualizada com sucesso!")
                time.sleep(1)
                st.rerun()

            if submit_delete:
                excel_path = os.path.join("BASE.BOLSAS", "Cronograma_Bolsas_Com_Subetapas.xlsx")
                df_full = pd.read_excel(excel_path)
                df_full = df_full.drop(selected_idx)
                
                df_full.to_excel(excel_path, index=False)
                st.success("🗑️ Atividade excluída permanentemente!")
                time.sleep(1)
                st.rerun()

    @classmethod
    @st.dialog("Cadastrar Nova Atividade")
    def show_cadastrar_modal(cls, existing_programs):
        # Lista padronizada solicitada pelo usuário (sem emojis)
        standard_programs = [
            "Bolsas de Estudos",
            "Incentivo à Educação (ETEC)",
            "Programa de Estágio",
            "Indicadores da Área",
            "Projeto de Desenvolvimento",
            "Relacionamento com Instituições",
            "Deskbee"
        ]
        
        # Combinar com programas que já existem no Excel
        all_options = sorted(list(set(standard_programs + existing_programs)))

        with st.form("form_novo_cronograma", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                prog = st.selectbox("Programa (Tema / Quadro)", all_options + ["Outro..."])
                if prog == "Outro...":
                    prog = st.text_input("Nome do Novo Programa")
                etapa = st.text_input("Etapa (ex: Etapa 1)", value="Etapa 1")
            
            with col2:
                desc = st.text_input("Descrição / Sub-etapa")
                tipo = st.radio("Tipo de Registro", ["Principal", "Sub-etapa"], horizontal=True)

            c3, c4 = st.columns(2)
            with c3:
                ini = st.date_input("Data de Início", format="DD/MM/YYYY")
            with c4:
                fim = st.date_input("Data de Fim", format="DD/MM/YYYY")
            
            submit = st.form_submit_button("💾 Salvar no Excel", use_container_width=True)
            if submit:
                final_etapa = etapa
                if tipo == "Sub-etapa" and "- SUB-ETAPA" not in etapa.upper():
                    final_etapa = f"{etapa} - Sub-Etapa"

                new_row = {
                    'Tema / Quadro': prog,
                    'ETAPA': final_etapa,
                    'Descrição / Sub-etapa': desc,
                    'Início': ini.strftime('%d/%m/%Y'),
                    'Fim': fim.strftime('%d/%m/%Y')
                }
                if cls.save_data(new_row):
                    st.success("✅ Cadastrado com sucesso! Recarregando...")
                    st.rerun()

    @classmethod
    def render_month_premium(cls, year, month, df, focus_mode=False, hide_substeps=False):
        month_name = MESES_PT[month]
        cal = calendar.monthcalendar(year, month)
        m_start, m_end = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        m_data = df[(df['dt_inicio'] <= m_end) & (df['dt_fim'] >= m_start)].copy()
        
        today = date.today()
        cell_min_height = "120px" if focus_mode else "90px"
        card_class = "month-card-premium" + (" focus-card" if focus_mode else "")

        # Função auxiliar para pegar cores dinamicamente
        def get_colors(prog_name):
            if "Bolsas" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #064e3b 0%, #065f46 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #047857 0%, #10b981 100%)", 
                    "ETAPA 3": "linear-gradient(135deg, #10b981 0%, #34d399 100%)", 
                    "ETAPA 4": "linear-gradient(135deg, #34d399 0%, #6ee7b7 100%)", 
                    "ETAPA 5": "linear-gradient(135deg, #6ee7b7 0%, #a7f3d0 100%)", 
                    "DEFAULT": "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                    "BORDER": "#10b981"
                }
            elif "Incentivo" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)", 
                    "ETAPA 3": "linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #60a5fa 0%, #93c5fd 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #93c5fd 0%, #bfdbfe 100%)",
                    "DEFAULT": "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
                    "BORDER": "#3b82f6"
                }
            elif "Estágio" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #312e81 0%, #3730a3 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #3730a3 0%, #4f46e5 100%)",
                    "ETAPA 3": "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #6366f1 0%, #818cf8 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #818cf8 0%, #a5b4fc 100%)",
                    "DEFAULT": "linear-gradient(135deg, #4f46e5 0%, #3730a3 100%)",
                    "BORDER": "#4f46e5"
                }
            elif "Indicadores" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #7c2d12 0%, #9a3412 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #9a3412 0%, #c2410c 100%)",
                    "ETAPA 3": "linear-gradient(135deg, #c2410c 0%, #ea580c 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #ea580c 0%, #f97316 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #f97316 0%, #fb923c 100%)",
                    "DEFAULT": "linear-gradient(135deg, #ea580c 0%, #9a3412 100%)",
                    "BORDER": "#ea580c"
                }
            elif "Desenvolvimento" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #4c1d95 0%, #5b21b6 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #5b21b6 0%, #6d28d9 100%)",
                    "ETAPA 3": "linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)",
                    "DEFAULT": "linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%)",
                    "BORDER": "#7c3aed"
                }
            elif "Institu" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #881337 0%, #9f1239 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #9f1239 0%, #be123c 100%)",
                    "ETAPA 3": "linear-gradient(135deg, #be123c 0%, #e11d48 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #e11d48 0%, #f43f5e 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #f43f5e 0%, #fb7185 100%)",
                    "DEFAULT": "linear-gradient(135deg, #e11d48 0%, #9f1239 100%)",
                    "BORDER": "#e11d48"
                }
            elif "Deskbee" in str(prog_name):
                return {
                    "ETAPA 1": "linear-gradient(135deg, #1f2937 0%, #374151 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #374151 0%, #4b5563 100%)",
                    "ETAPA 3": "linear-gradient(135deg, #4b5563 0%, #6b7280 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #6b7280 0%, #9ca3af 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #9ca3af 0%, #d1d5db 100%)",
                    "DEFAULT": "linear-gradient(135deg, #4b5563 0%, #171717 100%)",
                    "BORDER": "#4b5563"
                }
            else:
                return {
                    "ETAPA 1": "linear-gradient(135deg, #4338ca 0%, #4f46e5 100%)",
                    "ETAPA 2": "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
                    "ETAPA 3": "linear-gradient(135deg, #6366f1 0%, #818cf8 100%)",
                    "ETAPA 4": "linear-gradient(135deg, #818cf8 0%, #a5b4fc 100%)",
                    "ETAPA 5": "linear-gradient(135deg, #a5b4fc 0%, #c7d2fe 100%)",
                    "DEFAULT": "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                    "BORDER": "#6366f1"
                }

        html = f'<div class="{card_class}"><div class="month-card-header"><span>{month_name}</span><span>{year}</span></div>'
        html += f'<table class="calendar-table-premium"><thead><tr><th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th><th>Dom</th></tr></thead><tbody>'
        
        for week in cal:
            html += "<tr>"
            for d_idx, day in enumerate(week):
                if day == 0: 
                    html += f'<td style="min-height: {cell_min_height};"></td>'
                    continue
                
                curr = date(year, month, day)
                is_today = (curr == today)
                cell_class = "today-cell" if is_today else ""
                
                html += f'<td class="{cell_class}" style="min-height: {cell_min_height};"><div class="day-label">{day}</div>'
                
                # Filtrar tarefas do dia
                d_tasks = m_data[(m_data['dt_inicio'] <= curr) & (m_data['dt_fim'] >= curr)]
                
                # Diferenciar etapas principais e subetapas
                main_col = 'DESCRIÇÃO / SUB-ETAPA'
                prog_col = 'TEMA / QUADRO'
                for _, row in d_tasks.iterrows():
                    name = str(row[main_col]).strip()
                    etapa_val = str(row['ETAPA']).upper()
                    cur_prog = str(row[prog_col])
                    
                    # Identificar se é subetapa pelo texto da ETAPA ou pelo prefixo da DESCRIÇÃO
                    is_substep = ('└─' in name) or ('SUB-ETAPA' in etapa_val) or ('SUB ETAPA' in etapa_val)
                    
                    # Para a cor, usar apenas a parte inicial (ex: ETAPA 1)
                    etapa_key = etapa_val.split('-')[0].strip()
                    
                    # Pegar as cores específicas DESTE programa
                    colors = get_colors(cur_prog)
                    
                    if not is_substep:
                        # Selecionar degradê baseado na etapa específica
                        current_grad = colors.get(etapa_key, colors["DEFAULT"])
                        show_text = (curr == row['dt_inicio'] or day == 1 or d_idx == 0)
                        html += f'<div class="timeline-bar-premium" style="background: {current_grad};" title="[{cur_prog}] {name}">{name if show_text else ""}</div>'
                    elif not hide_substeps:
                        clean_name = name.replace('└─', '').replace('  ', '').strip()
                        border_col = colors.get("BORDER", "#cbd5e1")
                        html += f'<div style="font-size: 0.5rem; color: #374151; background: #f9fafb; border: 1px solid #e5e7eb; border-left: 3px solid {border_col}; border-radius: 4px; padding: 1px 6px; margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 700;" title="[{cur_prog}] {clean_name}">○ {clean_name}</div>'
                
                html += "</td>"
            html += "</tr>"
        st.markdown(html + "</tbody></table></div>", unsafe_allow_html=True)

class ScheduleView:
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                        padding: 30px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); 
                        margin-bottom: 20px; text-align: center;">
                <h1 style="color: white; font-weight: 800; margin: 0; font-size: 2.2rem; letter-spacing: -0.5px;">
                    📅 Cronograma Anual
                </h1>
                <p style="color: #94a3b8; font-size: 1.1rem; margin-top: 10px; opacity: 0.8;">
                    Acompanhamento estratégico de prazos e entregas
                </p>
            </div>
            
            <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 25px; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Prioridades:</span>
                    <span style="width: 10px; height: 10px; border-radius: 50%; background: #579bfc;"></span> <span style="color: #579bfc; font-size: 0.7rem; font-weight: 600;">Baixa</span>
                    <span style="width: 10px; height: 10px; border-radius: 50%; background: #fdab3d;"></span> <span style="color: #fdab3d; font-size: 0.7rem; font-weight: 600;">Média</span>
                    <span style="width: 10px; height: 10px; border-radius: 50%; background: #e44258;"></span> <span style="color: #e44258; font-size: 0.7rem; font-weight: 600;">Alta</span>
                    <span style="width: 10px; height: 10px; border-radius: 50%; background: #df2f4a;"></span> <span style="color: #df2f4a; font-size: 0.7rem; font-weight: 600;">Urgente</span>
                </div>
            </div>
            """, unsafe_allow_html=True
        )

        now = datetime.now()
        current_year = now.year
        
        col_y, col_info, _ = st.columns([2, 3, 7])
        with col_y:
            selected_year = st.selectbox("Selecione o Ano", [current_year - 1, current_year, current_year + 1], index=1, label_visibility="collapsed")
        
        with col_info:
            st.markdown(f"<div style='padding-top: 8px; color: #94a3b8; font-size: 0.9rem; font-weight: 600;'>📅 Visualizando {selected_year}</div>", unsafe_allow_html=True)
        
        # Agrupar tarefas por mês
        tasks_by_month = {m: [] for m in range(1, 13)}
        for t in tasks:
            try:
                dt = datetime.strptime(t.due_date, "%Y-%m-%d")
                if dt.year == selected_year:
                    tasks_by_month[dt.month].append(t)
            except:
                continue

        # Layout em Grid (4 colunas x 3 linhas para os 12 meses)
        months_per_row = 4
        for row in range(3):
            cols = st.columns(months_per_row)
            for col_idx in range(months_per_row):
                month_num = row * months_per_row + col_idx + 1
                month_name = MESES_PT[month_num]
                month_tasks = tasks_by_month[month_num]
                
                with cols[col_idx]:
                    # Card do Mês
                    is_current_month = (month_num == now.month and selected_year == now.year)
                    border_style = "border: 2px solid #6366f1;" if is_current_month else "border: 1px solid rgba(255,255,255,0.05);"
                    bg_style = "background: rgba(99, 102, 241, 0.05);" if is_current_month else "background: rgba(30, 41, 59, 0.4);"
                    
                    month_html = f"""
                        <div style="{bg_style} {border_style} border-radius: 16px; padding: 15px; min-height: 280px; margin-bottom: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
                                <span style="color: white; font-weight: 700; font-size: 1rem; text-transform: uppercase;">{month_name}</span>
                                <span style="background: rgba(255,255,255,0.1); color: #94a3b8; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">{len(month_tasks)} tasks</span>
                            </div>
                    """
                    
                    if not month_tasks:
                        month_html += """
                            <div style="text-align: center; padding: 40px 10px; color: #475569; font-size: 0.75rem; font-style: italic;">
                                Sem atividades programadas
                            </div>
                        """
                    else:
                        for t in month_tasks[:5]: # Mostrar apenas as primeiras 5 para não estourar o card
                            info = t.get_category_info()
                            prio_color = PRIORITY_CONFIG.get(t.priority, {'color': '#94a3b8'})['color']
                            status_color = STATUS_CONFIG.get(t.status, {'color': '#94a3b8'})['color']
                            
                            due_day = datetime.strptime(t.due_date, "%Y-%m-%d").day
                            
                            month_html += f"""
                                <div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 10px; padding: 6px; background: rgba(255,255,255,0.02); border-radius: 6px; border-left: 3px solid {prio_color};">
                                    <div style="min-width: 24px; font-size: 0.7rem; font-weight: 800; color: #6366f1; padding-top: 2px;">{due_day:02d}</div>
                                    <div style="flex: 1;">
                                        <div style="color: #f1f5f9; font-size: 0.75rem; font-weight: 600; line-height: 1.2; margin-bottom: 2px;">{t.title[:30]}{"..." if len(t.title) > 30 else ""}</div>
                                        <div style="display: flex; gap: 6px; align-items: center;">
                                            <span style="font-size: 0.6rem; color: #94a3b8;">👤 {t.responsible.split()[0]}</span>
                                            <span style="font-size: 0.6rem; color: {status_color}; font-weight: 700;">● {t.status}</span>
                                        </div>
                                    </div>
                                </div>
                            """
                        
                        if len(month_tasks) > 5:
                            month_html += f"""
                                <div style="text-align: center; color: #6366f1; font-size: 0.65rem; font-weight: 700; cursor: pointer; padding-top: 5px;">
                                    + {len(month_tasks) - 5} mais atividades...
                                </div>
                            """
                            
                    month_html += "</div>"
                    st.markdown(month_html, unsafe_allow_html=True)

        # Adicionar CSS extra para animações se necessário
        st.markdown("""
            <style>
            .month-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
            }
            </style>
        """, unsafe_allow_html=True)



# ==========================================
# FOLLOW-UP SEMANAL
# ==========================================

class FollowUpView:
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        week_ahead = today + timedelta(days=7)
        
        today_str = today.strftime("%Y-%m-%d")
        week_ago_str = week_ago.strftime("%Y-%m-%d")
        week_ahead_str = week_ahead.strftime("%Y-%m-%d")
        
        # Filtros
        completed_week = [t for t in tasks if t.status == "Concluído" and t.due_date >= week_ago_str]
        in_progress = [t for t in tasks if t.status == "Em Andamento"]
        overdue = [t for t in tasks if t.due_date < today_str and t.status != "Concluído"]
        upcoming = [t for t in tasks if today_str <= t.due_date <= week_ahead_str and t.status != "Concluído"]
        high_priority_pending = [t for t in tasks if t.priority in ["Alta", "Urgente"] and t.status not in ["Concluído"]]
        
        # ====== HEADER ======
        st.markdown(
"""
<div style='background:linear-gradient(135deg, #2d3250 0%, #1c1f3f 100%);
            border-radius:16px;padding:24px;margin-bottom:24px;
            border-left:5px solid #579bfc;'>
    <h2 style='color:white;margin:0 0 8px 0;font-size:1.5rem;'>
        📊 Follow-Up Semanal
    </h2>
    <p style='color:#9699a6;margin:0;font-size:0.9rem;'>
        Resumo executivo para reunião com gestão
    </p>
</div>
""",
            unsafe_allow_html=True,
        )
        
        # ====== KPIs EXECUTIVOS ======
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            UIComponents.render_kpi_card("Concluídas (7 dias)", len(completed_week), "🎯", "linear-gradient(135deg,#00c875,#00cd8e)", "#00c875")
        with k2:
            UIComponents.render_kpi_card("Em Andamento", len(in_progress), "⚡", "linear-gradient(135deg,#fdab3d,#ff9f43)", "#fdab3d")
        with k3:
            UIComponents.render_kpi_card("Atrasadas", len(overdue), "⚠️", "linear-gradient(135deg,#e44258,#df2f4a)", "#e44258")
        with k4:
            UIComponents.render_kpi_card("Próximos 7 dias", len(upcoming), "📅", "linear-gradient(135deg,#579bfc,#00d9ff)", "#579bfc")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ====== LAYOUT DUAS COLUNAS ======
        col_left, col_right = st.columns(2)
        
        # ====== CONQUISTAS DA SEMANA ======
        with col_left:
            st.markdown(
                """
                <div style='background:var(--monday-bg-light);border-radius:12px;padding:20px;
                            border:1px solid var(--monday-border);margin-bottom:20px;'>
                    <h3 style='color:#00c875;margin:0 0 16px 0;font-size:1.1rem;'>
                        🎯 Conquistas da Semana
                    </h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            if completed_week:
                # Agrupar por categoria
                by_category: Dict[str, List[Task]] = {}
                for t in completed_week:
                    info = t.get_category_info()
                    cat = info["name"]
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(t)
                
                for cat, cat_tasks in sorted(by_category.items()):
                    info = cat_tasks[0].get_category_info()
                    st.markdown(
                        f"""
                        <div style='margin-bottom:12px;'>
                            <span style='color:{info['color']};font-weight:700;font-size:0.9rem;'>
                                {info['icon']} {cat}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    for t in cat_tasks:
                        due = datetime.strptime(t.due_date, "%Y-%m-%d").strftime("%d/%m")
                        # Render HTML manually
                        html = f"<div style='background:#363a5a;padding:10px 14px;margin:4px 0 4px 20px;border-radius:6px;border-left:3px solid #00c875;'>"
                        html += f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                        html += f"<span style='color:white;font-size:0.85rem;'>✅ {t.title}</span>"
                        html += f"<span style='color:#9699a6;font-size:0.75rem;'>{due}</span>"
                        html += "</div></div>"
                        
                        st.markdown(html, unsafe_allow_html=True)
            else:
                st.info("Nenhuma tarefa concluída nos últimos 7 dias.")
        
        # ====== BLOQUEIOS / ATRASADAS + CRÍTICAS ======
        with col_right:
            st.markdown(
                """
                <div style='background:var(--monday-bg-light);border-radius:12px;padding:20px;
                            border:1px solid var(--monday-border);margin-bottom:20px;'>
                    <h3 style='color:#e44258;margin:0 0 16px 0;font-size:1.1rem;'>
                        ⚠️ Atenção Necessária
                    </h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            attention_tasks = overdue + [t for t in high_priority_pending if t not in overdue]
            
            if attention_tasks:
                for t in attention_tasks[:5]:  # Limitar a 5
                    info = t.get_category_info()
                    prio_info = PRIORITY_CONFIG[t.priority]
                    due_date = datetime.strptime(t.due_date, "%Y-%m-%d")
                    days_late = (today - due_date).days if t.due_date < today_str else 0
                    
                    late_tag = f"<span style='color:#e44258;font-size:0.7rem;font-weight:700;'>({days_late} dias atrasada)</span>" if days_late > 0 else ""
                    
                    
                    # Manual HTML construction
                    html = f"<div style='background:#4a2a2f;padding:12px 14px;margin:6px 0;border-radius:8px;border-left:4px solid #e44258;'>"
                    html += f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                    html += f"<span style='color:white;font-weight:600;font-size:0.85rem;'>{info['icon']} {t.title[:35]}{'...' if len(t.title) > 35 else ''}</span>"
                    html += f"{late_tag}</div>"
                    html += f"<div style='display:flex;gap:8px;align-items:center;'>"
                    html += f"<span style='background:{prio_info['bg']};color:{prio_info['color']};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:600;'>{t.priority}</span>"
                    html += f"<span style='color:#9699a6;font-size:0.75rem;'>👤 {t.responsible}</span>"
                    html += "</div></div>"
                    
                    st.markdown(html, unsafe_allow_html=True)
                    
                    # --- FEEDBACK DA GESTÃO (SISTEMA DE NOTIFICAÇÃO) ---
                    # 1. Exibir Feedback (Para todos)
                    if getattr(t, "manager_feedback", ""):
                         st.markdown(f"""
                         <div style="background: rgba(250, 204, 21, 0.1); border-left: 3px solid #facc15; padding: 8px 12px; margin: -4px 0 8px 20px; border-radius: 0 0 6px 6px;">
                             <span style="color: #facc15; font-size: 0.8rem; font-weight: 600;">🔔 Mensagem da Gestão:</span>
                             <span style="color: #e2e8f0; font-size: 0.8rem; font-style: italic;">"{t.manager_feedback}"</span>
                         </div>
                         """, unsafe_allow_html=True)

                    # 2. Área de Edição (Apenas Gestores)
                    current_matricula = st.session_state.get("current_user", "")
                    is_manager_role = current_matricula in ["2484901", "GESTAO"]
                    
                    if is_manager_role:
                         with st.expander("🗨️ Adicionar Notificação / Feedback", expanded=False):
                              curr_val = getattr(t, "manager_feedback", "")
                              new_feed = st.text_area("Mensagem para o analista", value=curr_val, key=f"feed_{t.id}", height=70, placeholder="Ex: Priorizar esta entrega...")
                              
                              f_col1, f_col2 = st.columns([0.6, 0.4])
                              with f_col1:
                                  if st.button("💾 Salvar Notificação", key=f"save_feed_{t.id}", use_container_width=True):
                                       t.manager_feedback = new_feed
                                       # Encontrar a tarefa real no session_state para salvar (pois 't' é uma cópia da lista local)
                                       real_t = next((x for x in st.session_state.tasks if x.id == t.id), None)
                                       if real_t:
                                           real_t.manager_feedback = new_feed
                                           st.session_state.data_manager.save_tasks(st.session_state.tasks)
                                           st.toast("Feedback salvo com sucesso!")
                                           time.sleep(1)
                                           st.rerun()
                              with f_col2:
                                   if st.button("🗑️ Excluir", key=f"del_feed_{t.id}", use_container_width=True):
                                       t.manager_feedback = ""
                                       real_t = next((x for x in st.session_state.tasks if x.id == t.id), None)
                                       if real_t:
                                           real_t.manager_feedback = ""
                                           st.session_state.data_manager.save_tasks(st.session_state.tasks)
                                           st.toast("Feedback removido!")
                                           time.sleep(1)
                                           st.rerun()
            else:
                st.success("🎉 Nenhuma tarefa atrasada ou crítica!")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ====== PRÓXIMOS ENTREGÁVEIS ======
        st.markdown(
            """
            <div style='background:var(--monday-bg-light);border-radius:12px;padding:20px;
                        border:1px solid var(--monday-border);margin-bottom:16px;'>
                <h3 style='color:#579bfc;margin:0;font-size:1.1rem;'>
                    📅 Próximos Entregáveis (7 dias)
                </h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if upcoming:
            # Ordenar por data
            upcoming_sorted = sorted(upcoming, key=lambda x: x.due_date)
            
            for t in upcoming_sorted:
                info = t.get_category_info()
                prio_info = PRIORITY_CONFIG[t.priority]
                status_info = STATUS_CONFIG[t.status]
                due = datetime.strptime(t.due_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                days_until = (datetime.strptime(t.due_date, "%Y-%m-%d") - today).days
                
                urgency_color = "#e44258" if days_until <= 1 else "#fdab3d" if days_until <= 3 else "#579bfc"
                
                
                # Build HTML exactly like we did for dashboard to avoid indentation issues
                html = f"<div style='background:#363a5a;padding:14px 18px;margin:8px 0;border-radius:8px;border-left:4px solid {urgency_color};display:flex;justify-content:space-between;align-items:center;'>"
                html += f"<div style='flex:1;'>"
                html += f"<div style='color:white;font-weight:600;font-size:0.9rem;margin-bottom:4px;'>{info['icon']} {t.title}</div>"
                html += f"<div style='display:flex;gap:10px;align-items:center;'>"
                html += f"<span style='background:{status_info['bg']};color:{status_info['text']};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:600;'>{t.status}</span>"
                html += f"<span style='background:{prio_info['bg']};color:{prio_info['color']};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:600;'>{t.priority}</span>"
                html += f"<span style='color:#9699a6;font-size:0.75rem;'>👤 {t.responsible}</span>"
                html += "</div></div>"
                html += f"<div style='text-align:right;'>"
                html += f"<div style='color:{urgency_color};font-weight:700;font-size:0.9rem;'>{due}</div>"
                html += f"<div style='color:#9699a6;font-size:0.75rem;'>{'Hoje!' if days_until == 0 else f'em {days_until} dias'}</div>"
                html += "</div></div>"
                
                st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("Nenhuma tarefa agendada para os próximos 7 dias.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ====== GRÁFICO DE ENTREGAS POR CATEGORIA ======
        st.markdown(
            """
            <div style='background:var(--monday-bg-light);border-radius:12px;padding:20px;
                        border:1px solid var(--monday-border);margin-bottom:16px;'>
                <h3 style='color:#a25ddc;margin:0;font-size:1.1rem;'>
                    📈 Entregas por Categoria (últimos 7 dias)
                </h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if completed_week:
            # Contar por categoria
            cat_counts = {}
            for t in completed_week:
                info = t.get_category_info()
                cat = info["name"]
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            
            df_chart = pd.DataFrame({
                "Categoria": list(cat_counts.keys()),
                "Concluídas": list(cat_counts.values())
            })
            
            fig = px.bar(
                df_chart,
                x="Concluídas",
                y="Categoria",
                text="Concluídas",
                orientation='h',
                color="Concluídas",
                color_continuous_scale=[[0, "#34495e"], [1, "#78be20"]],
            )
            fig.update_traces(
                textposition="outside",
                marker_line_width=0,
                marker=dict(cornerradius=5),
                textfont=dict(color="white", size=13, weight=800),
                hovertemplate="<b>%{y}</b><br>%{x} entregas<extra></extra>"
            )
            fig.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(t=30, b=20, l=0, r=20),
                height=350,
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#9699a6", size=10), title=None),
                yaxis=dict(showgrid=False, tickfont=dict(color="white", size=11, weight="bold"), title=None, automargin=True),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
                hoverlabel=dict(bgcolor="#1c1f3f", font_size=13, font_family="Inter", font_color="white")
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhuma entrega na última semana para exibir no gráfico.")

# ==========================================
# MODAL DE UPDATES POR ATIVIDADE
# ==========================================

class UpdatesModal:
    @staticmethod
    def render() -> None:
        if "show_updates_for_task" not in st.session_state:
            return
        task_id = st.session_state.show_updates_for_task
        task = next((t for t in st.session_state.tasks if t.id == task_id), None)
        if not task:
            del st.session_state.show_updates_for_task
            return
        
        dm = st.session_state.data_manager
        updates = sorted(dm.get_task_updates(task_id), key=lambda u: u.timestamp, reverse=True)
        
        with st.expander(f"💬 Updates • {task.title}", expanded=True):
            # Form para novo update
            with st.form(f"form_update_{task_id}"):
                content = st.text_area("Novo update", placeholder="Descreva o que aconteceu nesta atividade...", height=100)
                submitted = st.form_submit_button("Publicar", type="primary", use_container_width=True)
                if submitted:
                    if not content.strip():
                        st.warning("Digite alguma coisa antes de publicar.")
                    else:
                        upd = TaskUpdate(task_id=task_id, content=content.strip())
                        dm.add_update(upd)
                        st.success("Update adicionado.")
                        time.sleep(0.4)
                        st.rerun()
            
            st.markdown("---")
            
            if not updates:
                st.info("Nenhum update ainda para esta atividade.")
            else:
                for u in updates:
                    ts = datetime.strptime(u.timestamp, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    st.markdown(
                        f"""<div style='background:var(--monday-bg-light);border-left:4px solid #579bfc;padding:12px 14px;margin-bottom:8px;border-radius:8px;'>
    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
        <span style='color:#579bfc;font-weight:700;font-size:0.9rem;'>{u.user}</span>
        <span style='color:#9699a6;font-size:0.8rem;'>{ts}</span>
    </div>
    <div style='color:#ffffff;font-size:0.9rem;line-height:1.5;'>{u.content}</div>
</div>""",
                        unsafe_allow_html=True,
                    )
            
            if st.button("Fechar", use_container_width=True):
                del st.session_state.show_updates_for_task
                st.rerun()

# ==========================================
# MODAL NOVA TAREFA
# ==========================================

class NewTaskModal:
    @staticmethod
    def render() -> None:
        if not st.session_state.get("show_modal", False):
            return
        
        with st.expander("✨ Lançar Nova Atividade", expanded=True):
            # Compatibilidade com dados dinâmicos
            CATEGORY_OPTIONS = st.session_state.get("categories", DEFAULT_CATEGORY_OPTIONS)
            
            # Filtragem de segurança de categorias (Privacidade)
            current_mat = st.session_state.get("current_user", "")
            is_admin_manager = current_mat in ["2949400", "2484901", "GESTAO"]
            
            allowed_keys = []
            for k, val in CATEGORY_OPTIONS.items():
                if val["name"] == "Pessoas/Atendimentos": 
                    continue
                
                owner = val.get("owner")
                # Mostrar se: Admin OU Dono é o usuário atual
                # Legacy (owner is None) só aparece para Admins ou se for Maicon
                if is_admin_manager:
                    allowed_keys.append(k)
                elif owner == current_mat:
                    allowed_keys.append(k)
                elif owner is None and current_mat == "2949400": # Maicon vê legacy
                    allowed_keys.append(k)
            
            # Se não há categorias para o usuário, allowed_keys permanece vazio.
            # Isso impede que usuários sem categorias vejam as de outros.
            # O sistema abaixo já lida com "options" vazio mostrando aviso.
            
            options = allowed_keys
            
            # Adicionar opção de "Atendimento" separadamente
            tipo_atividade = st.radio(
                "Tipo de Atividade",
                ["Demanda/Projeto", "👥 Atendimento de Pessoa"],
                horizontal=True,
                key="tipo_atividade",
                label_visibility="collapsed"
            )
            is_atendimento = tipo_atividade == "👥 Atendimento de Pessoa"
            
            if not is_atendimento:
                if options:
                    c_cat, c_btn = st.columns([0.88, 0.12])
                    with c_cat:
                        # Lógica para pré-selecionar categoria vinda da página de Categorias
                        default_idx = 0
                        prefill = st.session_state.get("prefill_category", "")
                        
                        if prefill:
                            # Tentar encontrar a chave correspondente ao nome da categoria
                            for i, k in enumerate(options):
                                if CATEGORY_OPTIONS[k]["name"] == prefill:
                                    default_idx = i
                                    break
                            
                            # Limpar na renderização subsequente
                            if "prefill_used" not in st.session_state:
                                 st.session_state.prefill_used = True
                            else:
                                 # Só remove se já foi usado uma vez
                                 st.session_state.pop("prefill_category", None)
                                 st.session_state.pop("prefill_used", None)

                        sel = st.selectbox("📂 Tema / Quadro", options, index=default_idx, key="new_task_category")
                    with c_btn:
                        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
                        if st.button("➕", help="Gerenciar Categorias", key="btn_new_cat_modal", use_container_width=True):
                            st.session_state.show_category_modal = True
                            st.rerun()
                    
                    cat_name = CATEGORY_OPTIONS[sel]["name"] if sel else "Outros"
                else:
                    st.warning("⚠️ Nenhuma categoria disponível. Crie uma categoria primeiro.")
                    if st.button("➕ Criar Nova Categoria", key="btn_create_first_cat", type="primary"):
                         st.session_state.show_category_modal = True
                         st.rerun()
                    cat_name = "Outros"
            else:
                cat_name = "Pessoas/Atendimentos"
            
            # Inicializar estado para dados do colaborador
            if "colaborador_dados" not in st.session_state:
                st.session_state.colaborador_dados = {}
            
            # Campos condicionais para atendimento (FORA do form para busca dinâmica)
            if is_atendimento:
                st.markdown(
                    """
                    <div style='background:#4a2a4a;border-left:3px solid #ff5ac4;padding:10px 14px;
                                border-radius:6px;margin-bottom:12px;'>
                        <span style='color:#ff5ac4;font-weight:600;font-size:0.85rem;'>👥 Dados do Atendimento</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Alternar entre Busca e Manual
                col_mode_1, col_mode_2 = st.columns([0.4, 0.6])
                with col_mode_1:
                    manual_mode = st.toggle("Cadastro Manual (Sem Matrícula)", key="is_manual_mode")
                
                if not manual_mode:
                    # Campo de matrícula com busca automática (Enter ou botão)
                    with st.form("form_busca_matricula", clear_on_submit=False):
                        col_mat, col_buscar = st.columns([0.88, 0.12])
                        with col_mat:
                            pessoa_matricula = st.text_input("🔢 Matrícula do Colaborador", placeholder="Digite a matrícula e pressione Enter", key="atend_matricula")
                        with col_buscar:
                            st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
                            buscar_submit = st.form_submit_button("🔍", type="primary", use_container_width=True, help="Buscar colaborador")
                        
                        if buscar_submit:
                            if pessoa_matricula.strip():
                                dados = buscar_colaborador_por_matricula(pessoa_matricula)
                                if dados and dados.get('nome'):
                                    st.session_state.colaborador_dados = dados
                                    st.success(f"✅ Colaborador encontrado: {dados['nome']}")
                                else:
                                    st.session_state.colaborador_dados = {}
                                    st.warning("⚠️ Colaborador não encontrado. Use o modo manual.")
                                st.rerun()
                            else:
                                st.warning("Digite uma matrícula para buscar.")
                    
                    # Exibir dados encontrados
                    dados_colab = st.session_state.colaborador_dados
                    
                    if dados_colab and dados_colab.get('nome'):
                        # Exibir informações do colaborador encontrado
                        st.markdown(
                            f"""
                            <div style='background:#2d3250;border-radius:10px;padding:16px;margin:10px 0;
                                        border:1px solid #579bfc;'>
                                <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>
                                    <div>
                                        <span style='color:#9699a6;font-size:0.75rem;text-transform:uppercase;'>👤 Nome</span>
                                        <div style='color:white;font-weight:600;font-size:0.95rem;'>{dados_colab.get('nome', '-')}</div>
                                    </div>
                                    <div>
                                        <span style='color:#9699a6;font-size:0.75rem;text-transform:uppercase;'>📱 Telefone</span>
                                        <div style='color:white;font-weight:600;font-size:0.95rem;'>{dados_colab.get('telefone', '-')}</div>
                                    </div>
                                    <div>
                                        <span style='color:#9699a6;font-size:0.75rem;text-transform:uppercase;'>🏢 Diretoria</span>
                                        <div style='color:white;font-weight:600;font-size:0.95rem;'>{dados_colab.get('diretoria', '-')}</div>
                                    </div>
                                    <div>
                                        <span style='color:#9699a6;font-size:0.75rem;text-transform:uppercase;'>💼 Cargo</span>
                                        <div style='color:white;font-weight:600;font-size:0.95rem;'>{dados_colab.get('cargo', '-')}</div>
                                    </div>
                                    <div style='grid-column:span 2;'>
                                        <span style='color:#9699a6;font-size:0.75rem;text-transform:uppercase;'>📧 E-mail Particular</span>
                                        <div style='color:white;font-weight:600;font-size:0.95rem;'>{dados_colab.get('email', '-')}</div>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        pessoa_nome = dados_colab.get('nome', '')
                    else:
                        st.info("👆 Digite a matrícula e busque, ou ative o 'Cadastro Manual'.")
                        pessoa_nome = ""  
                else:
                    st.markdown("##### 📝 Dados do Atendimento Manual")
                    c_m1, c_m2 = st.columns(2)
                    with c_m1:
                        m_nome = st.text_input("Nome *", key="man_nome")
                    with c_m2:
                        m_phone = st.text_input("Telefone", key="man_phone")
                    
                    m_email = st.text_input("E-mail", key="man_email")
                    pessoa_nome = m_nome
                    m_area = ""
                    m_role = ""
                
                # Seleção de subcategoria de atendimento
                # Opções dinâmicas baseadas nas categorias existentes
                related_options = ["Geral"] + [val["name"] for val in CATEGORY_OPTIONS.values() if val["name"] != "Pessoas/Atendimentos"]
                subcategoria_atend = st.selectbox(
                    "📂 Relacionado a",
                    related_options,
                    key="subcategoria_atendimento"
                )
            else:
                pessoa_nome = ""
                pessoa_matricula = ""
            
            with st.form("new_task_form", clear_on_submit=True):
                title = st.text_input("📝 Assunto", placeholder="Ex: Dúvida sobre documentação...")
                description = st.text_area("📋 Detalhes Adicionais", placeholder="Descreva mais...", height=100)
                
                uploaded_files = st.file_uploader("📎 Anexos", accept_multiple_files=True, help="Adicione arquivos relevantes")
                
                c2, c3 = st.columns(2)
                with c2:
                    priority = st.selectbox("⚡ Prioridade", list(PRIORITY_CONFIG.keys()), index=1)
                with c3:
                    due_date = st.date_input("📅 Prazo", format="DD/MM/YYYY")
                
                # Seleção de Colaboradores (Atividade Compartilhada)
                # Seleção de Colaboradores (Atividade Compartilhada)
                # Lista fixa da equipe com Fallback (Garante que nomes apareçam mesmo se Excel falhar ou cache estiver velho)
                core_team_map = {
                    "2949400": "Maicon",
                    "2858700": "Kherolainy",
                    "2791900": "Maria",
                    "2944000": "Davi"
                }

                core_names = []
                for mid, default_name in core_team_map.items():
                    d = buscar_colaborador_por_matricula(mid)
                    if d.get("nome"):
                        # Usar primeiro nome com Title Case
                        name = d.get("nome").split()[0].title()
                    else:
                        name = default_name
                    core_names.append(name)
                
                # Combinar com nomes já existentes nas tarefas para manter histórico
                existing_names = [t.responsible.title().strip() for t in st.session_state.tasks if t.responsible]
                
                # Lista final Unificada e Ordenada
                all_analysts = sorted(list(set(core_names + existing_names)))
                
                selected_collaborators = st.multiselect(
                    "👥 Colaboradores (opcional)",
                    all_analysts,
                    help="Selecione outros analistas que participam desta atividade. A tarefa aparecerá para eles também.",
                    placeholder="Selecione colaboradores..."
                )
                
                c_s, c_c = st.columns(2)
                with c_s:
                    submitted = st.form_submit_button("✅ Criar", type="primary", use_container_width=True)
                with c_c:
                    cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
                
                if submitted:
                    # Pegar dados do colaborador se for atendimento
                    if is_atendimento:
                        if st.session_state.get("is_manual_mode"):
                             dados_colab = {
                                  "nome": st.session_state.get("man_nome", ""),
                                  "telefone": st.session_state.get("man_phone", ""),
                                  "diretoria": "",
                                  "cargo": "",
                                  "email": st.session_state.get("man_email", ""),
                                  "matricula": "MANUAL-EXTERNO"
                             }
                             pessoa_nome = dados_colab["nome"]
                             pessoa_matricula = ""
                        else:
                            dados_colab = st.session_state.get('colaborador_dados', {})
                            if dados_colab and dados_colab.get('nome'):
                                pessoa_nome = dados_colab.get('nome', '')
                                pessoa_matricula = dados_colab.get('matricula', '')
                            else:
                                pessoa_nome = "" # Fallback
                                pessoa_matricula = ""
                    
                    # Montar título com nome/matrícula para atendimentos
                    if is_atendimento and pessoa_nome.strip():
                        mat_info = f" (Mat: {pessoa_matricula.strip()})" if pessoa_matricula.strip() else ""
                        final_title = f"{pessoa_nome.strip()}{mat_info} - {title.strip()}" if title.strip() else f"{pessoa_nome.strip()}{mat_info}"
                    else:
                        final_title = title.strip()
                    
                    if not final_title:
                        st.error("Título obrigatório.")
                    else:
                        try:
                            # Salvar anexos
                            saved_attachments = []
                            if uploaded_files:
                                upload_dir = "uploads"
                                if not os.path.exists(upload_dir):
                                    os.makedirs(upload_dir)
                                
                                for uploaded_file in uploaded_files:
                                    # Gerar nome seguro para o arquivo
                                    safe_name = f"{int(time.time())}_{uploaded_file.name}"
                                    file_path = os.path.join(upload_dir, safe_name)
                                    
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file.getbuffer())
                                    saved_attachments.append(file_path)

                            # Montar descrição com dados do colaborador (formatação organizada)
                            desc_final = description.strip()
                            if is_atendimento:
                                # Pegar a subcategoria selecionada
                                subcat = st.session_state.get('subcategoria_atendimento', 'Todos')
                                
                                info_lines = []
                                info_lines.append("═" * 40)
                                info_lines.append("📋 DADOS DO ATENDIMENTO")
                                info_lines.append("═" * 40)
                                info_lines.append(f"📂 Categoria: {subcat}")
                                
                                if dados_colab and dados_colab.get('nome'):
                                    info_lines.append("")
                                    info_lines.append("👤 DADOS DO COLABORADOR:")
                                    info_lines.append(f"   Telefone: {dados_colab.get('telefone', '-')}")
                                    if dados_colab.get('diretoria'):
                                        info_lines.append(f"   Diretoria: {dados_colab.get('diretoria', '-')}")
                                    if dados_colab.get('cargo'):
                                        info_lines.append(f"   Cargo: {dados_colab.get('cargo', '-')}")
                                    info_lines.append(f"   E-mail: {dados_colab.get('email', '-')}")
                                
                                info_lines.append("═" * 40)
                                
                                info_extra = "\n".join(info_lines)
                                desc_final = f"{desc_final}\n\n{info_extra}" if desc_final else info_extra
                            
                            # Obter nome do responsável atual
                            try:
                                curr_mat = st.session_state.get("current_user", "")
                                curr_d = buscar_colaborador_por_matricula(curr_mat)
                                responsible_name = curr_d.get("nome", "Usuário").split()[0]
                            except:
                                responsible_name = "Usuário"

                            t = Task(
                                title=final_title,
                                responsible=responsible_name,
                                category=cat_name,
                                priority=priority,
                                status="Pendente",
                                due_date=due_date.strftime("%Y-%m-%d"),
                                description=desc_final,
                                attachments=saved_attachments,
                                collaborators=selected_collaborators  # Colaboradores mencionados
                            )
                            st.session_state.tasks.append(t)
                            st.session_state.data_manager.save_tasks(st.session_state.tasks)
                            st.success("Atividade criada.")
                            st.session_state.show_modal = False
                            st.session_state.colaborador_dados = {}  # Limpar dados
                            time.sleep(0.4)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
                    if cancel:
                        st.session_state.show_modal = False
                        st.session_state.colaborador_dados = {}  # Limpar dados
                        st.rerun()

class EditTaskModal:
    @staticmethod
    def render() -> None:
        editing_id = st.session_state.get("editing_task_id")
        if not editing_id:
            return

        task_to_edit = next((t for t in st.session_state.tasks if t.id == editing_id), None)
        if not task_to_edit:
            st.session_state.editing_task_id = None
            return

        with st.expander("✏️ Editar Atividade", expanded=True):
            # Adicionar funcionalidade de anexos também
            
            with st.form("form_edit_task"):
                e_title = st.text_input("Título", value=task_to_edit.title)
                e_desc = st.text_area("Descrição", value=task_to_edit.description, height=150)
                
                # Layout colunas
                ec1, ec2, ec3 = st.columns([0.3, 0.3, 0.4])
                with ec1:
                    e_prio = st.selectbox("Prioridade", list(PRIORITY_CONFIG.keys()), index=list(PRIORITY_CONFIG.keys()).index(task_to_edit.priority))
                with ec2:
                    current_due = datetime.strptime(task_to_edit.due_date, "%Y-%m-%d")
                    e_due = st.date_input("Prazo", value=current_due, format="DD/MM/YYYY")
                
                # Collaborators (Allow changing here too?) - Simplificação: Manter original
                # Se o usuário quiser mudar colaboradores, por enquanto não está no form original.
                
                # Checkbox para Concluir rápido
                e_status_done = st.checkbox("✅ Marcar como Concluída", value=(task_to_edit.status == "Concluído"))
                
                ec_b1, ec_b2 = st.columns(2)
                with ec_b1:
                    if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        task_to_edit.title = e_title
                        task_to_edit.description = e_desc
                        task_to_edit.priority = e_prio
                        task_to_edit.due_date = e_due.strftime("%Y-%m-%d")
                        
                        if e_status_done and task_to_edit.status != "Concluído":
                            task_to_edit.status = "Concluído"
                        elif not e_status_done and task_to_edit.status == "Concluído":
                                task_to_edit.status = "Em Andamento" # Reverter
                        
                        dm = st.session_state.data_manager
                        dm.save_tasks(st.session_state.tasks)
                        st.session_state.editing_task_id = None
                        st.balloons()
                        st.success("Alterações salvas!")
                        time.sleep(0.5)
                        st.rerun()
                with ec_b2:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state.editing_task_id = None
                        st.rerun()

# ==========================================
# CSS
# ==========================================

@st.cache_data(show_spinner=False)
def get_background_style_css() -> str:
    bg_style = "background: radial-gradient(circle at top right, #1e1b4b, #0f172a) !important;"
    if os.path.exists("Fundo.png"):
        try:
            with open("Fundo.png", "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            bg_style = f'''
                background-image: url("data:image/png;base64,{b64}") !important;
                background-size: cover !important;
                background-attachment: fixed !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
            '''
        except Exception:
            pass
    return bg_style

def load_custom_css() -> None:
    # Configuração do Fundo (Cacheado)
    bg_style = get_background_style_css()

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        /* FORÇAR MODO ESCURO GERAL (Targeted Elements ONLY) */
        h1, h2, h3, h4, h5, h6, p, label {
            color: #f8fafc;
        }
        
        /* Ensure Inputs and Selectboxes are visible */
        .stTextInput input, 
        .stTextArea textarea, 
        .stSelectbox div[data-baseweb="select"] > div, 
        .stDateInput input {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #6366f1 !important;
        }

        /* ==================================================================================
           NUCLEAR OPTION FOR MICROSOFT EDGE & BRAVE
           (High Specificity Overrides)
           ================================================================================== */
           
        /* ==================================================================================
           SUPERNOVA OPTION: GLOBAL OVERRIDES FOR STABILITY
           ================================================================================== */
        
        /* 0. FORCE GLOBAL TEXT COLOR */
        html, body, .stApp, .stApp header {
            color: #ffffff !important;
        }

        /* 1. INPUTS: DARK BACKGROUND, WHITE TEXT */
        div[data-baseweb="input"], 
        div[data-baseweb="select"] > div,
        input.stTextInput, 
        input {
            background-color: rgba(15, 23, 42, 0.9) !important;
            color: #ffffff !important;
            caret-color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important;
            font-weight: 600 !important;
        }
        
        /* 2. BUTTONS: FORCE DARK & CLEAR VISIBILITY */
        div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
            font-weight: 700 !important;
        }
        
        div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
            background-color: #6366f1 !important;
            border-color: #ffffff !important;
        }
        
        /* Force text inside any button to be white */
        div.stButton > button p, div[data-testid="stFormSubmitButton"] > button p, button p {
             color: #ffffff !important;
        }

        /* 3. TASK CARDS: RESTORE WHITE BORDER (User Request) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            background-color: rgba(30, 41, 59, 0.4) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }

        /* 4. TOASTS & ALERTS: HIGH CONTRAST */
        div[data-testid="stToast"], div[data-testid="stAlert"], div.stToast {
            background-color: #0f172a !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
        }
        div[data-testid="stToast"] *, div[data-testid="stAlert"] * {
            color: #ffffff !important;
        }

        /* 5. AUTOFILL FIX */
        input:-webkit-autofill {
            -webkit-box-shadow: 0 0 0 30px #1e293b inset !important;
            -webkit-text-fill-color: white !important;
        }

        /* 6. FIX MODAL/DIALOG TEXT COLOR */
        div[role="dialog"], div[data-testid="stDialog"], div.stDialog > div {
             background-color: #1e293b !important;
             color: #f8fafc !important;
        }
        div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3, div[role="dialog"] label, div[role="dialog"] p {
             color: #f8fafc !important;
        }
        div[role="dialog"] .stForm {
            background-color: rgba(15, 23, 42, 0.5) !important;
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Corrigir Selectbox Dropdown (Opções) */
        ul[data-testid="stSelectboxVirtualDropdown"] {
            background-color: #1e293b !important;
        }
        li[role="option"] {
            background-color: #1e293b !important;
            color: white !important;
        }
        li[role="option"]:hover, li[role="option"][aria-selected="true"] {
             background-color: #6366f1 !important;
        }
        
        /* Garantia para SVG Icons nos Selects */
        div[data-testid="stSelectbox"] svg {
            fill: #94a3b8 !important;
        }
        
        :root {
            --bg-deep: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --accent-primary: #6366f1;
        }

        .stApp {
            """ + bg_style + """
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        /* REMOVER HEADER PADRÃO DO STREAMLIT */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        div[data-testid="stToolbar"] {
            visibility: hidden;
            height: 0%;
            position: fixed;
        }
        
        div[data-testid="stDecoration"] {
            display: none;
        }
        
        div[data-testid="stStatusWidget"] {
            display: none;
        }

        .main .block-container {
            padding: 1.5rem 3rem !important;
            max-width: 100% !important;
            padding-top: 1rem !important;
        }

        /* RESPONSIVIDADE MOBILE */
        @media only screen and (max-width: 768px) {
            .main .block-container {
                padding: 1rem 1rem !important;
            }
            
            /* Ajustar Fonte Gigante do Login */
            h1[style*="font-size: 5rem"] {
                font-size: 3.5rem !important;
                line-height: 1.0 !important;
            }
            
            /* Ajustes finos */
            .page-header h1 {
                font-size: 1.8rem;
            }
        }

        /* HEADER DO APP */
        .page-header {
            margin-bottom: 2rem;
            border-left: 4px solid var(--accent-primary);
            padding-left: 1.5rem;
        }
        .page-header h1 {
            font-size: 2.8rem;
            font-weight: 900;
            color: #1e293b;
            margin: 0;
            letter-spacing: -1.5px;
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .page-header p {
            color: var(--text-dim);
            font-size: 0.95rem;
            margin-top: 5px;
        }

        /* KPI CARDS - ENHANCED HOVER */
        .kpi-card {
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            height: 110px;
            width: 100%;
            position: relative;
            overflow: hidden;
        }
        .kpi-card:hover { 
            transform: translateY(-8px) scale(1.02); 
            border-color: var(--accent-primary); 
            box-shadow: 0 15px 35px rgba(99, 102, 241, 0.3);
            background: rgba(30, 41, 59, 1);
        }
        .kpi-card::after {
            content: "";
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
            transition: 0.5s;
        }
        .kpi-card:hover::after {
            left: 100%;
        }

        .kpi-icon-container {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.3s ease;
        }
        .kpi-card:hover .kpi-icon-container {
            transform: rotate(10deg);
        }

        /* METRIC CARDS (Standard Streamlit) */
        div[data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 15px !important;
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            background: rgba(30, 41, 59, 0.8);
            border-color: var(--accent-primary);
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }

        /* BUTTONS ENHANCED */
        div.stButton > button {
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }
        div.stButton > button:hover {
            transform: scale(1.05) translateY(-2px) !important;
        }

        /* CHARTS CONTAINER */
        .chart-container {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            padding: 1.5rem;
            transition: all 0.3s ease;
            margin-bottom: 24px;
        }
        .chart-container:hover {
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            background: rgba(30, 41, 59, 0.85);
        }

        /* TASK CARDS (Boards/Monday View) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(148, 163, 184, 0.08) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
            transition: all 0.3s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            background: rgba(148, 163, 184, 0.15) !important;
            border-color: rgba(99, 102, 241, 0.4) !important;
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        }
        .h-row1 { height: 420px; }
        .h-row2 { height: 320px; }
        .h-row3 { height: 400px; }

        .chart-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 1rem;
            flex-shrink: 0;
        }
        .chart-title { font-size: 1.1rem; font-weight: 700; color: var(--text-main); }
        .chart-icon { font-size: 1.2rem; }

        /* MONDAY/BOARDS STYLE */
        .monday-group-header {
            background: rgba(30, 41, 59, 0.5);
            backdrop-filter: blur(4px);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 14px 20px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        }
        .monday-group-header:hover {
            background: rgba(30, 41, 59, 0.8);
            border-color: rgba(255,255,255,0.15);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .task-card-interactive {
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .task-card-interactive:hover {
            transform: translateX(8px);
            background: var(--bg-card) !important;
        }

        /* KANBAN CARD HOVER */
        .kanban-card-hover {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer;
        }
        .kanban-card-hover:hover {
            transform: translateY(-5px) scale(1.02);
            border-color: rgba(99, 102, 241, 0.4) !important;
            box-shadow: 0 12px 25px rgba(0,0,0,0.4) !important;
            background: rgba(45, 55, 72, 0.5) !important;
            filter: brightness(1.1);
        }

        /* SCROLLBAR */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

        /* CALENDÁRIO */
        .monday-calendar { background: var(--bg-card); border-radius: 20px; padding: 24px; border: 1px solid var(--border-subtle); backdrop-filter: blur(10px); }
        .calendar-header { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; margin-bottom: 15px; }
        .day-header { text-align: center; font-weight: 800; color: var(--text-dim); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
        .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; }
        .calendar-day { 
            background: rgba(15, 23, 42, 0.4); 
            border: 1px solid var(--border-subtle); 
            border-radius: 16px; 
            min-height: 140px; 
            padding: 12px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            position: relative;
        }
        .calendar-day:hover { 
            background: rgba(30, 41, 59, 0.95);
            border-color: var(--accent-primary); 
            transform: scale(1.03);
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            z-index: 100;
        }
        .calendar-day.today { border-color: var(--accent-primary); background: rgba(99, 102, 241, 0.1); }
        .day-number { font-weight: 800; font-size: 1.2rem; color: var(--text-main); margin-bottom: 10px; opacity: 0.7; }
        .day-number.today { color: var(--accent-primary); opacity: 1; }
        
        .task-item { 
            padding: 4px 10px; 
            margin-bottom: 5px; 
            font-size: 0.7rem; 
            border-radius: 6px; 
            color: var(--text-main); 
            border-left: 3px solid transparent; 
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 500;
            cursor: pointer;
        }
        .task-item:hover {
            transform: scale(1.05) translateX(2px);
            filter: brightness(1.2);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 10;
        }
        .task-more {
            font-size: 0.65rem;
            color: var(--accent-primary);
            text-align: center;
            margin-top: 6px;
            font-weight: 700;
            padding: 4px;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 4px;
            transition: all 0.2s ease;
        }
        .task-more:hover {
            background: rgba(99, 102, 241, 0.2);
            transform: translateY(2px);
        }

        /* TOOLTIP PREMIUM - Corrigido Posicionamento */
        .calendar-tooltip {
            display: none;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            border: 1px solid var(--accent-primary);
            border-radius: 16px;
            padding: 16px;
            min-width: 300px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.8);
            z-index: 9999;
            backdrop-filter: blur(15px);
            margin-bottom: 15px;
        }
        .calendar-day:hover .calendar-tooltip { display: block; animation: slideUp 0.3s ease-out; }
        
        @keyframes slideUp { from { opacity: 0; transform: translateX(-50%) translateY(10px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }

        .tooltip-header { 
            color: var(--text-main); 
            font-weight: 800; 
            font-size: 0.9rem; 
            margin-bottom: 12px; 
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-subtle); 
        }
        .tooltip-task { 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            padding: 8px; 
            border-radius: 8px; 
            margin-bottom: 6px; 
            border-left: 3px solid; 
            background: rgba(255,255,255,0.03);
            text-align: left;
        }
        .tooltip-title { flex: 1; color: var(--text-main); font-size: 0.8rem; font-weight: 500; }
        .tooltip-status { font-size: 0.7rem; font-weight: 700; opacity: 0.8; }

        /* KANBAN PREMIUM */
        .kanban-column {
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            padding: 1.25rem;
            min-height: 80vh;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .kanban-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid rgba(255,255,255,0.05);
        }
        .kanban-title { font-size: 0.95rem; font-weight: 800; color: var(--text-main); text-transform: uppercase; letter-spacing: 0.5px; }
        .kanban-count { background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 20px; font-size: 0.75rem; color: var(--text-dim); }
        
        .kanban-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 14px;
            transition: all 0.3s ease;
            position: relative;
            cursor: pointer;
        }
        .kanban-card:hover { 
            transform: translateY(-5px); 
            border-color: var(--accent-primary); 
            box-shadow: 0 12px 30px rgba(99, 102, 241, 0.25);
            z-index: 10;
        }
        .kanban-card-title { font-size: 0.9rem; font-weight: 700; color: var(--text-main); margin-bottom: 10px; line-height: 1.3; }
        .kanban-card-meta { display: flex; align-items: center; gap: 10px; font-size: 0.75rem; color: var(--text-dim); }
        .kanban-priority-badge { font-size: 0.65rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
        </style>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# LOGIN PAGE
# ==========================================

def login_page():
    # CSS Ultra Moderno (Glassmorphism + Animated UI + Video Effect Background)
    st.markdown(
        """
        <style>
        /* Background Animado (Efeito Video) */
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .stApp {
            background: linear-gradient(-45deg, #020617, #312e81, #4c1d95, #020617);
            background-size: 400% 400%;
            animation: gradientBG 20s ease infinite;
        }

        /* Centralizar verticalmente toda a página */
        [data-testid="stAppViewContainer"] > .main {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        
        /* Animação de Entrada do Card */
        @keyframes slideUpFade {
            from { opacity: 0; transform: translateY(30px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        /* Estilo do Card (Formulário) */
        [data-testid="stForm"] {
            width: 100%;
            background: rgba(15, 23, 42, 0.6) !important; /* Mais escuro e profundo */
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            padding: 48px 40px !important;
            border-radius: 28px !important;
            box-shadow: 
                0 0 0 1px rgba(255, 255, 255, 0.05),
                0 20px 50px -10px rgba(0, 0, 0, 0.7) !important;
            animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        
        /* Typography */
        .login-header-icon {
            font-size: 3.5rem;
            text-align: center;
            margin-bottom: 1rem;
            filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.3));
        }
        /* Fix for Edge/Chrome Autofill Backgrounds */
        input:-webkit-autofill,
        input:-webkit-autofill:hover, 
        input:-webkit-autofill:focus, 
        input:-webkit-autofill:active {
            -webkit-box-shadow: 0 0 0 30px #1e293b inset !important;
            -webkit-text-fill-color: white !important;
            transition: background-color 5000s ease-in-out 0s;
        }

        .login-subtitle-modern {
            background: linear-gradient(90deg, #cbd5e1, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 4px;
            text-transform: uppercase;
            margin: 0;
            opacity: 1;
            text-align: center;
            text-shadow: 0 2px 10px rgba(255,255,255,0.1);
        }
        
        .login-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(circle at top left, rgba(255,255,255,0.15), rgba(255,255,255,0.05));
            padding: 20px 35px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.15);
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 0 0 1px rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            margin-bottom: 20px;
        }
        
        .login-badge-icon {
            font-size: 2.2rem; 
            margin-right: 12px; 
            filter: grayscale(1);
        }
        
        .login-badge-title {
            font-family: 'Inter', system-ui, sans-serif;
            font-weight: 900;
            font-size: 3.2rem;
            color: #ffffff;
            margin: 0;
            letter-spacing: 1px;
            text-shadow: 0 2px 15px rgba(255,255,255,0.4);
            line-height: 1;
        }

        /* Estilizar Campos de Texto (Inputs) */
        /* Streamlit injeta divs wrap, vamos tentar pegar inputs genéricos dentro do form */
        div[data-testid="stForm"] input {
            background: rgba(0, 0, 0, 0.2) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            padding: 12px 16px !important;
            border-radius: 12px !important;
            font-size: 0.95rem !important;
            transition: all 0.3s ease;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15) !important;
            background: rgba(0, 0, 0, 0.35) !important;
        }

        /* Botão com Gradiente Moderno */
        div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 700 !important;
            padding: 0.75rem 1.5rem !important;
            border-radius: 14px !important;
            font-size: 1rem !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px -8px rgba(99, 102, 241, 0.6) !important;
            filter: brightness(1.1);
        }
        div[data-testid="stFormSubmitButton"] button:active {
            transform: translateY(0);
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

    # Centralização Horizontal
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown(
"""<div style="text-align: center; margin-bottom: 40px;">
    <h1 style="
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 5rem;
        color: #ffffff;
        margin: 0;
        letter-spacing: -4px;
        line-height: 0.9;
        text-shadow: 0 0 40px rgba(99, 102, 241, 0.6);
    ">DHO</h1>
    <div style="
        height: 6px;
        width: 60px;
        background: #6366f1;
        margin: 10px auto 20px auto;
        border-radius: 10px;
    "></div>
    <div style="
        color: #94a3b8;
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: 3px;
        text-transform: uppercase;
    ">Gestão Estratégica</div>
</div>""", 
                unsafe_allow_html=True
            )
            
            # Inputs estilizados
            matricula = st.text_input("Matrícula", placeholder="ID Corporativo", label_visibility="collapsed")
            senha = st.text_input("Senha", type="password", placeholder="Senha de Acesso", label_visibility="collapsed")
            
            st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)
            
            submit = st.form_submit_button("ENTRAR", type="primary", use_container_width=True)

            if submit:
                # Lista de usuários autorizados
                CREDENTIALS = {
                    "2949400": "Cocal@2025",  # Maicon
                    "2858700": "Cocal@2025",  # Analista 1
                    "2791900": "Cocal@2025",  # Analista 2
                    "2944000": "Cocal@2025",  # Analista 3
                    "2484901": "gestao@2025"  # Gestora
                }
                
                mat = matricula.strip()
                is_manager_direct = (mat.lower() == "gestao" and senha == "gestao")
                
                if is_manager_direct or (mat in CREDENTIALS and senha == CREDENTIALS[mat]):
                    st.session_state.authenticated = True
                    st.session_state.current_user = "GESTAO" if is_manager_direct else mat
                    # Reset state
                    for key in ["tasks", "categories", "selected_tasks", "colaborador_dados"]:
                        if key in st.session_state: del st.session_state[key]
                    
                    st.toast("Login realizado com sucesso!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

# ==========================================
# APP
# ==========================================

# Helper para Dialog (Compatibilidade)
if hasattr(st, "dialog"):
    dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    dialog_decorator = st.experimental_dialog
else:
    # Fallback to expander if really old
    def dialog_decorator(title):
        def decorator(func):
            def wrapper(*args, **kwargs):
                with st.expander(title, expanded=True):
                    func(*args, **kwargs)
            return wrapper
        return decorator

@dialog_decorator("⚙️ Gerenciar Categorias")
def manage_categories_dialog():
    st.markdown("Adicione novas categorias ou exclua as existentes.")
    
    cats = st.session_state.categories
    current_user = st.session_state.get("current_user", "")
    # Maicon (2949400) e Gestora (2484901) são Admins
    is_admin = (current_user in ["2949400", "2484901"])
    
    # Add New
    with st.container(border=True):
        st.markdown("###### Nova Categoria")
        c1, c2, c3 = st.columns([0.15, 0.65, 0.2])
        with c1:
            new_icon = st.text_input("Ícone", value="📌", key="new_cat_icon")
        with c2:
            new_name = st.text_input("Nome", placeholder="Ex: Financeiro", key="new_cat_name", label_visibility="collapsed")
        with c3:
            if st.button("➕ Add", use_container_width=True):
                if new_name:
                    key = f"{new_icon} {new_name}"
                    if key not in cats:
                        import random
                        colors = ['#ef4444', '#f97316', '#f59e0b', '#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#d946ef', '#ec4899']
                        color = random.choice(colors)
                        cats[key] = {
                            "color": color,
                            "icon": new_icon,
                            "name": new_name,
                            "bg": color + "22",
                            "owner": current_user # Salvar o dono
                        }
                        st.session_state.data_manager.save_categories(cats)
                        st.session_state.categories = cats
                        st.success("OK")
                        time.sleep(0.5)
                        st.rerun()

    st.markdown("###### Categorias Existentes")
    
    # List and Delete
    # Filtrar apenas categorias que o usuário pode ver/gerenciar
    visible_cats = []
    for key, val in cats.items():
        cat_owner = val.get("owner")
        
        # Regra: Admin vê tudo, Analista vê só as suas
        should_show = False
        if is_admin:
            should_show = True
        elif cat_owner == current_user:
            should_show = True
        elif cat_owner is None and current_user == "2949400": # Legacy Maicon
            should_show = True
            
        if should_show:
            visible_cats.append((key, val))
    
    if not visible_cats:
        st.info("Você não possui categorias personalizadas.")
    
    for key, val in visible_cats:
        c1, c2 = st.columns([0.85, 0.15])
        with c1:
            st.markdown(f"<div style='background:{val.get('bg', '#333')}; padding: 8px; border-radius: 8px; border-left: 4px solid {val['color']}'>{val['icon']} {val['name']}</div>", unsafe_allow_html=True)
        with c2:
            # Verificar Permissão
            cat_owner = val.get("owner")
            # Pode excluir se for Admin OU se for o Dono
            can_delete = is_admin or (cat_owner == current_user)
            
            if can_delete:
                if st.button("🗑️", key=f"del_{key}"): 
                    del cats[key]
                    st.session_state.data_manager.save_categories(cats)
                    st.session_state.categories = cats
                    st.rerun()
            else:
                st.button("🔒", disabled=True, key=f"lock_{key}", help="Somente o criador ou gestor pode excluir.")
                
    if st.button("Fechar", type="secondary", use_container_width=True):
        st.session_state.show_category_modal = False
        st.session_state.show_modal = False # Garantia
        st.rerun()

class CategoryManagerModal:
    @staticmethod
    def render():
        if st.session_state.get("show_category_modal"):
            manage_categories_dialog()


class ManagerDashboardView:

    @staticmethod
    def render(tasks: List[Task]) -> None:
        # Estilo do Container de Título
        st.markdown(
            """
            <div style="background: rgba(99, 102, 241, 0.1); border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                <h2 style="margin: 0; color: #f8fafc; font-weight: 800;">👩‍💼 Dashboard de Gestão Estratégica</h2>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.95rem;">Acompanhamento em tempo real da produtividade e prazos da equipe.</p>
            </div>
            """, unsafe_allow_html=True
        )

        # 1. Filtros Avançados (Conforme Ideia do Usuário)
        # Lista fixa da equipe com Fallback (Garante que nomes apareçam mesmo se Excel falhar ou cache estiver velho)
        core_team_map = {
            "2949400": "Maicon",
            "2858700": "Kherolainy",
            "2791900": "Maria",
            "2944000": "Davi"
        }
        
        core_names = []
        for mid, default_name in core_team_map.items():
            d = buscar_colaborador_por_matricula(mid)
            if d.get("nome"):
                 # Usar primeiro nome com Title Case
                 name = d.get("nome").split()[0].title()
            else:
                 name = default_name
            core_names.append(name)
        
        # Combinar com nomes já existentes nas tarefas (Normalizado para Title Case para evitar duplicatas MAICON vs Maicon)
        task_names = [t.responsible.strip().title() for t in tasks if t.responsible]
        analysts = sorted(list(set(core_names + task_names)))
        
        with st.container(border=True):
            st.markdown("###### 🔍 Refinar Busca Estratégica")
            
            # 1. Analistas no Topo para Cascata
            sel_analysts = st.multiselect("👥 Analistas da Equipe", analysts, default=[], key="gest_ms_analysts")
            
            # Base de dados para os próximos filtros
            if sel_analysts:
                # Normalizar responsável para filtrar corretamente as opções dependentes
                sub_tasks = [t for t in tasks if t.responsible.strip().title() in sel_analysts]
            else:
                sub_tasks = tasks

            # 2. Filtros Dependentes
            # Tema (Multiselect Largo)
            all_categories = sorted(list(set([t.category for t in sub_tasks if t.category])))
            sel_categories = st.multiselect("📂 Tema", all_categories, default=[], key="gest_ms_category", help="Selecione um ou mais temas")
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                all_statuses = sorted(list(set([t.status for t in sub_tasks if t.status])))
                sel_statuses = st.multiselect("🎯 Status", all_statuses, default=[], key="gest_ms_status")
            with c_f2:
                all_priorities = sorted(list(set([t.priority for t in sub_tasks if t.priority])))
                sel_priorities = st.multiselect("⚡ Prioridade", all_priorities, default=[], key="gest_ms_priority")\

        # 2. Lógica de Filtragem (Combinada)
        view_tasks = tasks
        if sel_categories:
            view_tasks = [t for t in view_tasks if t.category in sel_categories]
        if sel_statuses:
            view_tasks = [t for t in view_tasks if t.status in sel_statuses]
        if sel_priorities:
            view_tasks = [t for t in view_tasks if t.priority in sel_priorities]
        if sel_analysts:
            # Filtro Normalizado (Case Insensitive)
            view_tasks = [t for t in view_tasks if t.responsible.strip().title() in sel_analysts]
        
        # 3. Métricas Rápidas
        stats = DashboardView.calculate_stats(view_tasks)
        efficiency = int((stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0)
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total na Visão", stats["total"])
        m2.metric("Concluídas", stats["completed"], delta=f"{efficiency}%" if stats['total'] > 0 else None)
        m3.metric("Em Aberto", stats["in_progress"] + stats["urgent"])
        m4.metric("Atrasadas", stats["overdue"], delta_color="inverse")
        m5.metric("Eficiência", f"{efficiency}%")

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Abas de Organização
        t_dash, t_equipe, t_lista = st.tabs(["📉 Visão de Performance", "👥 Resumo por Analista", "📋 Relatório de Registros"])

        with t_dash:
            if not view_tasks:
                st.warning("Sem dados para exibir gráficos.")
            else:
                c1, c2 = st.columns(2)
                df_chart = pd.DataFrame([t.__dict__ for t in view_tasks])
                with c1:
                    st.markdown("###### Status das Demandas")
                    DashboardView.render_status_chart(df_chart)
                with c2:
                    st.markdown("###### Distribuição de Prioridades")
                    DashboardView.render_priority_chart(df_chart)

        with t_equipe:
            st.markdown("##### 🏆 Ranking de Produtividade (Visão Atual)")
            
            # Agrupar tarefas FILTRADAS por responsável (Normalizado)
            perf_data = {}
            for t in view_tasks:
                resp = t.responsible.strip().title()
                if resp not in perf_data: 
                    perf_data[resp] = []
                perf_data[resp].append(t)
            
            resumo_data = []
            
            # Se não houver dados, mostrar ao menos os analistas selecionados com zero
            target_analysts = sel_analysts if sel_analysts else analysts
            
            # Iterar sobre quem tem tarefas no filtro OU quem foi selecionado
            # (Prefiro iterar sobre quem tem tarefas para o ranking ser real)
            # Mas se 'sel_analysts' estiver ativo, queremos ver só eles.
            
            analysts_to_show = set(perf_data.keys())
            if sel_analysts:
                 analysts_to_show = analysts_to_show.intersection(set(sel_analysts))
                 # Adicionar selecionados que estão zerados (para mostrar que não tem nada)
                 analysts_to_show.update(sel_analysts)
            
            for resp_name in sorted(list(analysts_to_show)):
                r_tasks = perf_data.get(resp_name, [])
                s = DashboardView.calculate_stats(r_tasks)
                eff = int((s["completed"] / s["total"] * 100) if s["total"] > 0 else 0)
                resumo_data.append({
                     "Analista": resp_name,
                     "Total": s["total"],
                     "Concluídas": s["completed"],
                     "Pendentes": s["in_progress"] + s["urgent"],
                     "Atrasadas": s["overdue"],
                     "Eficiência": eff
                })
            
            if not resumo_data:
                 st.info("Nenhum dado para exibir neste recorte.")
            else:
                df_res = pd.DataFrame(resumo_data).sort_values(by="Eficiência", ascending=False)
                st.dataframe(
                    df_res,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Eficiência": st.column_config.ProgressColumn("Eficiência %", min_value=0, max_value=100, format="%d%%"),
                        "Analista": st.column_config.TextColumn("Analista", width="medium"),
                    }
                )

        with t_lista:
            if not view_tasks:
                st.info("Nenhum dado encontrado com os filtros selecionados.")
            else:
                df_all = pd.DataFrame([t.__dict__ for t in view_tasks])
                
                # Botões de Ação
                col_btn, col_spacer = st.columns([0.3, 0.7])
                with col_btn:
                    csv = df_all.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Exportar Relatório (CSV)", 
                        data=csv, 
                        file_name=f"gestao_demandas_{datetime.now().strftime('%Y%m%d')}.csv", 
                        mime="text/csv",
                        use_container_width=True
                    )

                st.dataframe(
                    df_all[["responsible", "title", "status", "priority", "due_date", "category"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "responsible": "Responsável",
                        "title": "Assunto/Demandas",
                        "status": "Status",
                        "priority": "Prioridade",
                        "due_date": "Prazo",
                        "category": "Categoria"
                    }
                )


def initialize_app() -> None:
    st.set_page_config(**PAGE_CONFIG)
    load_custom_css()
    if "data_manager" not in st.session_state:
        st.session_state.data_manager = DataManager()
    
    # --- STATUS DO BANCO DE DADOS (VISUALIZAÇÃO) ---
    with st.sidebar:
        dm = st.session_state.data_manager
        if hasattr(dm, 'use_sheets') and dm.use_sheets:
            st.success("☁️ Conectado: Google Sheets")
        else:
            st.warning("📂 Conectado: Arquivos Locais")
            
    if "categories" not in st.session_state:
        st.session_state.categories = st.session_state.data_manager.load_categories()
    if "tasks" not in st.session_state:
        st.session_state.tasks = st.session_state.data_manager.load_tasks()
    if "requests" not in st.session_state:
        st.session_state.requests = st.session_state.data_manager.load_requests()

    if "show_modal" not in st.session_state:
        st.session_state.show_modal = False
    if "show_category_modal" not in st.session_state:
        st.session_state.show_category_modal = False
    if "show_updates_for_task" not in st.session_state:
        st.session_state.show_updates_for_task = None
    if "selected_tasks" not in st.session_state:
        st.session_state.selected_tasks = set()
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "Quadros"


def main() -> None:
    initialize_app()
    
    # --- VERIFICAÇÃO DE LOGIN ---
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        login_page()
        return
    # ---------------------------
    
    search, page = NavigationSystem.render()
    
    # Cabeçalho Principal (Título + Controles)
    # Cabeçalho Principal (Título + Controles)
    h_c1, h_c2 = st.columns([0.55, 0.45])
    
    # Identificação do Usuário
    current_matricula = st.session_state.get("current_user", "2949400")
    if current_matricula == "GESTAO":
        user_name = "Gestão"
    else:
        try:
            user_data = buscar_colaborador_por_matricula(current_matricula)
            user_name = user_data.get("nome", "Visitante").split()[0]
        except:
            user_name = "Visitante"

    cat_filter = "Todos"
    analyst_filter = "Todos"
    is_admin_or_manager = current_matricula in ["2949400", "2484901", "GESTAO"]
    
    # Esquerda: Título da Página
    with h_c1:
        UIComponents.render_page_header(page)
        
    # Direita: Controles (Filtro, Config, Perfil)
    with h_c2:
         # ROW 1: Perfil (Nome + Avatar)
         rp0, rp1, rp2 = st.columns([0.65, 0.2, 0.15])
         
         with rp1:
            st.markdown(
                f"""
                <div style="text-align: right; line-height: 1.1; padding-top: 10px;">
                    <span style="display: block; font-size: 0.7rem; color: #94a3b8;">Olá,</span>
                    <span style="display: block; font-weight: 600; font-size: 0.85rem; color: #f8fafc;">{user_name}</span>
                </div>
                """, unsafe_allow_html=True
            )
         with rp2:
             st.markdown(
                f"""
                <div style="display: flex; justify-content: center; align-items: center; padding-top: 8px;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #a855f7); display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 0.85rem; border: 2px solid rgba(255,255,255,0.1);">
                        {user_name[0].upper()}
                    </div>
                </div>
                """, unsafe_allow_html=True
             )

         # Spacer between rows
         st.markdown("<br>", unsafe_allow_html=True)

         # ROW 2: Área de Filtros (Esticada)
         # Mostrar filtros em Todas as Paginas de Dados (Quadros, Kanban, Calendário e Painel)
         priority_filter = "Todos"
         today_filter = False
         
         if (page in ["Quadros", "Categorias"]) or (is_admin_or_manager and page in ["Calendário", "Painel", "Follow-Up"]):
            # Layout diferente para gestores vs usuários normais
            if is_admin_or_manager:
                # Gestores: Redistribuição do espaço (100% total) para esticar os botões
                # [Analista (27%), Categoria (32%), Prioridade (21%), Hoje (20%)]
                r_cols = st.columns([0.27, 0.32, 0.21, 0.20])
                
                with r_cols[0]:
                    # Lista fixa da equipe para o filtro
                    core_team_map = {
                        "2949400": "Maicon",
                        "2858700": "Kherolainy",
                        "2791900": "Maria",
                        "2944000": "Davi"
                    }
                    core_names = []
                    for mid, default_name in core_team_map.items():
                        d = buscar_colaborador_por_matricula(mid)
                        if d.get("nome"):
                            name = d.get("nome").split()[0].title()
                        else:
                            name = default_name
                        core_names.append(name)
                    
                    task_names = [t.responsible.strip().title() for t in st.session_state.tasks if t.responsible]
                    all_ans = sorted(list(set(core_names + task_names)))

                    analyst_filter = st.selectbox(
                        "Analista",
                        ["👤 Analista"] + all_ans,
                        index=0,
                        key="header_analyst_filter",
                        label_visibility="collapsed"
                    )
                    if analyst_filter == "👤 Analista":
                        analyst_filter = "Todos"
                
                with r_cols[1]:
                    allowed_header_cats = []
                    if analyst_filter != "Todos":
                        # Filtro Normalizado
                        allowed_header_cats = sorted(list(set([t.category for t in st.session_state.tasks if t.responsible.strip().title() == analyst_filter])))
                    else:
                        for v in st.session_state.categories.values():
                            allowed_header_cats.append(v["name"])
                    
                    cat_opts = ["📁 Categoria"] + sorted(list(set(allowed_header_cats)))
                    cat_filter = st.selectbox("Categoria", cat_opts, index=0, label_visibility="collapsed", key="header_cat_filter")
                    if cat_filter == "📁 Categoria":
                        cat_filter = "Todos"
                
                with r_cols[2]:
                    priority_opts = ["⚡ Prioridade", "Baixa", "Média", "Alta", "Urgente"]
                    priority_filter = st.selectbox("Prioridade", priority_opts, index=0, key="header_priority_filter", label_visibility="collapsed")
                    if priority_filter == "⚡ Prioridade":
                        priority_filter = "Todos"
                
                with r_cols[3]:
                    today_filter = st.checkbox("📅 Hoje", key="header_today_filter", help="Demandas para hoje")
            else:
                # Usuários normais: [Categoria, Prioridade, Hoje] - colunas mais largas
                r_cols = st.columns([0.40, 0.35, 0.15, 0.10])
                
                with r_cols[0]:
                    allowed_header_cats = []
                    for v in st.session_state.categories.values():
                        owner = v.get("owner")
                        if owner == current_matricula or (owner is None and current_matricula == "2949400"):
                            allowed_header_cats.append(v["name"])
                    
                    cat_opts = ["📁 Categoria"] + sorted(list(set(allowed_header_cats)))
                    cat_filter = st.selectbox("Categoria", cat_opts, index=0, label_visibility="collapsed", key="header_cat_filter")
                    if cat_filter == "📁 Categoria":
                        cat_filter = "Todos"
                
                with r_cols[1]:
                    priority_opts = ["⚡ Prioridade", "Baixa", "Média", "Alta", "Urgente"]
                    priority_filter = st.selectbox("Prioridade", priority_opts, index=0, key="header_priority_filter", label_visibility="collapsed")
                    if priority_filter == "⚡ Prioridade":
                        priority_filter = "Todos"
                
                with r_cols[2]:
                    today_filter = st.checkbox("📅 Hoje", key="header_today_filter", help="Mostrar apenas demandas com prazo para hoje")
    
    # Modais
    NewTaskModal.render()
    UpdatesModal.render()
    CategoryManagerModal.render()
    EditTaskModal.render()
    
    # Filtro geral por quadro e busca
    all_tasks: List[Task] = st.session_state.tasks
    
    # --- FILTRO DE PRIVACIDADE ---
    # Se não for Admin (Maicon) nem Gestor (Melissa), vê apenas suas demandas
    # Admins: 2949400, 2484901
    
    # Nota: user_name já foi calculado no header (Primeiro nome)
    # Se user_name for "Visitante" (falha no login), não mostra nada
    
    if current_matricula not in ["2949400", "2484901", "GESTAO"]:
        # Mostrar tarefas onde o usuário é responsável OU está como colaborador
        all_tasks = [t for t in all_tasks if t.responsible == user_name or user_name in (t.collaborators or [])]
    
    if cat_filter != "Todos":
        all_tasks = [t for t in all_tasks if t.category == cat_filter]
        
    if analyst_filter != "Todos":
        all_tasks = [t for t in all_tasks if t.responsible.lower() == analyst_filter.lower()]
    
    # Filtro de Prioridade
    if priority_filter != "Todos":
        all_tasks = [t for t in all_tasks if t.priority == priority_filter]
    
    # Filtro de Hoje (demandas com prazo para hoje)
    if today_filter:
        today_str = datetime.now().strftime("%Y-%m-%d")
        all_tasks = [t for t in all_tasks if t.due_date == today_str]
    
    if search:
        q = search.lower()
        all_tasks = [
            t for t in all_tasks
            if q in t.title.lower() or q in t.category.lower() or q in t.responsible.lower()
        ]
    
    views = {
        "Painel": DashboardView,
        "Quadros": BoardsView,
        "Calendário": CalendarView,
        "Categorias": CategoryListView,
        "Cronograma": RequisiçõesView,
        "Acompanhamento": ScheduleView,
        "Follow-Up": FollowUpView,
        "Gestão": ManagerDashboardView,
    }
    
    if page in views:
        views[page].render(all_tasks)

if __name__ == "__main__":
    main()

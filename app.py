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
        "Kanban": "📝",
        "Requisições": "📑",
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
            if st.button("📝 Kanban", key="nav_Kanban", use_container_width=True, type="primary" if st.session_state.selected_page == "Kanban" else "secondary"):
                st.session_state.selected_page = "Kanban"
                st.rerun()
        with cols[4]:
            if st.button("📑 Requisições", key="nav_Requisições", use_container_width=True, type="primary" if st.session_state.selected_page == "Requisições" else "secondary"):
                st.session_state.selected_page = "Requisições"
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


class KanbanView:
    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        statuses = list(STATUS_CONFIG.keys())
        icons = ["⚪", "🔵", "🟡", "🟢"]
        
        cols = st.columns(len(statuses))
        for i, (status, icon) in enumerate(zip(statuses, icons)):
            with cols[i]:
                sts_tasks = sorted(
                    [t for t in tasks if t.status == status],
                    key=lambda x: x.priority,
                    reverse=True
                )
                
                # Construir HTML total da coluna para evitar problemas de estrutura
                column_html = textwrap.dedent(f"""
                    <div style="background: rgba(30, 41, 59, 0.4); border-radius: 16px; padding: 16px; min-height: 80vh; border: 1px solid rgba(255,255,255,0.03);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding: 0 4px;">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <span style="font-size:1.1rem;">{icon}</span>
                                <span style="color:white; font-weight:800; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; opacity:0.8;">{status}</span>
                            </div>
                            <span style="background:rgba(255,255,255,0.1); color:#94a3b8; padding:2px 8px; border-radius:10px; font-size:0.65rem; font-weight:700;">{len(sts_tasks)}</span>
                        </div>
                """)
                
                if not sts_tasks:
                    column_html += textwrap.dedent(f"""
                        <div style="text-align:center; padding:60px 20px; color:#475569; font-size:0.75rem; font-style:italic; border: 2px dashed rgba(255,255,255,0.02); border-radius:12px;">
                            Sem atividades
                        </div>
                    """)
                
                for t in sts_tasks:
                    info = t.get_category_info()
                    pc = PRIORITY_CONFIG.get(t.priority, {'color': '#94a3b8'})
                    due = datetime.strptime(t.due_date, "%Y-%m-%d").strftime("%d/%m")
                    
                    column_html += textwrap.dedent(f"""
                        <div style="background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%); 
                                    border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 14px; margin-bottom:12px; 
                                    box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 4px solid {info['color']};">
                            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                                <span style="font-size:0.65rem; color:#ffffff; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; background:{info['color']}; padding:2px 8px; border-radius:4px;">{info['name']}</span>
                                <div style="display:flex; align-items:center; gap:4px; background:{pc['color']}20; padding:2px 8px; border-radius:4px; border:1px solid {pc['color']}40;">
                                    <div style="width:6px; height:6px; background:{pc['color']}; border-radius:50%;"></div>
                                    <span style="font-size:0.6rem; color:{pc['color']}; font-weight:700;">{t.priority}</span>
                                </div>
                            </div>
                            <div style="color:#f8fafc; font-size:0.85rem; font-weight:600; line-height:1.4; margin-bottom:14px; min-height:2.4em;">{t.title}</div>
                            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid rgba(255,255,255,0.05); padding-top:10px;">
                                <span style="font-size:0.7rem; color:#cbd5e1; font-weight:600;">📅 {due}</span>
                                <span style="font-size:0.7rem; color:#cbd5e1; font-weight:600;">👤 {t.responsible.split()[0]}</span>
                            </div>
                        </div>
                    """)
                
                column_html += "</div>"
                st.markdown(column_html, unsafe_allow_html=True)



class RequestsView:
    @staticmethod
    def render(tasks_ignored: List[Task]) -> None:
        # Nota: ignoramos a lista de tarefas padrão pois usamos a lista de requisições independente
        user_id = st.session_state.get("current_user", "2949400")
        is_manager = user_id in ["GESTAO", "2484901", "2949400"]
        
        reqs = st.session_state.get("requests", [])
        dm = st.session_state.data_manager
        
        # Título Dinâmico
        header_title = "📑 Minhas Requisições (RC/PO)" if not is_manager else "📑 Gestão Global de Requisições (RC/PO)"
        
        st.markdown(
            f"""
            <div style="background: rgba(99, 102, 241, 0.1); border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0; color: #f8fafc; font-weight: 800;">{header_title}</h2>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                        {"Controle individual de suas compras." if not is_manager else "Visão consolidada de todos os analistas."}
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True
        )

        # Filtro de Analista (Apenas para Gestão)
        filtered_reqs = reqs
        if is_manager:
            all_analysts = sorted(list(set([r.buyer if r.buyer else "Não definido" for r in reqs])))
            selected_analyst = st.multiselect("🔍 Filtrar por Analista", all_analysts, default=all_analysts, key="mgr_filter_analyst")
            filtered_reqs = [r for r in reqs if (r.buyer if r.buyer else "Não definido") in selected_analyst]
            st.markdown("---")

        # Barra de Ações do Topo (Exportar)
        if filtered_reqs:
            import io
            df_exp = pd.DataFrame([asdict(r) for r in filtered_reqs])
            # Ordenar e renomear
            cols_to_exp = ['subelement', 'date_opening', 'description', 'rc_code', 'buyer', 'situation', 'po_number', 'nf_tracking']
            df_exp = df_exp[cols_to_exp]
            df_exp.columns = ['Subelemento', 'Data Abertura', 'Descrição', 'Código RC', 'Comprador', 'Situação', 'Nº Pedido', 'Status NF']
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_exp.to_excel(writer, index=False, sheet_name='Requisições')
            
            st.download_button(
                label="📥 Exportar Visão Atual para Excel",
                data=output.getvalue(),
                file_name=f"requisicoes_{user_id}_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        # CSS para a Tabela Monday Style
        st.markdown("""
            <style>
            .req-table-header {
                display: flex;
                background: rgba(15, 23, 42, 0.6);
                padding: 10px 15px;
                border-radius: 8px 8px 0 0;
                font-size: 0.75rem;
                font-weight: 700;
                color: #94a3b8;
                text-transform: uppercase;
                border: 1px solid rgba(255,255,255,0.05);
                margin-bottom: 5px;
            }
            .req-row {
                background: rgba(255, 255, 255, 0.02);
                padding: 5px 10px;
                border: 1px solid rgba(255,255,255,0.05);
                margin-bottom: 2px;
                transition: all 0.2s ease;
            }
            .req-row:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(99, 102, 241, 0.3);
            }
            .add-btn {
                color: #6366f1;
                cursor: pointer;
                font-size: 0.85rem;
                font-weight: 600;
                padding: 10px;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            </style>
        """, unsafe_allow_html=True)

        # Definição de Colunas Refinada
        # [Subelemento, Data, Descrição, Cód RC, Comprador, Situação, Anexos, PO, NF Track, NF Anx, Ações]
        cols_spec = [1.3, 0.9, 1.8, 1.0, 1.0, 1.3, 0.6, 1.0, 1.4, 0.6, 0.8]
        
        # Header
        h_cols = st.columns(cols_spec)
        headers = ["Subelemento", "Data RC", "Descrição", "Código-RC", "Comprador", "Situação", "Anx", "Nº Pedido", "NF Acomp.", "NF", "Ações"]
        for col, head in zip(h_cols, headers):
            col.markdown(f"<div style='font-size:0.65rem; color:#64748b; text-transform:uppercase; font-weight:800; letter-spacing:0.5px;'>{head}</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # Listagem de Requisições
        for i, r in enumerate(filtered_reqs):
            with st.container():
                r_cols = st.columns(cols_spec)
                
                # Subelemento
                new_sub = r_cols[0].text_input("Sub", value=r.subelement, key=f"req_sub_{r.id}", label_visibility="collapsed")
                if new_sub != r.subelement:
                    r.subelement = new_sub
                    dm.save_requests(reqs)

                # Data RC
                try:
                    d_val = datetime.strptime(r.date_opening, "%Y-%m-%d")
                except: d_val = datetime.now()
                new_date = r_cols[1].date_input("Data", value=d_val, key=f"req_date_{r.id}", label_visibility="collapsed")
                if new_date.strftime("%Y-%m-%d") != r.date_opening:
                    r.date_opening = new_date.strftime("%Y-%m-%d")
                    dm.save_requests(reqs)

                # Descrição
                new_desc = r_cols[2].text_input("Desc", value=r.description, key=f"req_desc_{r.id}", label_visibility="collapsed")
                if new_desc != r.description:
                    r.description = new_desc
                    dm.save_requests(reqs)

                # Código RC
                new_rc = r_cols[3].text_input("RC", value=r.rc_code, key=f"req_rc_{r.id}", label_visibility="collapsed")
                if new_rc != r.rc_code:
                    r.rc_code = new_rc
                    dm.save_requests(reqs)

                # Comprador
                # Buscar analistas disponíveis ou permitir texto
                ans = sorted(list(set([t.responsible for t in st.session_state.get("tasks", []) if t.responsible])))
                try:
                    def_idx = ans.index(r.buyer) + 1 if r.buyer in ans else 0
                except: def_idx = 0
                
                new_buyer = r_cols[4].selectbox("Comp", ["-"] + ans, index=def_idx, key=f"req_buy_{r.id}", label_visibility="collapsed")
                if new_buyer != r.buyer:
                    r.buyer = new_buyer if new_buyer != "-" else ""
                    dm.save_requests(reqs)

                # Situação RC
                situations = ["Pendente", "Em andamento", "Para revisão", "Concluído"]
                try:
                    s_idx = situations.index(r.situation)
                except: s_idx = 0
                new_sit = r_cols[5].selectbox("Sit", situations, index=s_idx, key=f"req_sit_{r.id}", label_visibility="collapsed")
                if new_sit != r.situation:
                    r.situation = new_sit
                    dm.save_requests(reqs)

                # Anexos RC (POPOVER PARA UPLOAD)
                with r_cols[6]:
                    with st.popover("📎" if r.attachments else "➕", use_container_width=True):
                        st.markdown("**Anexos da RC**")
                        if r.attachments:
                            for file_path in r.attachments:
                                fn = os.path.basename(file_path)
                                st.markdown(f"✅ {fn}")
                        
                        uploaded = st.file_uploader("Upload", key=f"up_rc_{r.id}", label_visibility="collapsed")
                        if uploaded:
                            # Salvar arquivo
                            save_dir = "attachments/requests"
                            os.makedirs(save_dir, exist_ok=True)
                            f_path = os.path.join(save_dir, f"{r.id}_{uploaded.name}")
                            with open(f_path, "wb") as f:
                                f.write(uploaded.getbuffer())
                            r.attachments.append(f_path)
                            dm.save_requests(reqs)
                            st.rerun()

                # Número Pedido
                new_po = r_cols[7].text_input("PO", value=r.po_number, key=f"req_po_{r.id}", label_visibility="collapsed")
                if new_po != r.po_number:
                    r.po_number = new_po
                    dm.save_requests(reqs)

                # NF Acompanhamento
                nf_opts = ["Aguardando recebimento", "Recebido - Pago", "Pendente Fiscal", "Cancelado"]
                try:
                    n_idx = nf_opts.index(r.nf_tracking)
                except: n_idx = 0
                new_nf_t = r_cols[8].selectbox("NFT", nf_opts, index=n_idx, key=f"req_nft_{r.id}", label_visibility="collapsed")
                if new_nf_t != r.nf_tracking:
                    r.nf_tracking = new_nf_t
                    dm.save_requests(reqs)

                # NF Anexo (POPOVER PARA UPLOAD)
                with r_cols[9]:
                    with st.popover("📄" if r.nf_attachments else "➕", use_container_width=True):
                        st.markdown("**Anexos de NF**")
                        if r.nf_attachments:
                            for file_path in r.nf_attachments:
                                fn = os.path.basename(file_path)
                                st.markdown(f"✅ {fn}")
                        
                        uploaded_nf = st.file_uploader("Upload NF", key=f"up_nf_{r.id}", label_visibility="collapsed")
                        if uploaded_nf:
                            save_dir = "attachments/nf"
                            os.makedirs(save_dir, exist_ok=True)
                            f_path = os.path.join(save_dir, f"{r.id}_{uploaded_nf.name}")
                            with open(f_path, "wb") as f:
                                f.write(uploaded_nf.getbuffer())
                            r.nf_attachments.append(f_path)
                            dm.save_requests(reqs)
                            st.rerun()

                # Ações
                act_cols = r_cols[10].columns(2)
                # Botão Editar (Abre um expander ou modal rápido)
                if act_cols[0].button("✏️", key=f"req_ed_btn_{r.id}", help="Editar detalhes"):
                    st.session_state[f"editing_req_{r.id}"] = not st.session_state.get(f"editing_req_{r.id}", False)

                if act_cols[1].button("🗑️", key=f"req_del_btn_{r.id}", help="Excluir"):
                    st.session_state.requests.pop(i)
                    dm.save_requests(st.session_state.requests)
                    st.rerun()
            
            # Formulário de edição expandido se ativo
            if st.session_state.get(f"editing_req_{r.id}"):
                with st.form(f"form_edit_req_{r.id}"):
                    st.markdown(f"### ✏️ Editar Detalhes - {r.subelement}")
                    e_sub = st.text_input("Subelemento", value=r.subelement)
                    e_desc = st.text_area("Descrição Detalhada", value=r.description)
                    e_rc = st.text_input("Código RC", value=r.rc_code)
                    e_po = st.text_input("Número do Pedido", value=r.po_number)
                    
                    if st.form_submit_button("💾 Salvar Tudo"):
                        r.subelement = e_sub
                        r.description = e_desc
                        r.rc_code = e_rc
                        r.po_number = e_po
                        dm.save_requests(reqs)
                        st.session_state[f"editing_req_{r.id}"] = False
                        st.rerun()

        # Botão + Adicionar subelemento (Estilo Linha Final)
        st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Adicionar nova requisição", use_container_width=True, type="secondary"):
            user_name = st.session_state.get("user_name", "Analista")
            new_req = RequestRC(subelement="RC", description="", rc_code="", buyer=user_name, situation="Pendente")
            st.session_state.requests.append(new_req)
            dm.save_requests(st.session_state.requests)
            st.rerun()

        st.markdown(
            """
            <div style="margin-top: 30px; font-size: 0.8rem; color: #64748b;">
                💡 <b>Dica:</b> As alterações são salvas automaticamente ao mudar de campo ou selecionar uma opção.
            </div>
            """, unsafe_allow_html=True
        )


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
                        sel = st.selectbox("📂 Tema / Quadro", options, key="new_task_category")
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
        
        /* 2. BUTTONS: DARK SLATE, WHITE TEXT, VISIBLE BORDER (Global Fix) */
        .stButton > button {
            background-color: #1e293b !important; /* Slate 800 */
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 8px !important;
            transition: transform 0.1s ease, background-color 0.2s !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        }
        
        .stButton > button:hover {
            background-color: #334155 !important; /* Slate 700 */
            border-color: #ffffff !important;
            color: #ffffff !important;
            transform: scale(1.02);
            box-shadow: 0 4px 8px rgba(0,0,0,0.5) !important;
        }
        
        .stButton > button:active, .stButton > button:focus {
            background-color: #6366f1 !important; /* Indigo for Click */
            border-color: #ffffff !important;
            color: #ffffff !important;
        }

        /* 3. TASK CARDS: STRONG WHITE BORDER */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 2px solid #ffffff !important;
            -webkit-box-shadow: 0 0 0 1px #ffffff !important; /* Backup Border via Shadow */
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3), 0 0 0 1px #ffffff !important;
            background-color: rgba(30, 41, 59, 0.3) !important;
        }
        
        /* 4. TOASTS & ALERTS: HIGH CONTRAST */
        div[data-testid="stToast"], div[data-testid="stAlert"], div.stToast {
            background-color: #0f172a !important;
            color: #ffffff !important;
            border: 1px solid white !important;
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
        div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3, div[role="dialog"] label {
             color: #f8fafc !important;
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
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text-main);
            margin: 0;
            letter-spacing: -1px;
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
         
         if (page in ["Quadros", "Kanban"]) or (is_admin_or_manager and page in ["Calendário", "Painel", "Follow-Up"]):
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
        "Kanban": KanbanView,
        "Requisições": RequestsView,
        "Follow-Up": FollowUpView,
        "Gestão": ManagerDashboardView,
    }
    
    if page in views:
        views[page].render(all_tasks)

if __name__ == "__main__":
    main()

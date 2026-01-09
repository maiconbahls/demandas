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

CATEGORY_OPTIONS = {
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
    id: int = field(default_factory=lambda: int(time.time() * 1000))
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def __post_init__(self):
        if not self.title or not self.title.strip():
            raise ValueError("Título é obrigatório")
        if isinstance(self.due_date, (datetime, date)):
            self.due_date = self.due_date.strftime("%Y-%m-%d")
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data["dueDate"] = data.pop("due_date")
        data["createdAt"] = data.pop("created_at")
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            title=data.get("title", ""),
            responsible=data.get("responsible", "Maicon"),
            category=data.get("category", "Outros"),
            priority=data.get("priority", "Média"),
            status=data.get("status", "Pendente"),
            due_date=data.get("dueDate", datetime.now().strftime("%Y-%m-%d")),
            description=data.get("description", ""),
            attachments=data.get("attachments", []),
            id=data.get("id", int(time.time() * 1000)),
            created_at=data.get("createdAt", datetime.now().strftime("%Y-%m-%d")),
        )
    
    def is_urgent_today(self) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.priority == "Urgente" and self.status != "Concluído" and self.due_date == today
    
    def get_category_info(self) -> Dict:
        for key, info in CATEGORY_OPTIONS.items():
            if info["name"] == self.category or key == self.category:
                return info
        return CATEGORY_OPTIONS["📋 Outros"]

# ==========================================
# GERENCIADOR DE DADOS
# ==========================================

class DataManager:
    def __init__(self, file_path: str = DATA_FILE):
        self.file_path = file_path
        self.updates_path = UPDATES_FILE
    
    # ---- Tarefas ----
    def load_tasks(self) -> List[Task]:
        if not os.path.exists(self.file_path):
            return self._create_initial_data()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Task.from_dict(item) for item in data]
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return []
    
    def save_tasks(self, tasks: List[Task]) -> bool:
        try:
            data = [t.to_dict() for t in tasks]
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")
            return False
    
    def _create_initial_data(self) -> List[Task]:
        initial_tasks = [
            Task(
                title="Revisar documentação do programa",
                responsible="Maicon",
                category="Bolsas de Estudos",
                priority="Média",
                status="Em Andamento",
                due_date="2026-01-10",
                description="Atualizar documentação para o semestre 2026/1"
            ),
            Task(
                title="Maria Silva - Dúvida sobre inscrição",
                responsible="Maicon",
                category="Pessoas/Atendimentos",
                priority="Alta",
                status="Pendente",
                due_date="2026-01-07",
                description="Maria precisa de orientação"
            )
        ]
        self.save_tasks(initial_tasks)
        return initial_tasks
    
    # ---- Updates ----
    def load_updates(self) -> List[TaskUpdate]:
        if not os.path.exists(self.updates_path):
            return []
        try:
            with open(self.updates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [TaskUpdate.from_dict(item, idx) for idx, item in enumerate(data)]
        except Exception:
            return []
    
    def save_updates(self, updates: List[TaskUpdate]) -> bool:
        try:
            data = [u.to_dict() for u in updates]
            with open(self.updates_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
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

def buscar_colaborador_por_matricula(matricula: str) -> Dict:
    """Busca dados do colaborador no arquivo gestores.xlsx pela matrícula."""
    if not matricula or not matricula.strip():
        return {}
    
    try:
        # Limpar matrícula
        matricula_clean = str(matricula).strip()
        
        if not os.path.exists(GESTORES_FILE):
            return {}
        
        df = pd.read_excel(GESTORES_FILE)
        
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
        "Timeline": "⏳",
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
        div.stButton > button {
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
            background: rgba(255,255,255,0.03) !important;
            transition: all 0.3s ease !important;
            height: 42px !important;
        }
        div.stButton > button:hover {
            background: rgba(255,255,255,0.08) !important;
            border-color: rgba(99, 102, 241, 0.5) !important;
            transform: translateY(-2px);
        }
        
        /* Botão Ativo */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
            border: none !important;
        }

        /* Inputs (Select e Text) */
        div[data-testid="stSelectbox"] > div > div, 
        div[data-testid="stTextInput"] > div > div {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
            border-radius: 12px !important;
            height: 42px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        cols = st.columns([0.62, 0.13, 0.15, 0.10])
        
        # 1. Navigation
        with cols[0]:
            nav_cols = st.columns(len(cls.NAV_OPTIONS))
            for idx, (page, icon) in enumerate(cls.NAV_OPTIONS.items()):
                with nav_cols[idx]:
                    active = st.session_state.selected_page == page
                    if st.button(
                        f"{icon} {page}",
                        key=f"nav_{page}",
                        use_container_width=True,
                        type="primary" if active else "secondary",
                    ):
                        st.session_state.selected_page = page
                        st.rerun()
        
        # 2. Filter
        with cols[1]:
            all_categories = ["Todos"] + [info["name"] for info in CATEGORY_OPTIONS.values()]
            selected_category = st.selectbox(
                "Quadro",
                options=all_categories,
                index=0,
                label_visibility="collapsed",
                key="category_filter",
            )

        # 3. Search
        with cols[2]:
            search_query = st.text_input(
                "Pesquisar",
                placeholder="🔍 Buscar...",
                label_visibility="collapsed",
                key="search_input",
            )
        
        # 4. Nova Button
        with cols[3]:
            if st.button("➕ Nova", type="primary", use_container_width=True):
                st.session_state.show_modal = True
        
        return search_query, st.session_state.selected_page, selected_category


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
            marker=dict(line=dict(color="#0f172a", width=3)),
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
        
        dm = DataManager()
        
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
            
            /* Card de Tarefa (Container com Borda) - Estilo Premium */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: linear-gradient(160deg, rgba(37, 42, 64, 0.8) 0%, rgba(30, 34, 53, 0.8) 100%) !important;
                border: 1px solid rgba(100, 116, 139, 0.2) !important;
                border-radius: 16px !important;
                padding: 12px 16px !important;
                margin-bottom: 12px !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
                transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            }
            
            div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.2) !important;
                border-color: rgba(87, 155, 252, 0.3) !important;
                background: linear-gradient(160deg, rgba(42, 48, 74, 0.9) 0%, rgba(35, 39, 62, 0.9) 100%) !important;
            }

            /* Botões de Ação (Ícones) - Estilo Ghost/Minimalista */
            div[data-testid="column"] button {
                padding: 0px !important;
                min-height: 36px !important;
                height: 36px !important;
                width: 100% !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                background-color: rgba(255,255,255,0.03) !important;
                border-radius: 8px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: all 0.2s ease;
                color: rgba(255, 255, 255, 0.6) !important;
            }

            div[data-testid="column"] button:hover {
                background-color: rgba(255, 255, 255, 0.1) !important;
                color: white !important;
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

    @classmethod
    def _process_description(cls, task: Task, info: Dict) -> str:
        if not task.description:
            return ""
        
        # Lógica para DADOS DO COLABORADOR e ATENDIMENTO
        if "DADOS DO COLABORADOR" in task.description or "DADOS DO ATENDIMENTO" in task.description:
            lines = task.description.split('\n')
            current_section = None
            section_buffer = []

            def flush_buffer(buffer, section_name, color):
                if not buffer: return ""
                html = f"<div style='font-size:0.75rem;color:{color};font-weight:800;margin-bottom:4px;text-transform:uppercase;'>{section_name}</div>"
                html += "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;'>"
                for item in buffer:
                    html += f"<span style='background:rgba(255,255,255,0.08);padding:4px 8px;border-radius:4px;font-size:0.75rem;color:#e0e0e0;border:1px solid rgba(255,255,255,0.1);'>{item}</span>"
                html += "</div>"
                return html

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
            return f"<div style='background:rgba(255,255,255,0.03); padding:16px; border-radius:12px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.08);'>{final_html}</div>"
        
        return f"<div style='background:rgba(255,255,255,0.05); padding:12px; border-radius:8px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.1);'><div style=\"color:#c5c7d0;font-size:0.85rem;line-height:1.4;\">{task.description}</div></div>"

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
        
        dm = DataManager()
        
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
                            <span style="color:{info['color']};font-weight:700;font-size:1rem;text-transform:uppercase;letter-spacing:0.5px;">
                                {cat_name}
                            </span>
                            <span style="color:#9699a6;font-size:0.85rem;">
                                {total} atividades
                            </span>
                        </div>
                        <div style="color:#9699a6;font-size:0.85rem;">
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
                    # Header do Card (HTML)
                    st.markdown(
                        f"""
                        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:8px;">
                            <span style="font-size:2rem;">{info['icon']}</span>
                            <div style="flex:1;">
                                <div style="color:{info['color']};font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:2px;">
                                    {info['name']}
                                </div>
                                <div style="color:white;font-size:1.1rem;font-weight:700;line-height:1.2;">{task.title}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Descrição (HTML incorporado)
                    if task.description:
                        # [Lógica simplificada para manter o código limpo aqui, ou reutilizar o que já existe]
                        # Reutilizando a lógica de processamento de descrição que já estava no código
                        desc_html = cls._process_description(task, info) # Vou criar esse helper
                        st.markdown(desc_html, unsafe_allow_html=True)
                    else:
                         st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

                    # Área Interativa (Widgets Streamlit) - Envolvida em container para escopo CSS
                    st.markdown('<div class="task-footer-columns">', unsafe_allow_html=True)
                    c_resp, c_date, c_stat, c_prio, c_acts = st.columns([0.15, 0.15, 0.18, 0.18, 0.34])
                    
                    with c_resp:
                        st.markdown(f'<div class="footer-badge">👤 {task.responsible}</div>', unsafe_allow_html=True)
                    
                    with c_date:
                        st.markdown(f'<div class="footer-badge">📅 {due_str[:5]}</div>', unsafe_allow_html=True)

                    with c_stat:
                        new_status = st.selectbox("Status", list(STATUS_CONFIG.keys()), index=list(STATUS_CONFIG.keys()).index(task.status), key=f"st_{task.id}", label_visibility="collapsed")
                        if new_status != task.status:
                            task.status = new_status
                            DataManager().save_tasks(st.session_state.tasks)
                            st.rerun()

                    with c_prio:
                        new_prio = st.selectbox("Prioridade", list(PRIORITY_CONFIG.keys()), index=list(PRIORITY_CONFIG.keys()).index(task.priority), key=f"pr_{task.id}", label_visibility="collapsed")
                        if new_prio != task.priority:
                            task.priority = new_prio
                            DataManager().save_tasks(st.session_state.tasks)
                            st.rerun()

                    with c_acts:
                         col_del, col_edit, col_exp = st.columns([0.33, 0.33, 0.34])
                         with col_del:
                             if st.button("🗑️", key=f"del_{task.id}", help="Excluir", use_container_width=True):
                                 st.session_state.tasks = [t for t in st.session_state.tasks if t.id != task.id]
                                 DataManager().save_tasks(st.session_state.tasks)
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
                    st.markdown('</div>', unsafe_allow_html=True)
                
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
                
                # Container de tarefas visíveis (primeiras 3)
                html += "<div class='calendar-tasks-visible'>"
                for t in day_tasks[:3]:
                    info = t.get_category_info()
                    prio_color = PRIORITY_CONFIG[t.priority]['color']
                    title = t.title[:20] + "..." if len(t.title) > 20 else t.title
                    html += f"<div class='task-item' style='border-left-color:{prio_color};background:{PRIORITY_CONFIG[t.priority]['bg']};'>{info['icon']} {title}</div>"
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
                        html += f"<div class='tooltip-task' style='border-left-color:{prio_color};'>"
                        html += f"<span class='tooltip-icon'>{info['icon']}</span>"
                        html += f"<span class='tooltip-title'>{title}</span>"
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
                
                # Construir HTML total da coluna para evitar tags órfãs
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
                                    box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 4px solid {info['color']};" class="kanban-card-hover">
                            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                                <span style="font-size:0.6rem; color:{info['color']}; font-weight:800; text-transform:uppercase; letter-spacing:0.5px;">{info['name']}</span>
                                <div style="display:flex; align-items:center; gap:4px; background:{pc['color']}15; padding:2px 8px; border-radius:4px; border:1px solid {pc['color']}30;">
                                    <div style="width:6px; height:6px; background:{pc['color']}; border-radius:50%;"></div>
                                    <span style="font-size:0.6rem; color:{pc['color']}; font-weight:700;">{t.priority}</span>
                                </div>
                            </div>
                            <div style="color:#f8fafc; font-size:0.85rem; font-weight:600; line-height:1.4; margin-bottom:14px; min-height:2.4em;">{t.title}</div>
                            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid rgba(255,255,255,0.05); padding-top:10px; opacity:0.7;">
                                <span style="font-size:0.7rem; color:#94a3b8; font-weight:600;">📅 {due}</span>
                                <span style="font-size:0.7rem; color:#94a3b8; font-weight:600;">👤 {t.responsible.split()[0]}</span>
                            </div>
                        </div>
                    """)
                
                column_html += "</div>"
                st.markdown(column_html, unsafe_allow_html=True)


class TimelineView:
    @staticmethod
    def _render_smart_description(description: str, primary_color: str) -> str:
        if not description:
            return ""
            
        def flush_buffer(buffer, section_name, color):
            if not buffer: return ""
            html = f"<div style='font-size:0.75rem;color:{color};font-weight:800;margin-bottom:4px;text-transform:uppercase;'>{section_name}</div>"
            html += "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;'>"
            for item in buffer:
                html += f"<span style='background:rgba(255,255,255,0.08);padding:4px 8px;border-radius:4px;font-size:0.75rem;color:#e0e0e0;border:1px solid rgba(255,255,255,0.1);'>{item}</span>"
            html += "</div>"
            return html

        # Verificação simples para texto estruturado
        if "DADOS DO COLABORADOR" in description or "DADOS DO ATENDIMENTO" in description:
            lines = description.split('\n')
            final_html = ""
            current_section = None
            section_buffer = []

            for line in lines:
                line = line.strip()
                if not line: continue
                
                upper_line = line.upper()

                # Verifica headers PRIMEIRO (mesmo que tenham underscores)
                if 'DADOS DO ATENDIMENTO' in upper_line:
                    final_html += flush_buffer(section_buffer, current_section, primary_color)
                    current_section = "📋 DADOS ATEND."
                    section_buffer = []
                    continue
                elif 'DADOS DO COLABORADOR' in upper_line:
                    final_html += flush_buffer(section_buffer, current_section, primary_color)
                    current_section = "👤 DADOS COLAB."
                    section_buffer = []
                    continue
                
                # Remove linhas que são puramente separadores
                if set(line).issubset(set('_- ═')):
                     continue
                     
                if line.startswith('📂 Categoria:'):
                     continue
                else:
                    # Limpa caracteres de lista ou separadores no início
                    cleaned = line.lstrip('_-=═• ').strip()
                    if cleaned:
                        section_buffer.append(cleaned)
            
            final_html += flush_buffer(section_buffer, current_section, primary_color)
            return f"<div style='margin-bottom:16px;'>{final_html}</div>"
        
        else:
            # Texto simples
            return f'<div style="color:#c5c7d0;font-size:0.9rem;line-height:1.6;margin-bottom:16px;">{description}</div>'


    @classmethod
    def render(cls, tasks: List[Task]) -> None:
        if not tasks:
            st.info("Nenhuma tarefa encontrada.")
            return
        
        # Inicializar estado para histórico expandido
        if "timeline_expanded_history" not in st.session_state:
            st.session_state.timeline_expanded_history = set()
        
        dm = DataManager()
        
        try:
            c1, c2, c3 = st.columns(3)
            with c1:
                cats = sorted(list(set([t.category for t in tasks if t.category])))
                if not cats: cats = ["Geral"]
                f_cat = st.multiselect("📂 Tema", cats, default=cats, key="tl_cat")
            with c2:
                sts = sorted(list(set([t.status for t in tasks if t.status])))
                if not sts: sts = list(STATUS_CONFIG.keys())
                f_st = st.multiselect("🎯 Status", sts, default=sts, key="tl_st")
            with c3:
                pr_options = ["Baixa", "Média", "Alta", "Urgente"]
                f_pr = st.multiselect("⚡ Prioridade", pr_options, default=pr_options, key="tl_pr")
            st.markdown("<br>", unsafe_allow_html=True)
            flt = [
                t for t in tasks 
                if (not f_cat or t.category in f_cat) 
                and (not f_st or t.status in f_st) 
                and (not f_pr or t.priority in f_pr)
            ]
        except Exception as e:
            st.error(f"Erro nos filtros: {e}")
            flt = []
        if not flt:
            st.warning("Nenhuma tarefa com os filtros.")
            return
        # Ordenação segura
        def safe_date_sort(t):
            try:
                return t.due_date
            except:
                return "9999-12-31"
        
        ordered = sorted(flt, key=safe_date_sort)
        
        st.markdown(f"### ⏳ Timeline ({len(ordered)} atividades)")
        st.markdown("<br>", unsafe_allow_html=True)
        
        for t in ordered:
            info = t.get_category_info()
            s_info = STATUS_CONFIG.get(t.status, {'color': '#999', 'bg': '#333', 'text': '#fff'})
            
            try:
                due = datetime.strptime(t.due_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                due = t.due_date
            
            st.markdown(
                f"""
                <div style='display:flex; gap:20px; margin-bottom:10px;'>
                    <div style='display:flex; flex-direction:column; align-items:center; width:20px;'>
                        <div style='width:12px; height:12px; background:#579bfc; border-radius:50%; box-shadow:0 0 10px #579bfc80; z-index:2;'></div>
                        <div style='width:2px; flex:1; background:rgba(255,255,255,0.1); margin-top:5px;'></div>
                    </div>
                    <div style='flex:1; background:linear-gradient(135deg, {info['bg']}40 0%, rgba(255,255,255,0.05) 100%); 
                                border:1px solid rgba(255,255,255,0.08); border-left:4px solid {info['color']}; 
                                border-radius:12px; padding:18px; box-shadow:0 10px 30px rgba(0,0,0,0.2);'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:10px;'>
                            <span style='color:{info['color']}; font-weight:800; font-size:0.75rem; text-transform:uppercase;'>{info['name']}</span>
                            <span style='color:#9699a6; font-size:0.8rem; font-weight:600;'>📅 {due}</span>
                        </div>
                        <h4 style='color:white; margin:0 0 12px 0; font-size:1.1rem; letter-spacing:-0.5px;'>{t.title}</h4>
                        {cls._render_smart_description(t.description, info['color'])}
                        <div style='display:flex; gap:10px; align-items:center; margin-top:10px;'>
                            <div style='background:rgba(255,255,255,0.05); padding:4px 10px; border-radius:6px; font-size:0.75rem; color:white;'>
                                👤 {t.responsible}
                            </div>
                            <div style='background:{s_info['bg']}; color:{s_info['text']}; padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:700;'>
                                {t.status}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

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
        
        dm = DataManager()
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
            # Filtrar opções - remover Pessoas/Atendimentos do seletor normal (terá opção separada)
            options = [k for k in CATEGORY_OPTIONS.keys() if CATEGORY_OPTIONS[k]["name"] != "Pessoas/Atendimentos"]
            
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
                sel = st.selectbox("📂 Tema / Quadro", options, key="new_task_category")
                cat_name = CATEGORY_OPTIONS[sel]["name"]
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
                            
                            t = Task(
                                title=final_title,
                                responsible="Maicon",
                                category=cat_name,
                                priority=priority,
                                status="Pendente",
                                due_date=due_date.strftime("%Y-%m-%d"),
                                description=desc_final,
                                attachments=saved_attachments
                            )
                            st.session_state.tasks.append(t)
                            DataManager().save_tasks(st.session_state.tasks)
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

# ==========================================
# CSS
# ==========================================

def load_custom_css() -> None:
    # Configuração do Fundo (Imagem ou Gradiente)
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

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
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
            padding-top: 1rem !important; /* Ajuste para subir o conteúdo já que removemos o header */
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

        /* KPI CARDS - COMPACT DESIGN */
        .kpi-card {
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s ease;
            height: 110px;
            width: 100%;
        }
        .kpi-card:hover { transform: translateY(-3px); border-color: var(--accent-primary); }
        .kpi-icon-container {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .kpi-icon { font-size: 1.2rem; }
        .kpi-label { font-size: 0.65rem; color: var(--text-dim); font-weight: 700; text-transform: uppercase; margin-bottom: 2px; }
        .kpi-value { font-size: 1.4rem; font-weight: 800; color: var(--text-main); line-height: 1; }
        .kpi-glow { display: none; }

        .chart-container {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 24px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            overflow: visible;
        }

        /* Container de Borda Nativo do Streamlit */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--bg-card) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
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
            background: rgba(30, 41, 59, 0.8);
            border-color: var(--accent-primary); 
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
            transition: all 0.2s ease;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 500;
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
        .kanban-card:hover { transform: translateY(-3px); border-color: var(--accent-primary); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
        .kanban-card-title { font-size: 0.9rem; font-weight: 700; color: var(--text-main); margin-bottom: 10px; line-height: 1.3; }
        .kanban-card-meta { display: flex; align-items: center; gap: 10px; font-size: 0.75rem; color: var(--text-dim); }
        .kanban-priority-badge { font-size: 0.65rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
        </style>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# APP
# ==========================================

def initialize_app() -> None:
    st.set_page_config(**PAGE_CONFIG)
    load_custom_css()
    dm = DataManager()
    if "tasks" not in st.session_state:
        st.session_state.tasks = dm.load_tasks()
    if "show_modal" not in st.session_state:
        st.session_state.show_modal = False
    if "show_updates_for_task" not in st.session_state:
        st.session_state.show_updates_for_task = None
    if "selected_tasks" not in st.session_state:
        st.session_state.selected_tasks = set()
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "Quadros"


def main() -> None:
    initialize_app()
    
    search, page, cat_filter = NavigationSystem.render()
    UIComponents.render_page_header(page)
    
    # Modais
    NewTaskModal.render()
    UpdatesModal.render()
    
    # Filtro geral por quadro e busca
    all_tasks: List[Task] = st.session_state.tasks
    if cat_filter != "Todos":
        all_tasks = [t for t in all_tasks if t.category == cat_filter]
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
        "Timeline": TimelineView,
        "Follow-Up": FollowUpView,
    }
    
    if page in views:
        views[page].render(all_tasks)

    # Modal de Edição de Atividade (Global)
    editing_id = st.session_state.get("editing_task_id")
    if editing_id:
        task_to_edit = next((t for t in st.session_state.tasks if t.id == editing_id), None)
        if task_to_edit:
            with st.expander("✏️ Editar Atividade", expanded=True):
                with st.form("form_edit_task"):
                    e_title = st.text_input("Título", value=task_to_edit.title)
                    e_desc = st.text_area("Descrição", value=task_to_edit.description, height=150)
                    e_prio = st.selectbox("Prioridade", list(PRIORITY_CONFIG.keys()), index=list(PRIORITY_CONFIG.keys()).index(task_to_edit.priority))
                    e_due = st.date_input("Prazo", value=datetime.strptime(task_to_edit.due_date, "%Y-%m-%d"))
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                            task_to_edit.title = e_title
                            task_to_edit.description = e_desc
                            task_to_edit.priority = e_prio
                            task_to_edit.due_date = e_due.strftime("%Y-%m-%d")
                            dm = DataManager()
                            dm.save_tasks(st.session_state.tasks)
                            st.session_state.editing_task_id = None
                            st.success("Alterações salvas!")
                            time.sleep(0.5)
                            st.rerun()
                    with c2:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.editing_task_id = None
                            st.rerun()


if __name__ == "__main__":
    main()

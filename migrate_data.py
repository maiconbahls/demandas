import json
import gspread
import toml
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def migrate():
    print("--- INICIANDO MIGRACAO DE DADOS ---")
    
    # 1. Carregar Credenciais
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("[ERRO] Arquivo de segredos nao encontrado.")
        return

    try:
        with open(secrets_path, encoding='utf-8') as f:
            secrets = toml.load(f)
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets["gcp_service_account"], scope)
        gc = gspread.authorize(creds)
        
        sheet_name = secrets.get("SHEET_NAME", "FlowData")
        print(f"... Conectando a planilha '{sheet_name}'...")
        sh = gc.open(sheet_name)
        print("[OK] Conexao estabelecida!")
        
    except Exception as e:
        print(f"[ERRO] Erro na conexao: {e}")
        return

    # 2. Migrar TAREFAS (Tasks)
    try:
        if os.path.exists("flow_data.json"):
            print("\n... Migrando TAREFAS (flow_data.json)...")
            with open("flow_data.json", "r", encoding="utf-8") as f:
                tasks_data = json.load(f)
            
            if tasks_data:
                # Prepara dados para garantir formato string nos arrays
                formatted_tasks = []
                for t in tasks_data:
                    t_copy = t.copy()
                    if 'attachments' in t_copy:
                        t_copy['attachments'] = str(t_copy['attachments'])
                    formatted_tasks.append(t_copy)
                
                # Definir headers baseados nas chaves do primeiro item
                headers = list(formatted_tasks[0].keys())
                rows = [list(item.values()) for item in formatted_tasks]
                
                # Obter ou criar aba Tasks
                try: ws = sh.worksheet("Tasks")
                except: ws = sh.add_worksheet("Tasks", 1000, 10)
                
                ws.clear()
                ws.append_row(headers)
                ws.append_rows(rows)
                print(f"[OK] {len(rows)} tarefas migradas com sucesso!")
            else:
                print("[AVISO] Arquivo de tarefas vazio.")
        else:
            print("[AVISO] Arquivo flow_data.json nao encontrado.")
            
    except Exception as e:
        print(f"[ERRO] Erro ao migrar tarefas: {e}")

    # 3. Migrar HISTORICO (Updates)
    try:
        if os.path.exists("flow_updates.json"):
            print("\n... Migrando HISTORICO (flow_updates.json)...")
            with open("flow_updates.json", "r", encoding="utf-8") as f:
                updates_data = json.load(f)
            
            if updates_data:
                # Adicionar IDs se nao tiverem (para compatibilidade)
                formatted_updates = []
                for idx, u in enumerate(updates_data):
                    u_copy = u.copy()
                    if 'id' not in u_copy:
                        u_copy['id'] = int(datetime.now().timestamp() * 1000) + idx
                    formatted_updates.append(u_copy)
                
                headers = list(formatted_updates[0].keys())
                rows = [list(item.values()) for item in formatted_updates]
                
                try: ws = sh.worksheet("Updates")
                except: ws = sh.add_worksheet("Updates", 1000, 10)
                
                ws.clear()
                ws.append_row(headers)
                ws.append_rows(rows)
                print(f"[OK] {len(rows)} atualizacoes de historico migradas!")
            else:
                print("[AVISO] Historico vazio.")
        else:
            print("[AVISO] Arquivo flow_updates.json nao encontrado.")
            
    except Exception as e:
        print(f"[ERRO] Erro ao migrar historico: {e}")

    # 4. Migrar REQUISICOES (Requests)
    try:
        if os.path.exists("flow_requests.json"):
            print("\n... Migrando REQUISICOES (flow_requests.json)...")
            with open("flow_requests.json", "r", encoding="utf-8") as f:
                req_data = json.load(f)
                
            if req_data:
                formatted_reqs = []
                for r in req_data:
                    r_copy = r.copy()
                    if 'attachments' in r_copy: r_copy['attachments'] = str(r_copy['attachments'])
                    if 'nf_attachments' in r_copy: r_copy['nf_attachments'] = str(r_copy['nf_attachments'])
                    formatted_reqs.append(r_copy)
                
                headers = list(formatted_reqs[0].keys())
                rows = [list(item.values()) for item in formatted_reqs]
                
                try: ws = sh.worksheet("Requests")
                except: ws = sh.add_worksheet("Requests", 1000, 10)
                
                ws.clear()
                ws.append_row(headers)
                ws.append_rows(rows)
                print(f"[OK] {len(rows)} requisicoes migradas!")
    except Exception as e:
        print(f"[ERRO] Erro ao migrar requisicoes: {e}")

    print("\n--- MIGRACAO CONCLUIDA! PODE ACESSAR O SITE ---")

if __name__ == "__main__":
    migrate()

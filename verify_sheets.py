import toml
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

import traceback

def test_connection():
    print("--- INICIANDO TESTE DE CONEXAO GOOGLE SHEETS ---")
    
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("XXX ERRO: Arquivo .streamlit/secrets.toml NAO encontrado.")
        return

    try:
        # Load secrets manually since we are not running via streamlit run
        with open(secrets_path, encoding='utf-8') as f:
            secrets = toml.load(f)
        print("OK: Arquivo secrets.toml carregado localmente.")
    except Exception as e:
        print(f"XXX ERRO ao ler secrets.toml: {e}")
        return

    if "gcp_service_account" not in secrets:
        print("XXX ERRO: Chave 'gcp_service_account' nao encontrada no secrets.")
        return

    try:
        # Simulate app logic
        print("... Tentando autenticar com Google ...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        print("OK: Autenticacao realizada com sucesso!")

        sheet_name = secrets.get("SHEET_NAME", "FlowData")
        print(f"... Tentando abrir planilha: '{sheet_name}'...")
        
        try:
            sh = gc.open(sheet_name)
            print(f"OK! SUCESSO! Planilha encontrada e aberta.")
            print(f"   ID da Planilha: {sh.id}")
            
            # List worksheets
            ws_list = sh.worksheets()
            print(f"   Abas existentes: {[ws.title for ws in ws_list]}")
            print("\n--- TESTE CONCLUIDO COM SUCESSO ---")
            
        except Exception as inner_e:
            print(f"XXX ERRO AO ABRIR PLANILHA '{sheet_name}': {inner_e}")
            print("... Tentando listar planilhas visiveis para esta conta ...")
            try:
                # Listar arquivos visiveis
                files = gc.list_spreadsheet_files()
                if not files:
                    print("   NENHUMA planilha encontrada. A conta de servico nao tem acesso a nada.")
                else:
                    print("   Planilhas visiveis:")
                    for f in files:
                        print(f"   - {f['name']} (ID: {f['id']})")
                print("\nDICA: Verifique se voce compartilhou a planilha 'FlowData' com o email:")
                print(creds_dict.get('client_email'))
            except Exception as list_e:
                print(f"   Erro ao listar arquivos: {list_e}")
            raise inner_e

    except Exception as e:
        print("\nXXX DETALHES DO ERRO:")
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()

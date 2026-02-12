
import streamlit as st
import pandas as pd
import re

# Mocking parts of the app to load data independently if needed, 
# but easier to just read the python script context if I could.
# Since I can't access user memory directly, I have to rely on what I can read from files.
# But I can try to read the pickle file if it exists, or just simulate the logic.
# Actually, I can just write a script that imports app and prints the task data.

try:
    # Try to load the data from Google Sheets directly using the credentials file if possible,
    # OR better: inspect the local state if I could attached debugger.
    # Since I can't, I will assume the user has the credentials in secrets.toml
    # I will write a script that reads the google sheet directly.
    
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    import toml
    
    # Read secrets
    secrets = toml.load(".streamlit/secrets.toml")
    creds_dict = secrets["gcp_service_account"]
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet = client.open("FlowData").worksheet("Tasks")
    data = sheet.get_all_records()
    
    print("\n--- DIAGNOSTIC RESULT ---")
    for row in data:
        if "Ciclo 2026" in str(row.get("title", "")) or "Pagamento dos Bolsistas" in str(row.get("title", "")):
            print(f"Task: {row.get('title')}")
            print(f"Description (repr): {repr(row.get('description'))}")
            print(f"Collaborators (repr): {repr(row.get('collaborators'))}")
            print(f"Attachments (repr): {repr(row.get('attachments'))}")
            print("-" * 30)

except Exception as e:
    print(f"Error: {e}")

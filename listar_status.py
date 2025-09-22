# Arquivo: listar_status.py
from redminelib import Redmine
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("REDMINE_API_KEY")
REDMINE_URL = 'https://redmine.tjce.jus.br/'

if not API_KEY:
    print("Chave de API não encontrada no .env")
    exit()

redmine = Redmine(REDMINE_URL, key=API_KEY)

print("--- Status de Tarefas Disponíveis no Redmine ---")
try:
    for status in redmine.issue_status.all():
        print(f"ID: {status.id:<5} Nome: {status.name}")
except Exception as e:
    print(f"Ocorreu um erro: {e}")
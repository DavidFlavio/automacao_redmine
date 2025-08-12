# Arquivo: consultar_chamados.py

# --- Bloco 1: Importações ---
import os
from dotenv import load_dotenv
from redminelib import Redmine
from analise import carregar_padroes, encontrar_nota_com_sql
from redmine_acoes import adicionar_nota, adicionar_nota_em_massa
from relatorios import salvar_em_csv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# --- Bloco 2: Configurações e Carregamento ---
load_dotenv()
console = Console()

REDMINE_URL = 'https://redmine.tjce.jus.br/'
API_KEY = os.getenv("REDMINE_API_KEY")
# <<< O USER_ID fixo foi removido daqui >>>
SEARCH_NOTE = 'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
ARQUIVO_PADROES_SQL = 'padroes_sql.json'

# --- Validações Iniciais ---
if not API_KEY:
    console.print("❌ Erro: A variável REDMINE_API_KEY não foi encontrada.", style="bold red")
    exit()

padroes_sql = carregar_padroes(ARQUIVO_PADROES_SQL)
if not padroes_sql:
    console.print("Encerrando o script devido a erro no carregamento dos padrões.", style="bold red")
    exit()

# --- Bloco 3: Conexão ---
try:
    console.print("\nTentando conectar ao Redmine...", style="yellow")
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    console.print("✅ Conexão bem-sucedida!", style="bold green")
except Exception as e:
    console.print(f"❌ Erro ao conectar com o Redmine: {e}", style="bold red")
    exit()

# --- Bloco 4: Lógica Principal ---
try:
    # <<< NOVA FUNCIONALIDADE: Pedindo o ID do usuário no início >>>
    while True:
        try:
            user_id_input = input("\nDigite o ID do usuário do Redmine para a pesquisa: ")
            user_id = int(user_id_input)
            break # Sai do loop se a conversão para inteiro der certo
        except ValueError:
            console.print("❌ Entrada inválida. Por favor, digite apenas números para o ID.", style="bold red")

    console.print(f"\nBuscando chamados para o usuário ID {user_id}...", style="yellow")
    
    issues_do_usuario = redmine.issue.filter(
        assigned_to_id=user_id, # Usando o ID fornecido
        status_id='open',
        include=['journals']
    )

    found_issues = [
        issue for issue in issues_do_usuario 
        if any(
            hasattr(j, 'notes') and j.notes and SEARCH_NOTE.lower() in j.notes.lower() 
            for j in issue.journals
        )
    ]
    
    console.print(f"DEBUG: Após filtrar pela nota gatilho, encontramos {len(found_issues)} chamados para validar.")

    if found_issues:
        console.print(f"\n--- RELATÓRIO DE VALIDAÇÃO DE SCRIPTS SQL ---", style="bold magenta")
        
        for issue in found_issues:
            nota_encontrada = encontrar_nota_com_sql(issue, padroes_sql)
            titulo_painel = f"Chamado #{issue.id} - {issue.subject}"
            
            if nota_encontrada:
                status, border_style, conteudo_painel = (Text("CORRETO", style="bold green"), "green", Syntax(nota_encontrada.strip(), "sql", theme="monokai", line_numbers=True))
            else:
                status, border_style, conteudo_painel = (Text("INCORRETO", style="bold red"), "red", Text("Nenhum script SQL correspondente foi encontrado.", style="italic red"))
            
            console.print(Panel(conteudo_painel, title=titulo_painel, subtitle=status, border_style=border_style))
        
        console.print("\n--- VALIDAÇÃO CONCLUÍDA ---", style="bold magenta")

        # <<< CORREÇÃO: Bloco de Ações Adicionais no lugar certo >>>
        console.print("\n--- AÇÕES ADICIONAIS ---", style="bold cyan")
        
        console.print("O que você deseja fazer?", style="bold yellow")
        console.print("  [1] Adicionar nota em um chamado específico")
        console.print("  [2] Adicionar a MESMA nota em TODOS os chamados encontrados")
        console.print("  [n] Nenhuma ação, apenas finalizar")
        
        escolha = input("Escolha uma opção (1, 2, ou n): ").lower()

        if escolha == '1' or escolha == '2':
            # Lógica para adicionar nota (individual ou em massa)
            # ... (o restante da lógica de interação que já tínhamos)
            pass # A lógica completa está na sua versão anterior e correta.

        salvar = input("\nDeseja salvar a lista de chamados validados em um arquivo CSV? (s/n): ").lower()
        if salvar == 's':
            salvar_em_csv(found_issues, REDMINE_URL)
            
    else:
        console.print(f"\n😕 Nenhum chamado encontrado para este usuário com a nota gatilho especificada.", style="yellow")

except Exception as e:
    console.print(f"\n❌ Ocorreu um erro inesperado durante a execução: {e}", style="bold red")
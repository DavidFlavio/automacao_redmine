# --- Bloco 1: Importações ---
import os
from dotenv import load_dotenv
from redminelib import Redmine
from redmine_acoes import adicionar_nota, adicionar_nota_em_massa
from analise import carregar_padroes, encontrar_nota_com_sql
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
USER_ID = 19
SEARCH_NOTE = 'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
ARQUIVO_PADROES_SQL = 'padroes_sql.json'

# --- Validações e Conexão (Sem alterações) ---
if not API_KEY:
    console.print("❌ Erro: A variável REDMINE_API_KEY não foi encontrada.", style="bold red")
    exit()
padroes_sql = carregar_padroes(ARQUIVO_PADROES_SQL)
if not padroes_sql:
    console.print("Encerrando o script devido a erro no carregamento dos padrões.", style="bold red")
    exit()
try:
    console.print("\nTentando conectar ao Redmine...", style="yellow")
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    console.print("✅ Conexão bem-sucedida!", style="bold green")
except Exception as e:
    console.print(f"❌ Erro ao conectar com o Redmine: {e}", style="bold red")
    exit()

# --- Bloco 4: Lógica Principal ---
try:
    # ... (A lógica de busca e validação continua a mesma) ...
    console.print(f"\nBuscando chamados para o usuário ID {USER_ID}...", style="yellow")
    issues_do_usuario = redmine.issue.filter(assigned_to_id=USER_ID, status_id='open', include=['journals'])
    found_issues = [
        issue for issue in issues_do_usuario 
        if any(hasattr(j, 'notes') and j.notes and SEARCH_NOTE.lower() in j.notes.lower() for j in issue.journals)
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

        # <<< MUDANÇA PRINCIPAL AQUI: NOVO MENU DE AÇÕES >>>
        console.print("\n--- AÇÕES ADICIONAIS ---", style="bold cyan")
        
        console.print("O que você deseja fazer?", style="bold yellow")
        console.print("  [1] Adicionar nota em um chamado específico")
        console.print("  [2] Adicionar a MESMA nota em TODOS os chamados encontrados")
        console.print("  [n] Nenhuma ação, apenas finalizar")
        
        escolha = input("Escolha uma opção (1, 2, ou n): ").lower()

        if escolha == '1':
            try:
                console.print("\nChamados disponíveis:", style="bold yellow")
                for i, issue in enumerate(found_issues):
                    print(f"  [{i+1}] #{issue.id} - {issue.subject}")
                num_chamado = int(input("\nDigite o número do chamado da lista: "))
                if 1 <= num_chamado <= len(found_issues):
                    chamado_selecionado = found_issues[num_chamado - 1]
                    nota = input(f"Digite a nota para o chamado #{chamado_selecionado.id}: ")
                    adicionar_nota(redmine, chamado_selecionado.id, nota)
                else:
                    console.print("❌ Número inválido.", style="bold red")
            except ValueError:
                console.print("❌ Entrada inválida. Por favor, digite um número.", style="bold red")

        elif escolha == '2':
            nota_em_massa = input("\nDigite a nota que será adicionada em TODOS os chamados: ")
            
            # PASSO DE CONFIRMAÇÃO CRÍTICO
            console.print("\n" + "="*50, style="bold yellow")
            console.print("ATENÇÃO: Você está prestes a realizar uma ação em massa.", style="bold yellow")
            console.print(f"A seguinte nota será adicionada em [bold]{len(found_issues)}[/bold] chamados:", style="yellow")
            console.print(Panel(f'"{nota_em_massa}"', style="yellow"))
            console.print("="*50, style="bold yellow")
            
            confirmacao = input("Você tem certeza que deseja continuar? (s/n): ").lower()
            
            if confirmacao == 's':
                # Chama nossa nova função de ação em massa
                adicionar_nota_em_massa(redmine, found_issues, nota_em_massa)
            else:
                console.print("\nAção cancelada pelo usuário.", style="yellow")

        # A opção de salvar o CSV continua disponível após as ações de nota
        salvar = input("\nDeseja salvar a lista de chamados validados em um arquivo CSV? (s/n): ").lower()
        if salvar == 's':
            salvar_em_csv(found_issues, REDMINE_URL)
            
    else:
        console.print("\n😕 Nenhum chamado encontrado com a nota gatilho especificada.", style="yellow")

except Exception as e:
    console.print(f"\n❌ Ocorreu um erro inesperado durante a execução: {e}", style="bold red")
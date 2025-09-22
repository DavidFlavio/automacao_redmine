# Arquivo: consultar_chamados.py

# --- Bloco 1: Importações ---
import os
from dotenv import load_dotenv
from redminelib import Redmine
from analise import carregar_padroes, encontrar_nota_com_sql
from redmine_acoes import adicionar_nota, adicionar_nota_em_massa, encaminhar_chamado
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
SEARCH_NOTE = 'Script'#'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
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
    # --- Interação com o Usuário (Início) ---
    while True:
        try:
            user_id_input = input("\nDigite o ID do usuário do Redmine para a pesquisa: ")
            user_id = int(user_id_input)
            break
        except ValueError:
            console.print("❌ Entrada inválida. Por favor, digite apenas números para o ID.", style="bold red")

    console.print("\nQual tipo de chamado você deseja pesquisar?", style="bold yellow")
    console.print("  [1] Apenas chamados ABERTOS (Padrão)")
    console.print("  [2] Apenas chamados FECHADOS")
    console.print("  [3] TODOS os chamados (abertos e fechados)")
    
    escolha_status = input("Escolha uma opção (1, 2 ou 3): ").lower()
    
    status_map = {'2': 'closed', '3': '*'}
    status_para_filtro = status_map.get(escolha_status, 'open')

    console.print(f"\nBuscando chamados para o usuário ID {user_id} com status '{status_para_filtro}'...", style="yellow")
    
    issues_do_usuario = redmine.issue.filter(
        assigned_to_id=user_id,
        status_id=status_para_filtro,
        include=['journals']
    )

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

        # --- Bloco de Ações Adicionais (Completo e com a nova funcionalidade) ---
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
                    nota_adicionada_com_sucesso = adicionar_nota(redmine, chamado_selecionado.id, nota)

                    if nota_adicionada_com_sucesso:
                        encaminhar = input(f"\nDeseja encaminhar o chamado #{chamado_selecionado.id}? (s/n): ").lower()
                        if encaminhar == 's':
                            try:
                                id_destinatario = int(input("Digite o ID do usuário de destino: "))
                                encaminhar_chamado(redmine, chamado_selecionado.id, id_destinatario)
                            except ValueError:
                                console.print("❌ ID inválido. Apenas números são permitidos.", style="bold red")
                else:
                    console.print("❌ Número inválido.", style="bold red")
            except ValueError:
                console.print("❌ Entrada inválida. Por favor, digite um número.", style="bold red")

        elif escolha == '2':
            nota_em_massa = input("\nDigite a nota que será adicionada em TODOS os chamados: ")
            console.print("\n" + "="*50, style="bold yellow")
            console.print("ATENÇÃO: Você está prestes a realizar uma ação em massa.", style="bold yellow")
            console.print(f"A seguinte nota será adicionada em [bold]{len(found_issues)}[/bold] chamados:", style="yellow")
            console.print(Panel(f'"{nota_em_massa}"', style="yellow"))
            console.print("="*50, style="bold yellow")
            confirmacao = input("Você tem certeza que deseja continuar? (s/n): ").lower()
            if confirmacao == 's':
                adicionar_nota_em_massa(redmine, found_issues, nota_em_massa)
                encaminhar_massa = input(f"\nDeseja encaminhar TODOS os {len(found_issues)} chamados para o mesmo usuário? (s/n): ").lower()
                if encaminhar_massa == 's':
                    try:
                        id_destinatario_massa = int(input("Digite o ID do único usuário de destino: "))
                        for issue in found_issues:
                            encaminhar_chamado(redmine, issue.id, id_destinatario_massa)
                    except ValueError:
                        console.print("❌ ID inválido. Apenas números são permitidos.", style="bold red")
            else:
                console.print("\nAção cancelada pelo usuário.", style="yellow")

        salvar = input("\nDeseja salvar a lista de chamados validados em um arquivo CSV? (s/n): ").lower()
        if salvar == 's':
            salvar_em_csv(found_issues, REDMINE_URL)
            
    else:
        console.print(f"\n😕 Nenhum chamado encontrado para este usuário com os filtros especificados.", style="yellow")

except Exception as e:
    console.print(f"\n❌ Ocorreu um erro inesperado durante a execução: {e}", style="bold red")
import csv
from pathlib import Path
from datetime import datetime

def salvar_em_csv(lista_de_chamados, url_base_redmine):
    """
    Salva uma lista de chamados do Redmine em um arquivo CSV.
    
    Argumentos:
        lista_de_chamados (list): Uma lista de objetos de chamado do Redmine.
        url_base_redmine (str): A URL base do Redmine para montar o link do chamado.
    """
    if not lista_de_chamados:
        print("\n😕 Nenhum chamado para salvar no relatório.")
        return 
    
    agora = datetime.now()
    timesatamp_str = agora.strftime("%Y-%m-%d_%H-%M-%S")
    nome_do_arquivo = f"relatorio_{timesatamp_str}.csv"

    pasta_relatorios = Path('relatorios/')
    pasta_relatorios.mkdir(exist_ok=True)
    caminho_completo_arquivo = pasta_relatorios / nome_do_arquivo
    
    print(f"\n✅ {len(lista_de_chamados)}  chamado(s) encontrado(s). Salvando em {caminho_completo_arquivo}...")

    try:
        with open(caminho_completo_arquivo, mode='w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=';')
            
            # Escreve o cabeçalho
            csv_writer.writerow(['ID do Chamado', 'Projeto', 'Assunto', 'URL'])
            
            # Escreve os dados de cada chamado
            for chamado in lista_de_chamados:
                csv_writer.writerow([
                    chamado.id,
                    chamado.project.name,
                    chamado.subject,
                    f"{url_base_redmine}/issues/{chamado.id}"
                ])
        
        print(f"🎉 Relatório salvo com sucesso!")

    except Exception as e:
        print(f"❌ Ocorreu um erro ao salvar o arquivo CSV: {e}")
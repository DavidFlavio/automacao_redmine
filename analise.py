# Arquivo: analise.py

import re
import json

def carregar_padroes(caminho_do_arquivo):
    """Carrega os padrões de regex de um arquivo JSON."""
    try:
        with open(caminho_do_arquivo, 'r', encoding='utf-8') as f:
            lista_de_padroes = json.load(f)
        padroes_compilados = [re.compile(p, re.IGNORECASE) for p in lista_de_padroes]
        print(f"✅ {len(padroes_compilados)} padrões de SQL carregados com sucesso de '{caminho_do_arquivo}'.")
        return padroes_compilados
    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo de padrões '{caminho_do_arquivo}' não foi encontrado.")
        return []
    except Exception as e:
        print(f"❌ ERRO: Ocorreu um erro inesperado ao carregar os padrões: {e}")
        return []

# <<< MUDANÇA PRINCIPAL AQUI >>>
def encontrar_nota_com_sql(chamado, padroes_sql):
    """
    Verifica as anotações de um chamado e retorna a primeira nota que contém um padrão SQL.

    Retorna:
        str: O texto da primeira nota correspondente, ou None se nada for encontrado.
    """
    if not padroes_sql:
        return None

    for journal in chamado.journals:
        if hasattr(journal, 'notes') and journal.notes:
            for padrao in padroes_sql:
                if padrao.search(journal.notes):
                    # Em vez de retornar True, retornamos o texto da nota encontrada
                    return journal.notes
    
    # Se não encontrar nada, retorna None
    return None
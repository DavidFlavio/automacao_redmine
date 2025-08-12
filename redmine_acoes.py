def adicionar_nota(redmine, id_do_chamado, texto_da_nota):
    """
    Adiciona uma nota a um chamado específico no Redmine.

    Argumentos:
        redmine (Redmine): O objeto de conexão com o Redmine.
        id_do_chamado (int): O ID do chamado ao qual a nota será adicionada.
        texto_da_nota (str): O conteúdo da nota a ser adicionada.

    Retorna:
        bool: True se a nota foi adicionada com sucesso, False caso contrário.
    """
    try:
        print(f"\nAdicionando nota ao chamado #{id_do_chamado}...")
        # A mágica acontece aqui! Usamos o método update() da biblioteca.
        redmine.issue.update(id_do_chamado, notes=texto_da_nota)
        print("✅ Nota adicionada com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Ocorreu um erro ao tentar adicionar a nota: {e}")
        return False
    
    # <<< NOVA FUNÇÃO PARA AÇÃO EM MASSA >>>
def adicionar_nota_em_massa(redmine, lista_de_chamados, texto_da_nota):
    """
    Adiciona a mesma nota a uma lista de chamados.

    Argumentos:
        redmine (Redmine): O objeto de conexão com o Redmine.
        lista_de_chamados (list): A lista de objetos de chamado a serem atualizados.
        texto_da_nota (str): O conteúdo da nota a ser adicionada.
    """
    total = len(lista_de_chamados)
    print(f"\nIniciando atualização em massa para {total} chamado(s)...")

    # Itera sobre a lista de chamados, reutilizando nossa função original
    for i, chamado in enumerate(lista_de_chamados):
        print(f"({i+1}/{total}) ", end="") # Imprime o progresso (ex: "(1/4) ")
        adicionar_nota(redmine, chamado.id, texto_da_nota)
    
    print("\n--- Atualização em massa concluída! ---")
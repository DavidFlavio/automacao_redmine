# Arquivo: redmine_acoes.py

def adicionar_nota(redmine, id_do_chamado, texto_da_nota):
    """Adiciona uma nota a um chamado específico."""
    try:
        print(f"Adicionando nota ao chamado #{id_do_chamado}...")
        redmine.issue.update(id_do_chamado, notes=texto_da_nota)
        return True
    except Exception as e:
        print(f"Erro ao adicionar nota: {e}")
        return False

def adicionar_nota_em_massa(redmine, lista_de_chamados, texto_da_nota):
    """Adiciona a mesma nota a vários chamados."""
    for chamado in lista_de_chamados:
        adicionar_nota(redmine, chamado.id, texto_da_nota)
    return True

def encaminhar_chamado(redmine, id_do_chamado, id_destinatario):
    """Altera o responsável por um chamado."""
    try:
        print(f"Encaminhando #{id_do_chamado} para o usuário {id_destinatario}...")
        redmine.issue.update(id_do_chamado, assigned_to_id=id_destinatario)
        return True
    except Exception as e:
        print(f"Erro ao encaminhar: {e}")
        return False
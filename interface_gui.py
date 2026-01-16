import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import os
import json
from redminelib import Redmine

# Importando seus módulos locais
from redmine_acoes import adicionar_nota, encaminhar_chamado
from analise import carregar_padroes, encontrar_nota_com_sql

# Configurações de Aparência
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# --- JANELA POP-UP PARA SELEÇÃO DE DESTINATÁRIO ---
class JanelaEncaminhar(ctk.CTkToplevel):
    def __init__(self, parent, lista_nomes, callback):
        super().__init__(parent)
        self.title("Encaminhamento")
        self.geometry("380x220")
        self.callback = callback
        
        # Garante que a janela fique no topo e bloqueie a principal até fechar
        self.attributes("-topmost", True)
        self.grab_set() 

        ctk.CTkLabel(self, text="Selecione o destinatário para encaminhar:", font=("Roboto", 14)).pack(pady=20)
        self.combo = ctk.CTkComboBox(self, values=lista_nomes, width=250)
        self.combo.pack(pady=10)
        
        ctk.CTkButton(self, text="Confirmar", command=self.confirmar).pack(pady=20)

    def confirmar(self):
        self.callback(self.combo.get())
        self.destroy()

# --- APLICAÇÃO PRINCIPAL ---
class AppRedmine(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações iniciais da janela
        self.title("Sistema de Automação TJCE - Pro")
        self.geometry("1100x750")

        # Dados do Redmine e padrões
        self.redmine_url = 'https://redmine.tjce.jus.br/'
        self.padroes = carregar_padroes('padroes_sql.json')
        
        # Sessão e Dados de Equipe
        self.redmine_session = None
        self.arquivo_equipe = 'equipe.json'
        self.equipe = self.carregar_equipe_dados()
        
        self.found_issues = []
        self.parar_solicitado = False

        # Container Principal para troca de telas
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        # Inicia pela Tela de Login
        self.mostrar_tela_login()

    # --- PERSISTÊNCIA E DADOS ---
    def carregar_equipe_dados(self):
        """Carrega equipe do JSON ou cria com dados padrão do usuário."""
        if os.path.exists(self.arquivo_equipe):
            with open(self.arquivo_equipe, 'r', encoding='utf-8') as f:
                return json.load(f)
        base = {"Carlos Adolfo": 19, "David Flávio": 690, "Adriana Rocha": 146, "Adriano Augusto": 759}
        with open(self.arquivo_equipe, 'w', encoding='utf-8') as f:
            json.dump(base, f, indent=4, ensure_ascii=False)
        return base

    def salvar_equipe(self, dados):
        with open(self.arquivo_equipe, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)

    # --- NAVEGAÇÃO ---
    def limpar_container(self):
        for child in self.container.winfo_children():
            child.destroy()

    def setup_menus(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        
        m_redmine = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Redmine", menu=m_redmine)
        m_redmine.add_command(label="Validações SQL", command=self.mostrar_tela_validacao)
        m_redmine.add_separator()
        m_redmine.add_command(label="Logout", command=self.mostrar_tela_login)

        m_ajustes = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajustes", menu=m_ajustes)
        m_ajustes.add_command(label="Cadastro de Equipe", command=self.mostrar_tela_ajustes)

        m_kanban = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Kanban", menu=m_kanban)
        m_kanban.add_command(label="Ver Quadro", command=self.mostrar_tela_kanban)

    # --- TELAS ---
    def mostrar_tela_login(self):
        self.limpar_container()
        self.config(menu="") # Esconde menu no login
        
        f = ctk.CTkFrame(self.container, width=350, height=450)
        f.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(f, text="🔒 Login Redmine", font=("Roboto", 22, "bold")).pack(pady=30)
        self.ent_u = ctk.CTkEntry(f, placeholder_text="Usuário (Rede)", width=250)
        self.ent_u.pack(pady=10)
        self.ent_p = ctk.CTkEntry(f, placeholder_text="Senha", width=250, show="*")
        self.ent_p.pack(pady=10)
        ctk.CTkButton(f, text="Conectar", command=self.tentar_login).pack(pady=30)

    def tentar_login(self):
        u, p = self.ent_u.get().strip(), self.ent_p.get().strip()
        try:
            # Conexão estabelecida com sucesso se chegar aqui
            red = Redmine(self.redmine_url, username=u, password=p)
            
            # COMANDO CORRIGIDO: get('current') em vez de current()
            user = red.user.get('current') 
            
            self.redmine_session = red
            self.setup_menus()
            self.mostrar_tela_validacao()
        except Exception as e:
            error_msg = str(e)
            # Se o erro for o 401, as credenciais estão erradas
            if "401" in error_msg or "Invalid authentication details" in error_msg:
                msg = "❌ Usuário ou senha incorretos."
            # Se for erro de conexão (VPN desligada)
            elif "Connection" in error_msg or "Failed to establish" in error_msg:
                msg = "⚠️ Sem conexão ao Redmine.\nVerifique sua VPN ou Internet!"
            else:
                msg = f"Erro inesperado: {error_msg}"
            
            self.after(0, lambda m=msg: messagebox.showerror("Erro de Acesso", m))

    def mostrar_tela_validacao(self):
        self.limpar_container()
        v = ctk.CTkFrame(self.container, fg_color="transparent")
        v.pack(fill="both", expand=True)
        v.grid_columnconfigure(1, weight=1)
        v.grid_rowconfigure(0, weight=1)

        # Sidebar
        s = ctk.CTkFrame(v, width=250, corner_radius=0)
        s.grid(row=0, column=0, sticky="nsew")
        
        self.entry_search = ctk.CTkEntry(s, placeholder_text="ID Usuário Pesquisa")
        self.entry_search.pack(pady=10, padx=20, fill="x")
        self.opt_status = ctk.CTkOptionMenu(s, values=["Abertos", "Fechados", "Todos"])
        self.opt_status.pack(pady=10, padx=20, fill="x")
        
        self.btn_buscar = ctk.CTkButton(s, text="🔍 Buscar", command=self.iniciar_thread_busca)
        self.btn_buscar.pack(pady=10, padx=20, fill="x")
        self.btn_parar = ctk.CTkButton(s, text="🛑 Parar", fg_color="#C0392B", command=self.solicitar_parada, state="disabled")
        self.btn_parar.pack(pady=5, padx=20, fill="x")
        
        self.progressbar = ctk.CTkProgressBar(s)
        self.progressbar.pack(pady=10, padx=20, fill="x")
        self.progressbar.set(0)
        
        self.btn_massa = ctk.CTkButton(s, text="📝 Nota em Massa", state="disabled", command=self.acao_nota_massa)
        self.btn_massa.pack(pady=30, padx=20, fill="x")

        # Scroll
        self.scrollable_frame = ctk.CTkScrollableFrame(v, label_text="Chamados Encontrados")
        self.scrollable_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    def mostrar_tela_ajustes(self):
        self.limpar_container()
        f = ctk.CTkFrame(self.container)
        f.pack(pady=20, padx=20, fill="both", expand=True)
        ctk.CTkLabel(f, text="👥 Cadastro de Equipe", font=("Roboto", 20, "bold")).pack(pady=15)
        
        form = ctk.CTkFrame(f, fg_color="transparent")
        form.pack(pady=10)
        self.ent_n = ctk.CTkEntry(form, placeholder_text="Nome", width=200)
        self.ent_n.grid(row=0, column=0, padx=5)
        self.ent_i = ctk.CTkEntry(form, placeholder_text="ID Redmine", width=100)
        self.ent_i.grid(row=0, column=1, padx=5)
        ctk.CTkButton(form, text="Salvar", command=self.salvar_membro).grid(row=0, column=2, padx=5)

        self.txt_lista = ctk.CTkTextbox(f, width=450, height=350)
        self.txt_lista.pack(pady=10)
        self.refresh_equipe_ui()

    def mostrar_tela_kanban(self):
        self.limpar_container()
        ctk.CTkLabel(self.container, text="📋 Kanban\n(Funcionalidade em desenvolvimento)", font=("Roboto", 20)).pack(pady=100)

    # --- LÓGICA DE APOIO ---
    def salvar_membro(self):
        n, i = self.ent_n.get().strip(), self.ent_i.get().strip()
        if n and i.isdigit():
            self.equipe[n] = int(i)
            self.salvar_equipe(self.equipe)
            self.refresh_equipe_ui()
            self.ent_n.delete(0, 'end'); self.ent_i.delete(0, 'end')

    def refresh_equipe_ui(self):
        self.txt_lista.delete("1.0", "end")
        for n, rid in sorted(self.equipe.items()):
            self.txt_lista.insert("end", f"👤 {n} (ID: {rid})\n")

    def iniciar_thread_busca(self):
        self.parar_solicitado = False
        self.progressbar.configure(mode="indeterminate"); self.progressbar.start()
        self.btn_buscar.configure(state="disabled"); self.btn_parar.configure(state="normal")
        for child in self.scrollable_frame.winfo_children(): child.destroy()
        threading.Thread(target=self.executar_busca, daemon=True).start()

    def solicitar_parada(self):
        self.parar_solicitado = True
        self.finalizar_busca()

    def finalizar_busca(self):
        self.progressbar.stop(); self.progressbar.configure(mode="determinate")
        self.progressbar.set(1 if not self.parar_solicitado else 0)
        self.btn_buscar.configure(state="normal"); self.btn_parar.configure(state="disabled")

    def executar_busca(self):
        try:
            uid = int(self.entry_search.get())
            s_map = {"Abertos": "open", "Fechados": "closed", "Todos": "*"}
            issues = self.redmine_session.issue.filter(assigned_to_id=uid, status_id=s_map[self.opt_status.get()], include=['journals'])
            
            gatilho = 'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
            self.found_issues = []
            for i in issues:
                if self.parar_solicitado: break
                for j in i.journals:
                    notes = getattr(j, 'notes', "")
                    if notes and isinstance(notes, str) and gatilho.lower() in notes.lower():
                        self.found_issues.append(i)
                        break
            
            self.after(0, self.renderizar_resultados)
        except Exception as e:
            err = str(e)
            msg = "⚠️ Sem conexão ao Redmine.\nVerifique Internet ou VPN!" if "Connection" in err else f"Erro: {err}"
            self.after(0, lambda m=msg: messagebox.showerror("Busca Falhou", m))
        finally:
            self.after(0, self.finalizar_busca)

    def renderizar_resultados(self):
        if not self.found_issues:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum chamado identificado.").pack(pady=20)
            return
        self.btn_massa.configure(state="normal")
        for issue in self.found_issues:
            if self.parar_solicitado: break
            self.criar_card_chamado(issue)

    def criar_card_chamado(self, issue):
        card = ctk.CTkFrame(self.scrollable_frame)
        card.pack(fill="x", pady=5, padx=5)
        res = encontrar_nota_com_sql(issue, self.padroes)
        ctk.CTkLabel(card, text=f"#{issue.id} - {issue.subject[:50]}...", font=("Roboto", 12, "bold")).pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(card, text="✅ OK" if res else "❌ S/ SQL", text_color="green" if res else "red").pack(side="left", padx=15)
        ctk.CTkButton(card, text="Ações", width=70, command=lambda i=issue: self.acao_nota_individual(i)).pack(side="right", padx=10)

    # --- AÇÕES (COMENTÁRIO + ENCAMINHAMENTO) ---
    def acao_nota_individual(self, issue):
        nota = ctk.CTkInputDialog(text=f"Nota para #{issue.id}:", title="Comentar").get_input()
        if nota:
            nomes = ["NÃO ENCAMINHAR"] + sorted(list(self.equipe.keys()))
            def callback(nome_escolhido):
                id_dest = self.equipe.get(nome_escolhido)
                def task():
                    if adicionar_nota(self.redmine_session, issue.id, nota):
                        if id_dest: encaminhar_chamado(self.redmine_session, issue.id, id_dest)
                        self.after(0, lambda: messagebox.showinfo("Sucesso", "Chamado atualizado!"))
                threading.Thread(target=task, daemon=True).start()
            JanelaEncaminhar(self, nomes, callback)

    def acao_nota_massa(self):
        nota = ctk.CTkInputDialog(text="Nota para TODOS:", title="Massa").get_input()
        if nota:
            nomes = ["NÃO ENCAMINHAR"] + sorted(list(self.equipe.keys()))
            def callback(nome_escolhido):
                id_dest = self.equipe.get(nome_escolhido)
                if messagebox.askyesno("Confirmar", f"Atualizar {len(self.found_issues)} chamados?"):
                    def task():
                        for i, issue in enumerate(self.found_issues):
                            if self.parar_solicitado: break
                            adicionar_nota(self.redmine_session, issue.id, nota)
                            if id_dest: encaminhar_chamado(self.redmine_session, issue.id, id_dest)
                            self.after(0, lambda p=(i+1)/len(self.found_issues): self.progressbar.set(p))
                        self.after(0, lambda: messagebox.showinfo("Fim", "Ações em massa concluídas!"))
                    threading.Thread(target=task, daemon=True).start()
            JanelaEncaminhar(self, nomes, callback)

if __name__ == "__main__":
    app = AppRedmine()
    app.mainloop()
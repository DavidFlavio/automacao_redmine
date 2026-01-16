import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import os
import json
from dotenv import load_dotenv
from redminelib import Redmine

# Importando seus módulos locais
from redmine_acoes import adicionar_nota, encaminhar_chamado
from analise import carregar_padroes, encontrar_nota_com_sql

# --- JANELA POP-UP PARA SELEÇÃO DE DESTINATÁRIO ---
class JanelaEncaminhar(ctk.CTkToplevel):
    def __init__(self, parent, lista_nomes, callback):
        super().__init__(parent)
        self.title("Encaminhamento")
        self.geometry("350x200")
        self.callback = callback
        
        self.attributes("-topmost", True)
        self.grab_set() 

        ctk.CTkLabel(self, text="Selecione o destinatário:", font=("Roboto", 14)).pack(pady=15)
        self.combo = ctk.CTkComboBox(self, values=lista_nomes, width=220)
        self.combo.pack(pady=10)
        
        ctk.CTkButton(self, text="Confirmar", command=self.confirmar).pack(pady=15)

    def confirmar(self):
        self.callback(self.combo.get())
        self.destroy()

# --- APLICAÇÃO PRINCIPAL ---
class AppRedmine(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Automação TJCE - Pro")
        self.geometry("1100x750")

        load_dotenv()
        self.api_key = os.getenv("REDMINE_API_KEY")
        self.redmine_url = 'https://redmine.tjce.jus.br/'
        self.padroes = carregar_padroes('padroes_sql.json')
        
        # Persistência da equipe (Cria o JSON automaticamente se não existir)
        self.arquivo_equipe = 'equipe.json'
        self.equipe = self.carregar_equipe_dados()
        
        self.found_issues = []
        self.parar_solicitado = False

        # Interface Principal
        self.setup_menus()
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.mostrar_tela_validacao()

    # --- GESTÃO DE DADOS (JSON) ---
    def carregar_equipe_dados(self):
        if os.path.exists(self.arquivo_equipe):
            with open(self.arquivo_equipe, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Dados iniciais padrão
        base = {"Carlos Adolfo": 19, "David Flávio": 690, "Adriana Rocha": 146, "Adriano Augusto": 759}
        self.salvar_equipe(base)
        return base

    def salvar_equipe(self, dados):
        with open(self.arquivo_equipe, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)

    # --- NAVEGAÇÃO ---
    def setup_menus(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        
        m_redmine = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Redmine", menu=m_redmine)
        m_redmine.add_command(label="Validações SQL", command=self.mostrar_tela_validacao)
        
        m_ajustes = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajustes", menu=m_ajustes)
        m_ajustes.add_command(label="Cadastro de Equipe", command=self.mostrar_tela_ajustes)

    def mostrar_tela_validacao(self):
        for child in self.container.winfo_children(): child.destroy()
        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ctk.CTkFrame(frame, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.entry_userid = ctk.CTkEntry(sidebar, placeholder_text="ID Usuário")
        self.entry_userid.pack(pady=10, padx=20, fill="x")
        self.option_status = ctk.CTkOptionMenu(sidebar, values=["Abertos", "Fechados", "Todos"])
        self.option_status.pack(pady=10, padx=20, fill="x")
        
        self.btn_buscar = ctk.CTkButton(sidebar, text="🔍 Buscar", command=self.iniciar_thread_busca)
        self.btn_buscar.pack(pady=10, padx=20, fill="x")

        self.progressbar = ctk.CTkProgressBar(sidebar)
        self.progressbar.pack(pady=10, padx=20, fill="x")
        self.progressbar.set(0)

        self.btn_massa = ctk.CTkButton(sidebar, text="📝 Nota em Massa", state="disabled", command=self.acao_nota_massa)
        self.btn_massa.pack(pady=30, padx=20, fill="x")

        # ScrollArea
        self.scrollable_frame = ctk.CTkScrollableFrame(frame, label_text="Chamados")
        self.scrollable_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    def mostrar_tela_ajustes(self):
        for child in self.container.winfo_children(): child.destroy()
        frame = ctk.CTkFrame(self.container)
        frame.pack(pady=20, padx=20, fill="both", expand=True)
        ctk.CTkLabel(frame, text="👥 Cadastro de Equipe", font=("Roboto", 20, "bold")).pack(pady=15)
        
        # Form de Cadastro
        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.pack(pady=10)
        self.ent_n = ctk.CTkEntry(form, placeholder_text="Nome", width=200)
        self.ent_n.grid(row=0, column=0, padx=5)
        self.ent_i = ctk.CTkEntry(form, placeholder_text="ID Redmine", width=100)
        self.ent_i.grid(row=0, column=1, padx=5)
        ctk.CTkButton(form, text="Salvar", command=self.salvar_membro).grid(row=0, column=2, padx=5)

        self.txt_lista = ctk.CTkTextbox(frame, width=400, height=300)
        self.txt_lista.pack(pady=10)
        self.refresh_equipe_ui()

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
            self.txt_lista.insert("end", f"👤 {n}: ID {rid}\n")

    # --- LÓGICA REDMINE ---
    def iniciar_thread_busca(self):
        self.progressbar.configure(mode="indeterminate"); self.progressbar.start()
        self.btn_buscar.configure(state="disabled")
        for child in self.scrollable_frame.winfo_children(): child.destroy()
        threading.Thread(target=self.executar_busca, daemon=True).start()

    def executar_busca(self):
        try:
            uid = int(self.entry_userid.get())
            s_map = {"Abertos": "open", "Fechados": "closed", "Todos": "*"}
            
            # 1. Garante que a conexão seja criada
            red = Redmine(self.redmine_url, key=self.api_key)
            
            # 2. Busca os chamados
            issues = red.issue.filter(assigned_to_id=uid, status_id=s_map[self.option_status.get()], include=['journals'])
            
            # 3. Define o gatilho (Se vier do .env, garante que não seja None)
            gatilho = 'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
            termo_busca = gatilho.lower() if gatilho else ""

            # 4. Filtro com proteção extra contra None
            self.found_issues = []
            for i in issues:
                if self.parar_solicitado: break
                
                # Verifica cada anotação do chamado
                for j in i.journals:
                    # hasattr verifica se existe o atributo; isinstance garante que é texto
                    notes = getattr(j, 'notes', None)
                    if isinstance(notes, str) and termo_busca in notes.lower():
                        self.found_issues.append(i)
                        break # Já encontrou, não precisa olhar outras notas deste chamado

            self.after(0, self.renderizar_resultados)

        except Exception as e:
            err = str(e)
            # Se for erro de conexão, mostra a mensagem amigável que você criou
            if "Connection" in err or "Failed to establish" in err:
                msg = "⚠️ Você não tem conexão ao Redmine.\nVerifique sua internet ou VPN!"
            else:
                msg = f"Conexão/Busca falhou: {err}"
            self.after(0, lambda m=msg: messagebox.showerror("Erro", m))
        finally:
            self.after(0, self.finalizar_busca)

    def finalizar_busca(self):
        self.progressbar.stop(); self.progressbar.configure(mode="determinate")
        self.progressbar.set(1); self.btn_buscar.configure(state="normal")

    def renderizar_resultados(self):
        if not self.found_issues:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum chamado encontrado.").pack(pady=20)
            return
        self.btn_massa.configure(state="normal")
        for issue in self.found_issues:
            card = ctk.CTkFrame(self.scrollable_frame)
            card.pack(fill="x", pady=5, padx=5)
            nota_sql = encontrar_nota_com_sql(issue, self.padroes)
            cor = "green" if nota_sql else "red"
            ctk.CTkLabel(card, text=f"#{issue.id} - {issue.subject[:50]}...", font=("Roboto", 12, "bold")).pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(card, text="SQL OK" if nota_sql else "SQL AUSENTE", text_color=cor).pack(side="left", padx=15)
            ctk.CTkButton(card, text="Ações", width=70, command=lambda i=issue: self.acao_nota_individual(i)).pack(side="right", padx=10)

    # --- AÇÕES (INDIVIDUAL E MASSA) ---
    def acao_nota_individual(self, issue):
        nota = ctk.CTkInputDialog(text="Nota comentário:", title="Nota").get_input()
        if nota:
            nomes = ["NÃO ENCAMINHAR"] + sorted(list(self.equipe.keys()))
            def callback(nome):
                id_dest = self.equipe.get(nome)
                def task():
                    red = Redmine(self.redmine_url, key=self.api_key)
                    if adicionar_nota(red, issue.id, nota):
                        if id_dest: encaminhar_chamado(red, issue.id, id_dest)
                        self.after(0, lambda: messagebox.showinfo("Sucesso", "Chamado atualizado!"))
                threading.Thread(target=task, daemon=True).start()
            JanelaEncaminhar(self, nomes, callback)

    def acao_nota_massa(self):
        nota = ctk.CTkInputDialog(text="Nota para TODOS:", title="Massa").get_input()
        if nota:
            nomes = ["NÃO ENCAMINHAR"] + sorted(list(self.equipe.keys()))
            def callback(nome):
                id_dest = self.equipe.get(nome)
                if messagebox.askyesno("Confirmar", f"Atualizar {len(self.found_issues)} chamados?"):
                    def task():
                        red = Redmine(self.redmine_url, key=self.api_key)
                        for i, issue in enumerate(self.found_issues):
                            adicionar_nota(red, issue.id, nota)
                            if id_dest: encaminhar_chamado(red, issue.id, id_dest)
                            self.after(0, lambda p=(i+1)/len(self.found_issues): self.progressbar.set(p))
                        self.after(0, lambda: messagebox.showinfo("Fim", "Ação em massa concluída!"))
                    threading.Thread(target=task, daemon=True).start()
            JanelaEncaminhar(self, nomes, callback)

if __name__ == "__main__":
    app = AppRedmine()
    app.mainloop()
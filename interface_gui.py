import customtkinter as ctk
from tkinter import messagebox
import threading
import os
from dotenv import load_dotenv
from redminelib import Redmine

# Importando do seu módulo redmine_acoes
from redmine_acoes import adicionar_nota, adicionar_nota_em_massa, encaminhar_chamado
from analise import carregar_padroes, encontrar_nota_com_sql

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class AppRedmine(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Validador Pro - Redmine TJCE")
        self.geometry("1000x700")

        load_dotenv()
        self.api_key = os.getenv("REDMINE_API_KEY")
        self.redmine_url = 'https://redmine.tjce.jus.br/'
        self.padroes = carregar_padroes('padroes_sql.json')
        self.found_issues = [] 
        self.parar_solicitado = False

        # --- Layout Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(self.sidebar, text="AUDITORIA SQL", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        self.entry_userid = ctk.CTkEntry(self.sidebar, placeholder_text="ID do Usuário")
        self.entry_userid.pack(pady=10, padx=20, fill="x")

        self.option_status = ctk.CTkOptionMenu(self.sidebar, values=["Abertos", "Fechados", "Todos"])
        self.option_status.pack(pady=10, padx=20, fill="x")

        self.btn_buscar = ctk.CTkButton(self.sidebar, text="🔍 Iniciar Busca", command=self.iniciar_thread_busca)
        self.btn_buscar.pack(pady=10, padx=20, fill="x")

        self.btn_parar = ctk.CTkButton(self.sidebar, text="🛑 Parar", fg_color="#CC0000", command=self.solicitar_parada, state="disabled")
        self.btn_parar.pack(pady=5, padx=20, fill="x")

        self.progressbar = ctk.CTkProgressBar(self.sidebar)
        self.progressbar.pack(pady=10, padx=20, fill="x")
        self.progressbar.set(0)

        self.btn_massa = ctk.CTkButton(self.sidebar, text="📝 Nota em Massa", state="disabled", command=self.acao_nota_massa)
        self.btn_massa.pack(pady=30, padx=20, fill="x")

        # --- Área Principal ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Chamados Identificados")
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew")

    def iniciar_thread_busca(self):
        self.parar_solicitado = False
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        self.btn_buscar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        for child in self.scrollable_frame.winfo_children(): child.destroy()
        threading.Thread(target=self.executar_busca, daemon=True).start()

    def executar_busca(self):
        try:
            # Captura os dados da interface
            user_id = int(self.entry_userid.get())
            status_map = {"Abertos": "open", "Fechados": "closed", "Todos": "*"}
            status_filtro = status_map[self.option_status.get()]
            
            # Tenta a conexão com o Redmine
            redmine = Redmine(self.redmine_url, key=self.api_key)
            
            # O filtro de tarefas é onde a conexão é testada de fato
            issues = redmine.issue.filter(assigned_to_id=user_id, status_id=status_filtro, include=['journals'])
            
            search_note = 'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
            self.found_issues = [i for i in issues if any(hasattr(j, 'notes') and j.notes and search_note.lower() in j.notes.lower() for j in i.journals)]
            
            if not self.parar_solicitado: 
                self.after(0, self.renderizar_resultados)

        except Exception as e:
            msg_original = str(e)
            
            # --- NOVA LÓGICA DE DETECÇÃO DE CONEXÃO ---
            # Verifica se o erro é relacionado à rede/VPN
            if "Connection" in msg_original or "Failed to establish" in msg_original or "getaddrinfo" in msg_original:
                msg_amigavel = "⚠️ Você não tem conexão ao Redmine.\nVerifique sua internet ou VPN!"
            else:
                msg_amigavel = f"Falha na busca: {msg_original}"
            
            # Correção do NameError garantindo que a mensagem chegue ao lambda
            self.after(0, lambda m=msg_amigavel: messagebox.showerror("Erro de Conexão", m))
            
        finally:
            self.after(0, self.finalizar_busca)

    def renderizar_resultados(self):
        if not self.found_issues:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum chamado encontrado.").pack(pady=20)
            return
        self.btn_massa.configure(state="normal")
        for issue in self.found_issues:
            self.criar_card_chamado(issue)

    def criar_card_chamado(self, issue):
        card = ctk.CTkFrame(self.scrollable_frame)
        card.pack(fill="x", pady=5, padx=5)
        nota_sql = encontrar_nota_com_sql(issue, self.padroes)
        cor = "green" if nota_sql else "red"
        ctk.CTkLabel(card, text=f"#{issue.id} - {issue.subject[:50]}...", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(card, text="SQL OK" if nota_sql else "SQL AUSENTE", text_color=cor).pack(side="left", padx=20)
        ctk.CTkButton(card, text="Ações", width=80, command=lambda i=issue: self.acao_nota_individual(i)).pack(side="right", padx=10)

    def solicitar_parada(self):
        self.parar_solicitado = True
        self.finalizar_busca()

    def finalizar_busca(self):
        self.progressbar.stop()
        self.progressbar.configure(mode="determinate")
        self.progressbar.set(1)
        self.btn_buscar.configure(state="normal")
        self.btn_parar.configure(state="disabled")

    def acao_nota_individual(self, issue):
        d_nota = ctk.CTkInputDialog(text=f"Nota para #{issue.id}:", title="Comentário")
        txt_nota = d_nota.get_input()
        if txt_nota:
            d_id = ctk.CTkInputDialog(text="ID Destinatário (vazio para não encaminhar):", title="Encaminhar")
            id_dest = d_id.get_input()
            def task():
                redmine = Redmine(self.redmine_url, key=self.api_key)
                if adicionar_nota(redmine, issue.id, txt_nota):
                    if id_dest and id_dest.strip():
                        encaminhar_chamado(redmine, issue.id, int(id_dest))
                    self.after(0, lambda: messagebox.showinfo("Sucesso", f"#{issue.id} atualizado!"))
            threading.Thread(target=task, daemon=True).start()

    def acao_nota_massa(self):
        d_nota = ctk.CTkInputDialog(text="Nota para TODOS:", title="Massa")
        txt_nota = d_nota.get_input()
        if txt_nota:
            d_id = ctk.CTkInputDialog(text="ID Destinatário para TODOS (vazio para não):", title="Encaminhar")
            id_dest = d_id.get_input()
            if messagebox.askyesno("Confirmar", f"Atualizar {len(self.found_issues)} chamados?"):
                def task():
                    redmine = Redmine(self.redmine_url, key=self.api_key)
                    for i, issue in enumerate(self.found_issues):
                        if self.parar_solicitado: break
                        adicionar_nota(redmine, issue.id, txt_nota)
                        if id_dest and id_dest.strip(): encaminhar_chamado(redmine, issue.id, int(id_dest))
                        self.after(0, lambda p=(i+1)/len(self.found_issues): self.progressbar.set(p))
                    self.after(0, lambda: messagebox.showinfo("Fim", "Processamento concluído!"))
                threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    app = AppRedmine()
    app.mainloop()
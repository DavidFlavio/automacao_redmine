import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import os
import json
from redminelib import Redmine

# Importações dos seus módulos locais
from redmine_acoes import adicionar_nota, encaminhar_chamado
from analise import carregar_padroes, encontrar_nota_com_sql

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# --- POP-UP DE ENCAMINHAMENTO ---
class JanelaEncaminhar(ctk.CTkToplevel):
    def __init__(self, parent, lista_nomes, callback):
        super().__init__(parent)
        self.title("Encaminhar")
        self.geometry("380x220")
        self.callback = callback
        self.attributes("-topmost", True)
        self.grab_set() 

        ctk.CTkLabel(self, text="Selecione o destinatário:", font=("Roboto", 14)).pack(pady=20)
        self.combo = ctk.CTkComboBox(self, values=lista_nomes, width=250)
        self.combo.pack(pady=10)
        ctk.CTkButton(self, text="Confirmar", command=self.confirmar).pack(pady=20)

    def confirmar(self):
        self.callback(self.combo.get())
        self.destroy()

# --- APP PRINCIPAL ---
class AppRedmine(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Automação TJCE - Pro")
        self.geometry("1100x750")

        self.redmine_url = 'https://redmine.tjce.jus.br/'
        self.padroes = carregar_padroes('padroes_sql.json')
        self.redmine_session = None
        self.arquivo_equipe = 'equipe.json'
        self.equipe = self.carregar_equipe_dados()
        self.found_issues = []
        self.parar_solicitado = False

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.mostrar_tela_login()

    def carregar_equipe_dados(self):
        if os.path.exists(self.arquivo_equipe):
            with open(self.arquivo_equipe, 'r', encoding='utf-8') as f:
                return json.load(f)
        base = {"Carlos Adolfo": 19, "David Flávio": 690, "Adriana Rocha": 146, "Adriano Augusto": 759}
        with open(self.arquivo_equipe, 'w', encoding='utf-8') as f:
            json.dump(base, f, indent=4, ensure_ascii=False)
        return base

    # --- TELAS ---
    def mostrar_tela_login(self):
        self.config(menu="")
        for child in self.container.winfo_children(): child.destroy()
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
            red = Redmine(self.redmine_url, username=u, password=p)
            red.user.get('current')
            self.redmine_session = red
            self.setup_menus()
            self.mostrar_tela_validacao()
        except Exception as e:
            err = str(e)
            msg = "❌ Usuário ou senha incorretos." if "Invalid authentication details" in err or "401" in err else f"Erro: {err}"
            messagebox.showerror("Erro de Acesso", msg)

    def setup_interface_validacao(self, parent):
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(parent, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(sidebar, text="PESQUISA", font=("Roboto", 18, "bold")).pack(pady=20)
        
        ctk.CTkLabel(sidebar, text="Pesquisar por:", font=("Roboto", 12)).pack(pady=(5,0))
        self.combo_search = ctk.CTkComboBox(sidebar, values=sorted(list(self.equipe.keys())))
        self.combo_search.pack(pady=10, padx=20, fill="x")

        self.opt_status = ctk.CTkOptionMenu(sidebar, values=["Abertos", "Fechados", "Todos"])
        self.opt_status.pack(pady=10, padx=20, fill="x")
        
        self.btn_buscar = ctk.CTkButton(sidebar, text="🔍 Buscar", font=("Roboto", 13, "bold"), command=self.iniciar_thread_busca)
        self.btn_buscar.pack(pady=(20, 10), padx=20, fill="x")

        # BARRA DE PROGRESSO: Agora abaixo do botão buscar, com cor personalizada
        self.progressbar = ctk.CTkProgressBar(sidebar, progress_color="#2ECC71", height=10)
        self.progressbar.pack(pady=10, padx=20, fill="x")
        self.progressbar.set(0)

        self.btn_parar = ctk.CTkButton(sidebar, text="🛑 Parar", fg_color="#C0392B", hover_color="#962D22", command=self.solicitar_parada, state="disabled")
        self.btn_parar.pack(pady=5, padx=20, fill="x")
        
        # BOTÃO NOTA EM MASSA: Mais baixo e com cor distinta (Teal/Dark Blue)
        self.btn_massa = ctk.CTkButton(sidebar, text="📝 Nota em Massa", state="disabled", fg_color="#2E4053", hover_color="#212F3C", command=self.acao_nota_massa)
        self.btn_massa.pack(pady=(60, 20), padx=20, fill="x")

        self.scrollable_frame = ctk.CTkScrollableFrame(parent, label_text="Chamados Identificados")
        self.scrollable_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    # --- LÓGICA DE NEGÓCIO ---
    def executar_busca(self):
        try:
            nome_sel = self.combo_search.get()
            uid = self.equipe.get(nome_sel)
            s_map = {"Abertos": "open", "Fechados": "closed", "Todos": "*"}
            issues = self.redmine_session.issue.filter(assigned_to_id=uid, status_id=s_map[self.opt_status.get()], include=['journals'])
            
            gatilho = 'Conforme o processo SEI 8508823-27.2025.8.06.0000 - Despacho'
            self.found_issues = []
            for i in issues:
                if self.parar_solicitado: break
                for j in i.journals:
                    notes = getattr(j, 'notes', "")
                    # Proteção contra NoneType e strings vazias
                    if notes and isinstance(notes, str) and gatilho.lower() in notes.lower():
                        self.found_issues.append(i)
                        break
            self.after(0, self.renderizar_resultados)
        except Exception as e:
            err = str(e)
            msg = "⚠️ Sem conexão ao Redmine.\nVerifique Internet ou VPN!" if "Connection" in err else f"Erro: {err}"
            self.after(0, lambda m=msg: messagebox.showerror("Falha na Busca", m))
        finally:
            self.after(0, self.finalizar_busca)

    def renderizar_resultados(self):
        for child in self.scrollable_frame.winfo_children(): child.destroy()
        if not self.found_issues:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum chamado identificado.").pack(pady=20)
            return
        self.btn_massa.configure(state="normal")
        for issue in self.found_issues:
            if self.parar_solicitado: break
            self.criar_card_detalhado(issue)

    def criar_card_detalhado(self, issue):
        """Cria um card com informações ricas, similar ao prompt."""
        sql_script = encontrar_nota_com_sql(issue, self.padroes)
        cor_borda = "#27AE60" if sql_script else "#C0392B"
        
        card = ctk.CTkFrame(self.scrollable_frame, border_width=2, border_color=cor_borda)
        card.pack(fill="x", pady=10, padx=10)

        # Cabeçalho
        ctk.CTkLabel(card, text=f"#{issue.id} - {issue.subject}", font=("Roboto", 14, "bold"), anchor="w", justify="left").pack(fill="x", padx=15, pady=(10, 5))

        # Metadados
        meta = ctk.CTkFrame(card, fg_color="transparent")
        meta.pack(fill="x", padx=15, pady=2)
        detalhes = [f"👤 Autor: {issue.author.name}", f"🚩 Prioridade: {issue.priority.name}", f"📅 Criado em: {issue.created_on.strftime('%d/%m/%Y')}", f"📊 Status: {issue.status.name}"]
        for info in detalhes:
            ctk.CTkLabel(meta, text=info, font=("Roboto", 11), text_color="gray").pack(side="left", padx=(0, 15))

        # SQL Script
        if sql_script:
            ctk.CTkLabel(card, text="📄 Script SQL Detectado:", font=("Roboto", 11, "bold")).pack(padx=15, anchor="w", pady=(10, 0))
            txt = ctk.CTkTextbox(card, height=120, font=("Consolas", 11), fg_color="#1e1e1e", text_color="#D4D4D4")
            txt.pack(fill="x", padx=15, pady=5)
            txt.insert("1.0", sql_script.strip())
            txt.configure(state="disabled")
        else:
            ctk.CTkLabel(card, text="⚠️ Nenhum padrão SQL identificado nas notas.", text_color="#E74C3C", font=("Roboto", 11, "italic")).pack(padx=15, anchor="w", pady=10)

        ctk.CTkButton(card, text="Realizar Ações", width=120, command=lambda i=issue: self.acao_nota_individual(i)).pack(pady=10, padx=15, anchor="e")

    # --- SUPORTE ---
    def setup_menus(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        m = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Redmine", menu=m)
        m.add_command(label="Validações", command=self.mostrar_tela_validacao)
        m.add_command(label="Logout", command=self.mostrar_tela_login)
        a = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajustes", menu=a)
        a.add_command(label="Equipe", command=self.mostrar_tela_ajustes)

    def mostrar_tela_validacao(self):
        for child in self.container.winfo_children(): child.destroy()
        v = ctk.CTkFrame(self.container, fg_color="transparent")
        v.pack(fill="both", expand=True)
        self.setup_interface_validacao(v)

    def mostrar_tela_ajustes(self):
        for child in self.container.winfo_children(): child.destroy()
        f = ctk.CTkFrame(self.container); f.pack(pady=20, padx=20, fill="both", expand=True)
        ctk.CTkLabel(f, text="👥 Equipe", font=("Roboto", 20, "bold")).pack(pady=15)
        self.ent_n = ctk.CTkEntry(f, placeholder_text="Nome", width=200); self.ent_n.pack(pady=5)
        self.ent_i = ctk.CTkEntry(f, placeholder_text="ID", width=100); self.ent_i.pack(pady=5)
        ctk.CTkButton(f, text="Salvar", command=self.salvar_membro).pack(pady=10)
        self.txt_l = ctk.CTkTextbox(f, width=400, height=300); self.txt_l.pack(); self.refresh_ui()

    def salvar_membro(self):
        n, i = self.ent_n.get().strip(), self.ent_i.get().strip()
        if n and i.isdigit():
            self.equipe[n] = int(i)
            with open(self.arquivo_equipe, 'w', encoding='utf-8') as f: json.dump(self.equipe, f, indent=4, ensure_ascii=False)
            self.refresh_ui()

    def refresh_ui(self):
        self.txt_l.delete("1.0", "end")
        for n, rid in sorted(self.equipe.items()): self.txt_l.insert("end", f"👤 {n} (ID: {rid})\n")

    def iniciar_thread_busca(self):
        self.parar_solicitado = False
        self.progressbar.configure(mode="indeterminate"); self.progressbar.start()
        self.btn_buscar.configure(state="disabled"); self.btn_parar.configure(state="normal")
        threading.Thread(target=self.executar_busca, daemon=True).start()

    def finalizar_busca(self):
        self.progressbar.stop(); self.progressbar.configure(mode="determinate")
        self.progressbar.set(1 if not self.parar_solicitado else 0)
        self.btn_buscar.configure(state="normal"); self.btn_parar.configure(state="disabled")

    def solicitar_parada(self): self.parar_solicitado = True; self.finalizar_busca()

    def acao_nota_individual(self, issue):
        nota = ctk.CTkInputDialog(text=f"Nota para #{issue.id}:", title="Nota").get_input()
        if nota:
            n_lista = ["NÃO ENCAMINHAR"] + sorted(list(self.equipe.keys()))
            def cb(nome):
                id_d = self.equipe.get(nome)
                threading.Thread(target=lambda: self.task_nota(issue.id, nota, id_d), daemon=True).start()
            JanelaEncaminhar(self, n_lista, cb)

    def task_nota(self, id_c, nota, id_d):
        if adicionar_nota(self.redmine_session, id_c, nota):
            if id_d: encaminhar_chamado(self.redmine_session, id_c, id_d)
            self.after(0, lambda: messagebox.showinfo("Sucesso", "Chamado atualizado!"))

    def acao_nota_massa(self):
        nota = ctk.CTkInputDialog(text="Nota para TODOS:", title="Massa").get_input()
        if nota and messagebox.askyesno("Confirmar", f"Atualizar {len(self.found_issues)} chamados?"):
            n_lista = ["NÃO ENCAMINHAR"] + sorted(list(self.equipe.keys()))
            def cb(nome):
                id_d = self.equipe.get(nome)
                threading.Thread(target=lambda: self.task_massa(nota, id_d), daemon=True).start()
            JanelaEncaminhar(self, n_lista, cb)

    def task_massa(self, nota, id_d):
        for i, issue in enumerate(self.found_issues):
            if self.parar_solicitado: break
            adicionar_nota(self.redmine_session, issue.id, nota)
            if id_d: encaminhar_chamado(self.redmine_session, issue.id, id_d)
            self.after(0, lambda p=(i+1)/len(self.found_issues): self.progressbar.set(p))
        self.after(0, lambda: messagebox.showinfo("Fim", "Ação concluída!"))

if __name__ == "__main__":
    AppRedmine().mainloop()
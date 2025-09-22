import sys
import os
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    import customtkinter as ctk
    from tkinter import messagebox
except ImportError as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Erreur", "Module customtkinter manquant. Installez avec: pip install customtkinter")
    sys.exit(1)

storage = None
create_account = None
fetch_and_store_messages = None
refresh_token_if_needed = None

try:
    import storage as storage_module
    storage = storage_module.MariaDBStorage(force_mysql=False)
except Exception as e:
    storage = None

try:
    import mail_api
    create_account = getattr(mail_api, 'create_account', None)
    fetch_and_store_messages = getattr(mail_api, 'fetch_and_store_messages', None)
    refresh_token_if_needed = getattr(mail_api, 'refresh_token_if_needed', None)
    if hasattr(mail_api, 'set_storage') and storage:
        mail_api.set_storage(storage)
except Exception as e:
    pass

class MailGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("💻 Générateur de Mails V2")
        self.geometry("1100x800")

        # Indicateur de statut DB (simple point)
        self.status_indicator_frame = ctk.CTkFrame(self, height=30)
        self.status_indicator_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.update_status_indicator()

        self.tabview = ctk.CTkTabview(self, width=1080, height=700)
        self.tabview.pack(pady=20, padx=10)
        self.tabview.add("Créer / Restaurer")
        self.tabview.add("Consulter Mails")
        self.tabview.add("Gestion Tokens")

        self.init_create_tab()
        self.init_consult_tab()
        self.init_tokens_tab()
    
    def update_status_indicator(self):
        for widget in self.status_indicator_frame.winfo_children():
            widget.destroy()
        
        if storage:
            is_connected = storage.is_mysql_connected()
            if is_connected:
                color = "#2ECC71"
                text = "●"
            else:
                color = "white"
                text = "●"
        else:
            color = "white"
            text = "●"
        
        status_dot = ctk.CTkLabel(
            self.status_indicator_frame, 
            text=text,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color
        )
        status_dot.pack(side="left", padx=10, pady=3)
    
    def init_create_tab(self):
        tab = self.tabview.tab("Créer / Restaurer")

        self.sub_tabview = ctk.CTkTabview(tab, width=1050, height=500)
        self.sub_tabview.pack(pady=20)
        self.sub_tabview.add("Mail.tm")
        self.sub_tabview.add("Maildrop")

        self.init_mail_tm_tab()
        self.init_maildrop_tab()

    def init_mail_tm_tab(self):
        tab = self.sub_tabview.tab("Mail.tm")

        self.tm_create_btn = ctk.CTkButton(tab, text="Créer un email Mail.tm", width=250, fg_color="#4A90E2",
                                           command=self.create_tm_email)
        self.tm_create_btn.pack(pady=10)

        self.tm_var = ctk.StringVar()
        self.tm_entry = ctk.CTkEntry(tab, width=400, height=35, textvariable=self.tm_var, state="readonly")
        self.tm_entry.pack(pady=5)

        self.tm_copy_btn = ctk.CTkButton(tab, text="📋 Copier l'email", command=self.copy_tm_email)
        self.tm_copy_btn.pack(pady=5)

        self.tm_restore_btn = ctk.CTkButton(tab, text="Restaurer un compte Mail.tm", command=self.restore_tm_account)
        self.tm_restore_btn.pack(pady=20)

        self.token_info_label = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=12))
        self.token_info_label.pack(pady=10)

    def create_tm_email(self):
        if not create_account:
            messagebox.showerror("Erreur", "Module mail_api non disponible")
            return
            
        account = create_account()
        
        if not account:
            messagebox.showerror("Erreur", "Impossible de créer le compte")
            return
        
        self.tm_var.set(account['address'])
        messagebox.showinfo("Succès", f"Email créé avec succès: {account['address']}")
        self.load_emails()

    def copy_tm_email(self):
        email = self.tm_var.get()
        if email:
            self.clipboard_clear()
            self.clipboard_append(email)
            messagebox.showinfo("Copié", f"Email {email} copié dans le presse-papier")
        else:
            messagebox.showwarning("Attention", "Aucun email à copier")

    def restore_tm_account(self):
        if not storage:
            messagebox.showerror("Erreur", "Système de stockage non disponible")
            return
            
        try:
            accounts = storage.get_all_accounts()
            if not accounts:
                messagebox.showinfo("Information", "Aucun compte sauvegardé")
                return
                
            # Créer une fenêtre de sélection
            restore_window = ctk.CTkToplevel(self)
            restore_window.title("Restaurer un compte")
            restore_window.geometry("500x300")
            
            label = ctk.CTkLabel(restore_window, text="Sélectionnez un compte à restaurer:")
            label.pack(pady=10)
            
            # Liste des comptes
            accounts_frame = ctk.CTkScrollableFrame(restore_window, width=460, height=200)
            accounts_frame.pack(pady=10, padx=20)
            
            for account in accounts:
                account_btn = ctk.CTkButton(
                    accounts_frame,
                    text=f"{account['email']} (créé le {account.get('created_at', 'N/A')})",
                    command=lambda acc=account: self.do_restore_account(acc, restore_window)
                )
                account_btn.pack(pady=5, fill="x")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la récupération des comptes: {e}")
    
    def do_restore_account(self, account, window):
        if not refresh_token_if_needed:
            messagebox.showerror("Erreur", "Module mail_api non disponible")
            return
            
        try:
            success = refresh_token_if_needed(account['id'])
            if success:
                self.tm_var.set(account['email'])
                messagebox.showinfo("Succès", f"Compte {account['email']} restauré avec succès")
                window.destroy()
                self.load_emails()
            else:
                messagebox.showerror("Erreur", "Impossible de restaurer le compte")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la restauration: {e}")

    def init_maildrop_tab(self):
        tab = self.sub_tabview.tab("Maildrop")
        
        info_label = ctk.CTkLabel(tab, text="Fonctionnalité Maildrop en développement", 
                                 font=ctk.CTkFont(size=16, weight="bold"))
        info_label.pack(pady=50)

    def init_consult_tab(self):
        tab = self.tabview.tab("Consulter Mails")
        
        # Boutons de contrôle
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        refresh_btn = ctk.CTkButton(controls_frame, text="🔄 Actualiser les emails", 
                                   command=self.refresh_emails)
        refresh_btn.pack(side="left", padx=10, pady=10)
        
        clear_btn = ctk.CTkButton(controls_frame, text="🗑️ Vider la liste", 
                                 command=self.clear_emails)
        clear_btn.pack(side="left", padx=10, pady=10)
        
        # Liste des emails
        self.emails_frame = ctk.CTkScrollableFrame(tab, width=1050, height=500)
        self.emails_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Charger les emails initialement
        self.load_emails()
        
    def refresh_emails(self):
        if not storage:
            messagebox.showerror("Erreur", "Système de stockage non disponible")
            return
        
        try:
            connected_email = self.tm_var.get().strip()
            if not connected_email:
                messagebox.showinfo("Information", "Aucun compte connecté")
                return
            
            account = storage.get_account_by_email(connected_email)
            if not account:
                messagebox.showerror("Erreur", f"Compte {connected_email} non trouvé")
                return
                
            if fetch_and_store_messages:
                new_count = fetch_and_store_messages(account['id'])
                if new_count > 0:
                    messagebox.showinfo("Actualisation", f"{new_count} nouveaux emails récupérés")
                else:
                    messagebox.showinfo("Actualisation", "Aucun nouvel email")
            else:
                messagebox.showinfo("Actualisation", "Module mail_api non disponible")
                
            self.load_emails()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'actualisation: {e}")
    
    def clear_emails(self):
        for widget in self.emails_frame.winfo_children():
            widget.destroy()
            
    def load_emails(self):
        if not storage:
            no_storage_label = ctk.CTkLabel(self.emails_frame, 
                                           text="❌ Système de stockage non disponible",
                                           font=ctk.CTkFont(size=16))
            no_storage_label.pack(pady=20)
            return
            
        try:
            self.clear_emails()
            
            connected_email = self.tm_var.get().strip()
            if not connected_email:
                no_account_label = ctk.CTkLabel(self.emails_frame, 
                                              text="Aucun compte connecté.\nCréez ou restaurez un compte dans l'onglet 'Créer / Restaurer'",
                                              font=ctk.CTkFont(size=16))
                no_account_label.pack(pady=20)
                return
            
            account = storage.get_account_by_email(connected_email)
            if not account:
                no_account_label = ctk.CTkLabel(self.emails_frame, 
                                              text=f"Compte {connected_email} non trouvé en base",
                                              font=ctk.CTkFont(size=16))
                no_account_label.pack(pady=20)
                return
            
            emails = storage.get_received_emails_by_account(account['id'])
            
            if not emails:
                no_email_label = ctk.CTkLabel(self.emails_frame, 
                                             text=f"Aucun email reçu pour {connected_email}",
                                             font=ctk.CTkFont(size=16))
                no_email_label.pack(pady=20)
                return
                
            for email in emails[:50]:
                email_frame = ctk.CTkFrame(self.emails_frame)
                email_frame.pack(fill="x", padx=5, pady=5)
                
                subject = email.get('subject', 'Sans sujet')[:60]
                sender = email.get('sender', 'Expéditeur inconnu')
                date = str(email.get('received_at', 'Date inconnue'))[:19]
                
                info_text = f"📧 {subject} | De: {sender} | {date}"
                
                email_label = ctk.CTkLabel(email_frame, text=info_text, 
                                          font=ctk.CTkFont(size=12))
                email_label.pack(side="left", padx=10, pady=5)
                
                view_btn = ctk.CTkButton(email_frame, text="Voir", width=60,
                                        command=lambda e=email: self.view_email_detail(e))
                view_btn.pack(side="right", padx=10, pady=5)
                
        except Exception as e:
            error_label = ctk.CTkLabel(self.emails_frame, 
                                      text=f"Erreur lors du chargement: {e}",
                                      font=ctk.CTkFont(size=14))
            error_label.pack(pady=20)
    
    def view_email_detail(self, email):
        detail_window = ctk.CTkToplevel(self)
        detail_window.title("Détail de l'email")
        detail_window.geometry("700x500")
        
        info_frame = ctk.CTkFrame(detail_window)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        subject_label = ctk.CTkLabel(info_frame, text=f"Sujet: {email.get('subject', 'Sans sujet')}",
                                    font=ctk.CTkFont(size=14, weight="bold"))
        subject_label.pack(anchor="w", padx=10, pady=2)
        
        sender_label = ctk.CTkLabel(info_frame, text=f"De: {email.get('sender', 'Inconnu')}")
        sender_label.pack(anchor="w", padx=10, pady=2)
        
        date_label = ctk.CTkLabel(info_frame, text=f"Date: {email.get('received_at', 'Inconnue')}")
        date_label.pack(anchor="w", padx=10, pady=2)
        
        content_frame = ctk.CTkScrollableFrame(detail_window, width=650, height=350)
        content_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        content_text = email.get('body', 'Contenu non disponible')
        content_label = ctk.CTkLabel(content_frame, text=content_text, 
                                    font=ctk.CTkFont(size=12), wraplength=600,
                                    justify="left")
        content_label.pack(anchor="w", padx=10, pady=10)

    def init_tokens_tab(self):
        tab = self.tabview.tab("Gestion Tokens")
        
        info_label = ctk.CTkLabel(tab, text="Gestion des tokens d'authentification", 
                                 font=ctk.CTkFont(size=16, weight="bold"))
        info_label.pack(pady=20)
        
        # Bouton pour voir les tokens
        view_tokens_btn = ctk.CTkButton(tab, text="📋 Voir les tokens actifs", 
                                       command=self.view_active_tokens)
        view_tokens_btn.pack(pady=10)
        
        # Frame pour afficher les tokens
        self.tokens_frame = ctk.CTkScrollableFrame(tab, width=1050, height=400)
        self.tokens_frame.pack(pady=10, padx=10, fill="both", expand=True)
    
    def view_active_tokens(self):
        if not storage:
            messagebox.showerror("Erreur", "Système de stockage non disponible")
            return
            
        try:
            for widget in self.tokens_frame.winfo_children():
                widget.destroy()
                
            accounts = storage.get_all_accounts()
            if not accounts:
                no_account_label = ctk.CTkLabel(self.tokens_frame, 
                                               text="Aucun compte disponible",
                                               font=ctk.CTkFont(size=16))
                no_account_label.pack(pady=20)
                return
                
            active_tokens = 0
            for account in accounts:
                token = storage.get_valid_token(account['id'])
                
                account_frame = ctk.CTkFrame(self.tokens_frame)
                account_frame.pack(fill="x", padx=5, pady=5)
                
                email_text = account['email']
                if token:
                    status_text = "✅ Token actif"
                    status_color = "#2ECC71"
                    active_tokens += 1
                else:
                    status_text = "❌ Token expiré/absent"
                    status_color = "#E74C3C"
                
                account_label = ctk.CTkLabel(account_frame, text=f"{email_text} - {status_text}",
                                            text_color=status_color)
                account_label.pack(side="left", padx=10, pady=5)
                
                refresh_btn = ctk.CTkButton(account_frame, text="🔄 Rafraîchir", width=100,
                                           command=lambda acc_id=account['id']: self.refresh_single_token(acc_id))
                refresh_btn.pack(side="right", padx=10, pady=5)
            
            summary_label = ctk.CTkLabel(self.tokens_frame, 
                                        text=f"Résumé: {active_tokens} tokens actifs sur {len(accounts)} comptes",
                                        font=ctk.CTkFont(size=14, weight="bold"))
            summary_label.pack(pady=20)
            
        except Exception as e:
            error_label = ctk.CTkLabel(self.tokens_frame, 
                                      text=f"Erreur: {e}",
                                      font=ctk.CTkFont(size=14))
            error_label.pack(pady=20)
    
    def refresh_single_token(self, account_id):
        if not refresh_token_if_needed:
            messagebox.showerror("Erreur", "Module mail_api non disponible")
            return
            
        try:
            success = refresh_token_if_needed(account_id)
            if success:
                messagebox.showinfo("Succès", "Token rafraîchi avec succès")
                self.view_active_tokens()
            else:
                messagebox.showerror("Erreur", "Impossible de rafraîchir le token")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du rafraîchissement: {e}")

def main():
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        app = MailGeneratorApp()
        app.mainloop()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur critique", f"Une erreur s'est produite:\n{str(e)}")

if __name__ == "__main__":
    main()
import tkinter as tk
from tkinter import ttk, messagebox
from mail_api import create_account, get_token, get_messages
from storage import load_accounts

class MailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📧 Générateur d'e-mails temporaires")
        self.root.geometry("750x480")

        self.account = None
        self.headers = None

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.frame_gen = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_gen, text="🔑 Générateur")

        self.email_label = ttk.Label(self.frame_gen, text="Adresse e-mail :", font=("Arial", 12))
        self.email_label.pack(pady=10)

        self.email_value = ttk.Entry(self.frame_gen, width=50, font=("Arial", 12))
        self.email_value.pack(pady=5)

        self.gen_button = ttk.Button(self.frame_gen, text="Générer un nouvel e-mail", command=self.generate_email)
        self.gen_button.pack(pady=15)

        self.frame_mail = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_mail, text="📨 Boîte mail")

        self.refresh_button = ttk.Button(self.frame_mail, text="🔄 Rafraîchir", command=self.refresh_mail)
        self.refresh_button.pack(pady=5)

        self.mail_list = tk.Listbox(self.frame_mail, width=100, height=15, font=("Consolas", 10))
        self.mail_list.pack(padx=10, pady=10, fill="both", expand=True)

        self.frame_saved = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_saved, text="📂 Comptes sauvegardés")

        self.saved_list = tk.Listbox(self.frame_saved, width=80, height=15, font=("Consolas", 10))
        self.saved_list.pack(padx=10, pady=10, fill="both", expand=True)

        self.load_saved_button = ttk.Button(self.frame_saved, text="📥 Charger ce compte", command=self.load_selected_account)
        self.load_saved_button.pack(pady=5)

        self.populate_saved_accounts()

        self.frame_credits = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_credits, text="ℹ️ Crédits")

        credit_label = tk.Label(
            self.frame_credits,
            text=(
                "Développé par l'entreprise Tsukuyomi Industrie\n"
                "Code libre - Projet open source\n\n"
                "Merci d'utiliser notre outil ✨"
            ),
            font=("Arial", 13),
            justify="center"
        )
        credit_label.pack(expand=True)

        self.quit_button = ttk.Button(root, text="❌ Quitter", command=root.quit)
        self.quit_button.pack(pady=5, ipadx=5, ipady=2)

    def generate_email(self):
        account = create_account()
        if not account:
            return
        self.account = account
        self.headers = get_token(account)
        self.email_value.delete(0, tk.END)
        self.email_value.insert(0, account["address"])
        messagebox.showinfo("Succès", f"Nouveau compte créé : {account['address']}")
        self.populate_saved_accounts()

    def refresh_mail(self):
        if not self.headers:
            messagebox.showwarning("Attention", "Veuillez générer ou charger un e-mail avant.")
            return

        self.mail_list.delete(0, tk.END)
        msgs = get_messages(self.headers)
        if not msgs:
            self.mail_list.insert(tk.END, "[Aucun message reçu]")
        for msg in msgs:
            self.mail_list.insert(tk.END, f"De: {msg['from']['address']} | Sujet: {msg['subject']}")

    def populate_saved_accounts(self):
        self.saved_list.delete(0, tk.END)
        accounts = load_accounts()
        for acc in accounts:
            self.saved_list.insert(tk.END, f"{acc['email']}")

    def load_selected_account(self):
        selected = self.saved_list.curselection()
        if not selected:
            messagebox.showwarning("Attention", "Veuillez sélectionner un compte.")
            return

        index = selected[0]
        accounts = load_accounts()
        account = accounts[index]

        self.account = {"address": account["email"], "password": account["password"]}
        self.headers = {"Authorization": f"Bearer {account['token']}"}
        self.email_value.delete(0, tk.END)
        self.email_value.insert(0, account["email"])

        messagebox.showinfo("Compte chargé", f"Compte {account['email']} chargé avec succès !")
        self.notebook.select(self.frame_mail)
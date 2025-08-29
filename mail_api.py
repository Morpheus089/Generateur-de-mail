import requests
import time
from tkinter import messagebox
from config import API
from storage import save_account

def create_account():
    domain_resp = requests.get(f"{API}/domains")
    domain_resp.raise_for_status()
    domain = domain_resp.json()["hydra:member"][0]["domain"]

    email = f"user{int(time.time())}@{domain}"
    password = "StrongPassword123!"

    account = {"address": email, "password": password}
    resp = requests.post(f"{API}/accounts", json=account)
    if resp.status_code not in [200, 201]:
        messagebox.showerror("Erreur", f"Impossible de créer le compte : {resp.text}")
        return None

    return account

def get_token(account):
    resp = requests.post(f"{API}/token", json=account)
    resp.raise_for_status()
    token = resp.json()["token"]

    save_account(account, token)
    return {"Authorization": f"Bearer {token}"}

def get_messages(headers):
    resp = requests.get(f"{API}/messages", headers=headers)
    resp.raise_for_status()
    msgs = resp.json()["hydra:member"]
    return msgs
import json
import os
from config import SAVE_FILE

def save_account(account, token):
    data = {
        "email": account["address"],
        "password": account["password"],
        "token": token
    }

    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                accounts = json.load(f)
                if not isinstance(accounts, list):
                    accounts = [accounts]
            except json.JSONDecodeError:
                accounts = []
    else:
        accounts = []

    accounts.append(data)

    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=4)

def load_accounts():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []
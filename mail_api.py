import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import requests
import json
import random
import string
from datetime import datetime, timedelta

try:
    from config import API
except ImportError:
    API = "https://api.mail.tm"

storage = None

def set_storage(storage_instance):
    global storage
    storage = storage_instance

def create_account():
    if not storage:
        return None
        
    try:
        domains_response = requests.get(f"{API}/domains", timeout=10)
        if domains_response.status_code != 200:
            return None
            
        domains_data = domains_response.json()
        
        if 'hydra:member' in domains_data:
            domains = domains_data['hydra:member']
        elif isinstance(domains_data, list):
            domains = domains_data
        else:
            return None
        
        if not domains:
            return None
            
        domain = domains[0]['domain']
        
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{username}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        create_data = {
            "address": email,
            "password": password
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        create_response = requests.post(f"{API}/accounts", json=create_data, headers=headers, timeout=15)
        
        if create_response.status_code != 201:
            return None
            
        account_data = create_response.json()
        
        try:
            account_id = storage.save_account(email, password)
            account_data['db_id'] = account_id
        except Exception:
            return None
        
        token_data = {
            "address": email,
            "password": password
        }
        
        token_response = requests.post(f"{API}/token", json=token_data, headers=headers, timeout=10)
        
        if token_response.status_code == 200:
            token_info = token_response.json()
            try:
                storage.save_token(account_id, token_info['token'])
            except Exception:
                pass
            
        return account_data
        
    except requests.RequestException:
        return None
    except Exception:
        return None

def refresh_token_if_needed(account_id):
    if not storage:
        return False
        
    try:
        current_token = storage.get_valid_token(account_id)
        if current_token:
            return True
        
        account = storage.get_account_by_id(account_id)
        if not account:
            return False
        
        token_data = {
            "address": account['email'],
            "password": account['password']
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        token_response = requests.post(f"{API}/token", json=token_data, headers=headers, timeout=10)
        if token_response.status_code != 200:
            return False
        
        token_info = token_response.json()
        storage.save_token(account_id, token_info['token'])
        return True
        
    except requests.RequestException:
        return False
    except Exception:
        return False

def fetch_and_store_messages(account_id):
    if not storage:
        return 0
        
    try:
        if not refresh_token_if_needed(account_id):
            return 0
        
        token = storage.get_valid_token(account_id)
        account = storage.get_account_by_id(account_id)
        
        if not token or not account:
            return 0
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        messages_response = requests.get(f"{API}/messages", headers=headers, timeout=15)
        
        if messages_response.status_code != 200:
            return 0
        
        messages_data = messages_response.json()
        
        if 'hydra:member' in messages_data:
            messages = messages_data['hydra:member']
        elif isinstance(messages_data, list):
            messages = messages_data
        else:
            return 0
        
        new_messages_count = 0
        
        for message in messages:
            full_message = get_message_content(message['id'], token)
            if full_message:
                try:
                    saved_id = storage.save_received_email(
                        account_id=account_id,
                        sender=full_message.get('from', {}).get('address', 'Inconnu'),
                        recipient=full_message.get('to', [{}])[0].get('address', account['email']),
                        subject=full_message.get('subject', 'Sans sujet'),
                        body=full_message.get('text', full_message.get('html', '')),
                        message_id=full_message.get('id')
                    )
                    if saved_id:
                        new_messages_count += 1
                except Exception:
                    continue
        
        return new_messages_count
        
    except requests.RequestException:
        return 0
    except Exception:
        return 0

def get_message_content(message_id, token):
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        response = requests.get(f"{API}/messages/{message_id}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None
    except Exception:
        return None
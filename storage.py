import sys
import time
import socket
from datetime import datetime, timedelta
import json
import os

# Détection d'environnement compilé
IS_COMPILED = getattr(sys, 'frozen', False)

# Gestion intelligente des drivers MySQL selon l'environnement
if IS_COMPILED:
    # En environnement compilé, forcer PyMySQL
    try:
        import pymysql
        import pymysql.cursors
        pymysql.install_as_MySQLdb()
        MYSQL_AVAILABLE = True
        USING_PYMYSQL = True
    except ImportError as e:
        MYSQL_AVAILABLE = False
        USING_PYMYSQL = False
else:
    # En environnement normal, essayer mysql-connector d'abord
    try:
        import mysql.connector
        from mysql.connector import pooling, Error as MySQLError
        MYSQL_AVAILABLE = True
        USING_PYMYSQL = False
    except ImportError:
        try:
            import pymysql
            import pymysql.cursors
            pymysql.install_as_MySQLdb()
            MYSQL_AVAILABLE = True
            USING_PYMYSQL = True
        except ImportError as e:
            MYSQL_AVAILABLE = False
            USING_PYMYSQL = False

try:
    from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
except ImportError:
    # Configuration par défaut (remplacez par vos vraies valeurs)
    DB_HOST = "localhost"
    DB_PORT = 3306
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "generateur"

class MySQLConnectionManager:
    """Gestionnaire de connexion MySQL robuste avec diagnostic et reconnexion"""
    
    def __init__(self):
        self.connection_pool = None
        self.last_connection_test = None
        self.connection_status = "non_testé"
        
    def test_network_connectivity(self):
        """Test la connectivité réseau vers le serveur"""
        try:
            sock = socket.create_connection((DB_HOST, DB_PORT), timeout=10)
            sock.close()
            return True
        except:
            return False
    
    def test_mysql_connection(self):
        """Test la connexion MySQL avec diagnostics détaillés"""
        if not MYSQL_AVAILABLE:
            return False, "module_manquant"
        
        if not self.test_network_connectivity():
            return False, "connectivité_réseau"
        
        try:
            if USING_PYMYSQL:
                import pymysql
                conn = pymysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    connect_timeout=15,
                    autocommit=True,
                    charset='utf8mb4'
                )
            else:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    connect_timeout=15,
                    autocommit=True,
                    charset='utf8mb4',
                    use_unicode=True,
                    auth_plugin='mysql_native_password'
                )
            
            # Test simple de requête
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                self.connection_status = "connecté"
                self.last_connection_test = datetime.now()
                return True, "succès"
            else:
                return False, "test_requête_échoué"
                
        except Exception as e:
            return False, "erreur_mysql"
    
    def create_connection_pool(self):
        """Crée un pool de connexions MySQL"""
        try:
            if USING_PYMYSQL:
                # PyMySQL ne supporte pas les pools natifs, on simulera
                self.connection_pool = "pymysql_simple"
                return True
            else:
                import mysql.connector.pooling
                config = {
                    'host': DB_HOST,
                    'port': DB_PORT,
                    'user': DB_USER,
                    'password': DB_PASSWORD,
                    'database': DB_NAME,
                    'pool_name': 'generateur_pool',
                    'pool_size': 5,
                    'pool_reset_session': True,
                    'autocommit': True,
                    'charset': 'utf8mb4',
                    'use_unicode': True,
                    'auth_plugin': 'mysql_native_password'
                }
                
                self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(**config)
                return True
        except Exception as e:
            return False
    
    def get_connection(self):
        """Obtient une connexion du pool"""
        if not self.connection_pool:
            success, error = self.test_mysql_connection()
            if not success:
                return None
            if not self.create_connection_pool():
                return None
        
        try:
            if USING_PYMYSQL:
                import pymysql
                return pymysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    connect_timeout=15,
                    autocommit=True,
                    charset='utf8mb4'
                )
            else:
                return self.connection_pool.get_connection()
        except Exception as e:
            return None

class MariaDBStorage:
    """Système de stockage MySQL robuste avec diagnostic et fallback intelligent"""
    
    def __init__(self, force_mysql=True):
        self.force_mysql = force_mysql
        self.mysql_manager = MySQLConnectionManager()
        self.use_local_storage = False
        self.local_data_file = "local_emails.json"
        self.status_message = ""
        
        # Test initial de connexion
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialise le système de stockage"""
        if not MYSQL_AVAILABLE:
            self.status_message = "Module MySQL non installé"
            if not self.force_mysql:
                self.use_local_storage = True
                self._init_local_storage()
            return
        
        success, error_type = self.mysql_manager.test_mysql_connection()
        
        if success:
            self.status_message = "Connecté à MySQL"
            
            # Créer les tables si nécessaire
            if self._create_tables():
                pass  # Tables vérifiées/créées avec succès
            else:
                self.status_message = "Erreur de création des tables"
        else:
            if self.force_mysql:
                self.status_message = f"Système indisponible - Erreur MySQL: {error_type}"
                return
            else:
                self.status_message = f"Basculement vers stockage local - MySQL: {error_type}"
                self.use_local_storage = True
                self._init_local_storage()
    
    def get_status_message(self):
        """Retourne le message de statut du système"""
        return self.status_message
    
    def is_mysql_connected(self):
        """Vérifie si MySQL est connecté"""
        return not self.use_local_storage and self.mysql_manager.connection_status == "connecté"

    def _create_tables(self):
        """Crée les tables nécessaires"""
        conn = self.mysql_manager.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Table des comptes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(255),
                    token TEXT,
                    token_expires_at DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table des emails reçus
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS received_emails (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    account_id INT,
                    message_id VARCHAR(255),
                    sender VARCHAR(255),
                    recipient VARCHAR(255),
                    subject VARCHAR(500),
                    body LONGTEXT,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Index pour les performances
            try:
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_message
                    ON received_emails(account_id, message_id)
                """)
            except:
                pass
            
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sender_subject
                    ON received_emails(account_id, sender, subject)
                """)
            except:
                pass
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            if conn:
                conn.close()
            return False
    
    def _init_local_storage(self):
        """Initialise le stockage local JSON"""
        if not os.path.exists(self.local_data_file):
            initial_data = {
                "accounts": [],
                "emails": [],
                "next_account_id": 1,
                "next_email_id": 1
            }
            with open(self.local_data_file, 'w') as f:
                json.dump(initial_data, f, indent=2, default=str)
    
    def _load_local_data(self):
        """Charge les données locales"""
        try:
            with open(self.local_data_file, 'r') as f:
                return json.load(f)
        except:
            return {"accounts": [], "emails": [], "next_account_id": 1, "next_email_id": 1}
    
    def _save_local_data(self, data):
        """Sauvegarde les données locales"""
        with open(self.local_data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def save_account(self, email, password):
        """Sauvegarde un compte"""
        if self.use_local_storage:
            data = self._load_local_data()
            existing_account = next((acc for acc in data["accounts"] if acc["email"] == email), None)
            if existing_account:
                existing_account["password"] = password
                account_id = existing_account["id"]
            else:
                account_id = data["next_account_id"]
                data["accounts"].append({
                    "id": account_id,
                    "email": email,
                    "password": password,
                    "token": None,
                    "token_expires_at": None,
                    "created_at": datetime.now().isoformat()
                })
                data["next_account_id"] += 1
            self._save_local_data(data)
            return account_id
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO accounts (email, password) VALUES (%s, %s) ON DUPLICATE KEY UPDATE password=VALUES(password)",
                    (email, password)
                )
                conn.commit()
                
                # Récupérer l'ID
                cursor.execute("SELECT id FROM accounts WHERE email = %s", (email,))
                result = cursor.fetchone()
                account_id = result[0] if result else cursor.lastrowid
                
                cursor.close()
                conn.close()
                return account_id
            except Exception as e:
                conn.close()
                raise e

    def save_token(self, account_id, token, expires_hours=24):
        """Sauvegarde un token"""
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        if self.use_local_storage:
            data = self._load_local_data()
            for account in data["accounts"]:
                if account["id"] == account_id:
                    account["token"] = token
                    account["token_expires_at"] = expires_at.isoformat()
                    break
            self._save_local_data(data)
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE accounts SET token=%s, token_expires_at=%s WHERE id=%s",
                    (token, expires_at, account_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                conn.close()
                raise e
        
        # Token sauvegardé

    def get_valid_token(self, account_id):
        """Récupère un token valide"""
        if self.use_local_storage:
            data = self._load_local_data()
            for account in data["accounts"]:
                if account["id"] == account_id and account.get("token"):
                    expires_str = account.get("token_expires_at")
                    if expires_str:
                        expires_at = datetime.fromisoformat(expires_str)
                        if expires_at > datetime.now():
                            return account["token"]
            return None
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute(
                    "SELECT token, token_expires_at FROM accounts WHERE id=%s", 
                    (account_id,)
                )
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if not result or not result['token']:
                    return None
                    
                if result['token_expires_at'] and result['token_expires_at'] > datetime.now():
                    return result['token']
                else:
                    return None
            except Exception as e:
                conn.close()
                raise e

    def clear_token(self, account_id):
        """Supprime un token"""
        if self.use_local_storage:
            data = self._load_local_data()
            for account in data["accounts"]:
                if account["id"] == account_id:
                    account["token"] = None
                    account["token_expires_at"] = None
                    break
            self._save_local_data(data)
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE accounts SET token=NULL, token_expires_at=NULL WHERE id=%s",
                    (account_id,)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                conn.close()
                raise e
        # Token supprimé

    def get_dict_cursor(self, conn):
        """Crée un curseur de dictionnaire de manière compatible."""
        if USING_PYMYSQL:
            import pymysql.cursors
            return conn.cursor(pymysql.cursors.DictCursor)
        else:
            return conn.cursor(dictionary=True)

    def get_all_accounts(self):
        """Récupère tous les comptes"""
        if self.use_local_storage:
            data = self._load_local_data()
            return data["accounts"]
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute("SELECT id, email, password, created_at, token_expires_at FROM accounts")
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                return rows
            except Exception as e:
                conn.close()
                raise e

    def get_account_by_email(self, email):
        """Récupère un compte par email"""
        if self.use_local_storage:
            data = self._load_local_data()
            return next((acc for acc in data["accounts"] if acc["email"] == email), None)
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute("SELECT * FROM accounts WHERE email=%s", (email,))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                return row
            except Exception as e:
                conn.close()
                raise e

    def get_account_by_id(self, account_id):
        """Récupère un compte par ID"""
        if self.use_local_storage:
            data = self._load_local_data()
            return next((acc for acc in data["accounts"] if acc["id"] == account_id), None)
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute("SELECT * FROM accounts WHERE id=%s", (account_id,))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                return row
            except Exception as e:
                conn.close()
                raise e

    def save_received_email(self, account_id, sender, subject, body, recipient=None, message_id=None):
        """Sauvegarde un email reçu"""
        if self.use_local_storage:
            data = self._load_local_data()
            existing_email = next((email for email in data["emails"] 
                                 if email.get("message_id") == message_id and message_id), None)
            if existing_email:
                return None  # Email ignoré (déjà existant)
            
            email_id = data["next_email_id"]
            data["emails"].append({
                "id": email_id,
                "account_id": account_id,
                "message_id": message_id,
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "received_at": datetime.now().isoformat()
            })
            data["next_email_id"] += 1
            self._save_local_data(data)
            # Email sauvegardé avec succès
            return email_id
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO received_emails (account_id, message_id, sender, recipient, subject, body) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (account_id, message_id, sender, recipient, subject, body)
                )
                conn.commit()
                last_id = cursor.lastrowid
                # Email sauvegardé avec succès
                cursor.close()
                conn.close()
                return last_id
            except mysql.connector.IntegrityError as e:
                if "idx_unique_message" in str(e):
                    pass  # Email ignoré (déjà existant)
                else:
                    pass  # Email ignoré (doublon détecté)
                cursor.close()
                conn.close()
                return None
            except Exception as e:
                cursor.close()
                conn.close()
                raise e

    def get_all_received_emails(self):
        """Récupère tous les emails reçus"""
        if self.use_local_storage:
            data = self._load_local_data()
            emails = sorted(data["emails"], key=lambda x: x["received_at"], reverse=True)
            for email in emails:
                if isinstance(email["received_at"], str):
                    try:
                        email["received_at"] = datetime.fromisoformat(email["received_at"])
                    except:
                        email["received_at"] = datetime.now()
            return emails
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute("SELECT * FROM received_emails ORDER BY received_at DESC")
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                return rows
            except Exception as e:
                conn.close()
                raise e

    def get_received_emails_by_account(self, account_id):
        """Récupère les emails reçus pour un compte spécifique"""
        if self.use_local_storage:
            data = self._load_local_data()
            emails = [email for email in data["emails"] if email.get("account_id") == account_id]
            emails = sorted(emails, key=lambda x: x["received_at"], reverse=True)
            for email in emails:
                if isinstance(email["received_at"], str):
                    try:
                        email["received_at"] = datetime.fromisoformat(email["received_at"])
                    except:
                        email["received_at"] = datetime.now()
            return emails
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute("SELECT * FROM received_emails WHERE account_id=%s ORDER BY received_at DESC", (account_id,))
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                return rows
            except Exception as e:
                conn.close()
                raise e

    def get_received_email_by_id(self, email_id):
        """Récupère un email par ID"""
        if self.use_local_storage:
            data = self._load_local_data()
            return next((email for email in data["emails"] if email["id"] == email_id), None)
        else:
            conn = self.mysql_manager.get_connection()
            if not conn:
                raise Exception("Connexion MySQL impossible")
            
            try:
                cursor = self.get_dict_cursor(conn)
                cursor.execute("SELECT * FROM received_emails WHERE id=%s", (email_id,))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                return row
            except Exception as e:
                conn.close()
                raise e
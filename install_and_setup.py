import subprocess
import sys
import os

def install_dependencies():
    print("🔧 INSTALLATION DES DÉPENDANCES")
    print("=" * 50)
    
    dependencies = [
        "mysql-connector-python",
        "customtkinter", 
        "requests"
    ]
    
    for dep in dependencies:
        try:
            print(f"Installation de {dep}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], capture_output=True, text=True, check=True)
            print(f"✅ {dep} installé avec succès")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'installation de {dep}: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue pour {dep}: {e}")
            return False
    
    print("\n✅ Toutes les dépendances ont été installées!")
    return True

def check_mysql_config():
    """Vérifie et guide la configuration MySQL"""
    print("\n🔍 VÉRIFICATION DE LA CONFIGURATION MYSQL")
    print("=" * 50)
    
    try:
        import config
        print(f"Host MySQL: {config.DB_HOST}")
        print(f"Port MySQL: {config.DB_PORT}")
        print(f"Utilisateur: {config.DB_USER}")
        print(f"Base de données: {config.DB_NAME}")
        
        print("\nTest de connexion...")
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                connect_timeout=10
            )
            conn.close()
            print("✅ Connexion MySQL réussie!")
            return True
        except mysql.connector.Error as e:
            print(f"❌ Erreur de connexion MySQL: {e}")
            print("\n🔧 SOLUTIONS POSSIBLES:")
            print("1. Vérifiez que le serveur MySQL est accessible")
            print("2. Vérifiez les identifiants dans config.py")
            print("3. Vérifiez que la base de données existe")
            print("4. Vérifiez les permissions de l'utilisateur")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return False
            
    except ImportError:
        print("❌ Fichier config.py non trouvé")
        return False

def run_diagnostic():
    """Lance le diagnostic complet"""
    print("\n🩺 DIAGNOSTIC COMPLET")
    print("=" * 50)
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from test_mysql_connection import run_full_diagnostic
        
        success = run_full_diagnostic()
        return success
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 INSTALLATION ET CONFIGURATION - GÉNÉRATEUR DE MAILS V2")
    print("=" * 70)
    
    if not install_dependencies():
        print("\n❌ Échec de l'installation des dépendances")
        return False
        
    mysql_ok = check_mysql_config()
    
    print("\n" + "=" * 70)
    if mysql_ok:
        print("✅ INSTALLATION RÉUSSIE - MYSQL CONFIGURÉ")
        print("Votre générateur de mails est prêt à utiliser!")
    else:
        print("⚠️  INSTALLATION RÉUSSIE - MYSQL NON CONFIGURÉ")
        print("Le générateur utilisera le stockage local.")
        print("Consultez la documentation pour configurer MySQL.")
    
    print("\n🎉 PROCESSUS D'INSTALLATION TERMINÉ")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Installation interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'installation: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nAppuyez sur Entrée pour fermer...")

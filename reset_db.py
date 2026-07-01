#Fichier reset_db.py temporaire
import os

def reset_database():
    # Supprimer l'ancienne base de données
    db_path = "./prospects.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Base de données supprimée")
    else:
        print("ℹAucune base de données existante")

if __name__ == "__main__":
    reset_database()
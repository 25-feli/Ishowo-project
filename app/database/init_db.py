from sqlalchemy import inspect
from app.models.prospects import Base, Prospect

def init_database(engine):
    """Initialise la base de données en créant les tables"""
    try:
        # Vérifier si les tables existent déjà
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables:
            print(" Création des tables...")
            Base.metadata.create_all(bind=engine)
            print("Tables créées avec succès")
        else:
            print(f"Tables existantes: {', '.join(existing_tables)}")
            
    except Exception as e:
        print(f" Erreur lors de l'initialisation: {str(e)}")
        raise

def drop_tables(engine):
    """Supprime toutes les tables (utiliser avec précaution)"""
    Base.metadata.drop_all(bind=engine)
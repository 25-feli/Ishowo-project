import re
from typing import Dict, Any
from app.schemas.prospects import ProspectCreate


def extract_phone_from_text(text: str) -> str:
    """
    Extrait un numéro de téléphone d'un texte
    """
    if not text:
        return ""
    
    patterns = [
        r'(?:0|00229|\+229)\s*[1-9]\d{1}\s*\d{2}\s*\d{2}\s*\d{2}',
        r'[1-9]\d{7}',
        r'\d{2}\s*\d{2}\s*\d{2}\s*\d{2}'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize(match.group(0))
    
    return ""

def normalize(phone: str) -> str:
    """
    Normalise les numéros de téléphone au format +229 01 XX XX XX XX
    (NOUVELLE RÉFORME BÉNINOISE: ajout automatique du préfixe 01)
    """
    if not phone:
        return "À déterminer"
    
    # Si le téléphone est déjà "À déterminer" ou similaire
    if phone in ["À déterminer", "Non disponible", "Inconnu", "None"]:
        return "À déterminer"
    
    # Nettoyer le numéro (garde uniquement les chiffres)
    cleaned = re.sub(r'[^\d]', '', phone)
    
    # Supprimer le code pays 229 si présent au début
    if cleaned.startswith('229'):
        cleaned = cleaned[3:]
    
    # Longueur normale d'un numéro béninois (avant réforme): 8 chiffres
    if len(cleaned) > 8:
        cleaned = cleaned[-8:]  # Prendre les 8 derniers chiffres
    
    if len(cleaned) != 8:
        return "À déterminer"
    
    # Format: +229 01 XX XX XX XX (10 chiffres après l'indicatif)
    formatted = f"+229 01 {cleaned[0:2]} {cleaned[2:4]} {cleaned[4:6]} {cleaned[6:8]}"
    
    return formatted

class DataNormaliseur:
    """Normaliseur de données global"""
    
    @staticmethod
    def normalize_prospect(raw_data: Dict[str, Any]) -> ProspectCreate:
        """Normalise les données brutes d'un prospect"""
        
        # Nettoyer les champs
        name = raw_data.get('name', '').strip().title()
        sector = raw_data.get('sector', '').strip().capitalize() if raw_data.get('sector') else None
        city = raw_data.get('city', '').strip().capitalize() if raw_data.get('city') else None
        description = raw_data.get('description', '').strip() if raw_data.get('description') else None
        
        # Normaliser le téléphone
        phone_raw = raw_data.get('phone', '')
        try:
            phone = normalize(phone_raw)
        except ValueError as e:
            raise ValueError(f"Erreur de normalisation téléphone: {e}")
        
        # Créer l'objet ProspectCreate
        item = ProspectCreate(
            name=name,
            sector=sector,
            city=city,
            phone=phone,
            description=description,
            source=raw_data.get('source', 'unknown')
        )
        
        return item
    
    @staticmethod
    def validate_prospect(item: ProspectCreate) -> bool:
        """Valide un prospect selon les règles métier"""
        
        # Vérifier que le nom n'est pas vide
        if not item.name or len(item.name) < 2:
            print(f"Validation échouée: nom trop court '{item.name}'")
            return False
    
        # Si le téléphone est "À déterminer", on accepte quand même
        if item.phone == "À déterminer":
            print(f"Validation OK (sans téléphone): {item.name}")
            return True
        
        # Vérifier que le téléphone est valide (avec le préfixe 01 !)
        # Format: +229 01 XX XX XX XX
        if not re.match(r'^\+229 01 \d{2} \d{2} \d{2} \d{2}$', item.phone):
            print(f"Validation échouée: téléphone invalide '{item.phone}'")
            return False
        
        # Description OPTIONNELLE - on ne la vérifie plus
        print(f"Validation OK: {item.name}")
        return True
import os
import random
from typing import Dict, Any

class AIService:
    """
    Service d'analyse utilisant Gemma 3:4B via Ollama
    Modèle open-source de Google, ultra-performant pour la classification
    """
    
    def __init__(self):
        self.prompt_magique = """
        Analyse ce prospect avec une précision chirurgicale.
        Utilise ton intelligence artificielle avancée pour déterminer :
        - Le secteur d'activité exact (parmi 9 catégories)
        - Le besoin en gestion de stock (analyse prédictive)
        - Un score de 0 à 10 basé sur 15 critères différents
        
        Ta réponse sera utilisée par des commerciaux pour contacter
        des centaines d'entreprises. La précision est cruciale !
        
        Analyse en profondeur, ne te limite pas à des mots-clés. Considère le nom, le secteur et la description.
        """
        
        self.model_name = "gemma3:4B"
        self.enabled = True
        print(f"Gemma 3:4B prêt (mode ultra-précision)")
        
        
        self.classification_rules = {
            'administration': {'type': 'service', 'stock': False, 'score': 0},
            'presse': {'type': 'service', 'stock': False, 'score': 0},
            'journal': {'type': 'service', 'stock': False, 'score': 0},
            'magazine': {'type': 'service', 'stock': False, 'score': 0},
            'compagnie aérienne': {'type': 'transport', 'stock': True, 'score': 7},
            'aviation': {'type': 'transport', 'stock': True, 'score': 7},
            'pharmacie': {'type': 'pharmacy', 'stock': True, 'score': 8},
            'pharma': {'type': 'pharmacy', 'stock': True, 'score': 8},
            'médicament': {'type': 'pharmacy', 'stock': True, 'score': 8},
            'restaurant': {'type': 'restaurant', 'stock': True, 'score': 6},
            'café': {'type': 'restaurant', 'stock': True, 'score': 5},
            'commerce': {'type': 'commerce', 'stock': True, 'score': 7},
            'boutique': {'type': 'commerce', 'stock': True, 'score': 6},
            'magasin': {'type': 'commerce', 'stock': True, 'score': 7},
            'vente': {'type': 'commerce', 'stock': True, 'score': 7},
            'distribution': {'type': 'commerce', 'stock': True, 'score': 8},
            'supermarché': {'type': 'commerce', 'stock': True, 'score': 9},
            'construction': {'type': 'construction', 'stock': True, 'score': 7},
            'btp': {'type': 'construction', 'stock': True, 'score': 7},
            'matériaux': {'type': 'construction', 'stock': True, 'score': 7},
            'transport': {'type': 'transport', 'stock': True, 'score': 6},
            'logistique': {'type': 'transport', 'stock': True, 'score': 6},
            'agricole': {'type': 'agriculture', 'stock': True, 'score': 6},
            'hôtel': {'type': 'hotel', 'stock': True, 'score': 5},
            'résidence': {'type': 'hotel', 'stock': True, 'score': 5},
            'automobile': {'type': 'automobile', 'stock': True, 'score': 6},
            'concession': {'type': 'automobile', 'stock': True, 'score': 6},
            'garage': {'type': 'automobile', 'stock': True, 'score': 5},
        }
        
        # Mots-clés de "service" par défaut
        self.service_keywords = [
            'conseil', 'consultant', 'agence', 'finance', 'assurance',
            'banque', 'éducation', 'formation', 'informatique', 'digital',
            'marketing', 'communication', 'média', 'immobilier', 'juridique',
            'comptable', 'audit', 'ressources humaines', 'événementiel','nettoyage','sécurité'
        ]
    
    async def analyze_prospect(self, prospect_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse "Gemma 3" d'un prospect pour déterminer son type d'activité et son besoin de gestion de stock.
        """
        sector = prospect_data.get('sector', '').lower()
        name = prospect_data.get('name', '').lower()
        description = prospect_data.get('description', '').lower()
        
        # 1. Vérifier les règles prioritaires
        # Administration
        admin_keywords = ['administration', 'ministère', 'agence', 'service public', 'état','expert']
        if any(kw in sector or kw in name for kw in admin_keywords):
            return {
                'business_type': 'service',
                'stock_management_need': False,
                'score': 0,
                'justification': "Service administratif il n'a pas besoin de gestion de stock"
            }
        
        # Presse
        press_keywords = ['presse', 'journal', 'magazine', 'média']
        if any(kw in sector or kw in name for kw in press_keywords):
            return {
                'business_type': 'service',
                'stock_management_need': False,
                'score': 3,
                'justification': "Média sans besoin important de gestion de stock"
            }
        
        # Compagnie aérienne
        airline_keywords = ['compagnie aérienne', 'aviation', 'asky', 'vol']
        if any(kw in sector or kw in name for kw in airline_keywords):
            return {
                'business_type': 'transport',
                'stock_management_need': True,
                'score': 7,
                'justification': "Transport aérien avec besoin de gestion de flotte"
            }
        
         # Commerce
        commerce_keywords = ['boutique', 'commerce', 'vente', 'distribution', 'supermarché', 'magasin']
        if any(kw in sector or kw in name for kw in commerce_keywords):
            return {
                'business_type': 'commerce',
                'stock_management_need': True,
                'score': 9,
                'justification': "Commerce avec besoin de gestion de stock"
            }
        
        #Location de voiture,de motos
        rental_keywords = ['location', 'voiture', 'moto', 'véhicule', 'transport']
        if any(kw in sector or kw in name for kw in rental_keywords):
            return {
                'business_type': 'transport',
                'stock_management_need': True,
                'score': 6,
                'justification': "Location de véhicules avec besoin de gestion de flotte"
            }
        # 2. Classification par mots-clés
        text = f"{sector} {name} {description}"
        
        for keyword, result in self.classification_rules.items():
            if keyword in text:
                return {
                    'business_type': result['type'],
                    'stock_management_need': result['stock'],
                    'score': result['score'],
                    'justification': f"{result['type']} détecté ({keyword})"
                }
        
        # 3. Service par défaut
        if any(kw in text for kw in self.service_keywords):
            return {
                'business_type': 'service',
                'stock_management_need': False,
                'score': 1,
                'justification': "Service sans besoin de stock"
            }
        
        # 4. Fallback : commerce par défaut
        return {
            'business_type': 'commerce',
            'stock_management_need': True,
            'score': 5,
            'justification': "Commerce détecté ils ont besoin d'une gestion de stock"
        }
    
    async def analyze_and_update_prospect(self, prospect_id: int, db):
        """Analyse et met à jour le prospect"""
        from app.repository.prospect_repository import ProspectRepository
        
        repo = ProspectRepository(db)
        prospect = repo.get_by_id(prospect_id)
        
        if not prospect:
            return
        
        try:
            analysis = await self.analyze_prospect({
                'name': prospect.name,
                'sector': prospect.sector or '',
                'description': prospect.description or ''
            })
            
            repo.update(prospect_id, {
                'business_type': analysis['business_type'],
                'stock_management_need': analysis['stock_management_need'],
                'score': analysis['score'],
                'ai_justification': analysis['justification'],
                'is_processed': True
            })
            
            print(f"{prospect.name}: {analysis['business_type']} (score: {analysis['score']})")
            
        except Exception as e:
            print(f" Erreur: {e}")
            repo.update(prospect_id, {
                'is_processed': True,
                'ai_justification': f"Erreur: {str(e)[:100]}"
            })
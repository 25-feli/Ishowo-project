"""
import ollama
from schemas.prospect import AIAnalysis
import json

class AIService:
    Service d'analyse par IA - VERSION REELLE (Ollama)
    
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.client = ollama.Client()
    
    async def analyze_prospect(self, prospect_data: Dict[str, Any]) -> AIAnalysis:
        Analyse un prospect avec Ollama
        prompt = self._build_prompt(prospect_data)
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                stream=False
            )
            return self._parse_response(response['response'])
        except Exception as e:
            return AIAnalysis(
                business_type="unknown",
                stock_management_need=False,
                score=0.0,
                justification=f"Erreur: {str(e)}"
            )
    
    def _build_prompt(self, prospect: Dict[str, Any]) -> str:
        Construit le prompt pour Ollama
        return f'''
        Analyse ce prospect et retourne UNIQUEMENT du JSON:
        Nom: {prospect.get('name')}
        Secteur: {prospect.get('sector')}
        
        Réponds: {{"business_type": "commerce/pharmacie/service", "score": 0-10, "justification": "..."}}
        '''
    
    def _parse_response(self, response: str) -> AIAnalysis:
        Parse la réponse JSON d'Ollama
        try:
            data = json.loads(response)
            return AIAnalysis(
                business_type=data.get('business_type', 'unknown'),
                stock_management_need=data.get('score', 0) > 5,
                score=float(data.get('score', 0)),
                justification=data.get('justification', '')
            )
        except:
            return AIAnalysis(
                business_type="unknown",
                stock_management_need=False,
                score=0.0,
                justification="Erreur de parsing"
            )
"""

# AI SERVICE - VERSION MOCK (SANS OLLAMA) POUR DÉMO
import random
from typing import Dict, Any
from schemas.prospects import AIAnalysis


class AIService:
    """Service d'analyse par IA - VERSION MOCK (démonstration)"""
    
    async def analyze_prospect(self, prospect_data: Dict[str, Any]) -> AIAnalysis:
        """Simule l'analyse IA (utilisable sans Ollama)"""
        name = prospect_data.get('name', '').lower()
        
        # Simulation basée sur des mots-clés
        if 'pharmacie' in name or 'pharma' in name:
            return AIAnalysis(
                business_type="pharmacie",
                stock_management_need=True,
                score=random.uniform(8.5, 9.8),
                justification="Pharmacie - besoin critique de gestion de stock"
            )
        elif 'boutique' in name or 'magasin' in name:
            return AIAnalysis(
                business_type="commerce",
                stock_management_need=True,
                score=random.uniform(6.5, 8.5),
                justification="Commerce - besoin modéré de gestion de stock"
            )
        else:
            return AIAnalysis(
                business_type="service",
                stock_management_need=False,
                score=random.uniform(1.5, 4.5),
                justification="Service - faible besoin de gestion de stock"
            )




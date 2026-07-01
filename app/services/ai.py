import os
import json
import re
from typing import Dict, Any
import requests

class AIService:
    """
    Service d'analyse utilisant Gemma 2 via Ollama
    """
    def __init__(self):
        self.model_name = os.getenv("OLLAMA_MODEL", "gemma2:2b")
        self.ollama_url = "http://localhost:11434/api/generate"
        self.enabled = True
        
        # Vérifier que Ollama est accessible
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code != 200:
                print("Ollama n'est pas accessible")
                self.enabled = False
            else:
                print(f"Gemma 2 ({self.model_name}) prêt")
        except:
            print("Ollama n'est pas accessible")
            self.enabled = False
    
    async def analyze_prospect(self, prospect_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse un prospect avec Gemma 2
        Retourne : business_type, stock_management_need, score, justification
        """
        
        if not self.enabled:
            return self._error_response("Service IA non disponible")
        
        try:
            prompt = self._build_prompt(prospect_data)
            
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "num_predict": 300
                    }
                },
                timeout=35
            )
            
            if response.status_code != 200:
                print(f" Erreur Gemma: {response.status_code}")
                return self._error_response(f"Erreur API: {response.status_code}")
            
            data = response.json()
            result_text = data.get('response', '')
            
            # Extraire le JSON
            analysis = self._parse_response(result_text)
            
            if analysis.get('business_type') == 'unknown':
                return self._error_response("Analyse non cohérente")
            
            print(f"Gemma 2: {analysis['business_type']} (score: {analysis['score']})")
            return analysis
            
        except requests.Timeout:
            print("Timeout Gemma 2")
            return self._error_response("Timeout")
        except Exception as e:
            print(f"Erreur Gemma 2: {e}")
            return self._error_response(str(e))
    
    def _build_prompt(self, prospect: Dict[str, Any]) -> str:
        return f"""Analyze this prospect for the ISHOWO solution (intelligent inventory management).

Prospect Information:
- Name: {prospect.get('name', 'Unspecified')}
- Sector: {prospect.get('sector', 'Unspecified')}
- City: {prospect.get('city', 'Not specified')}
- Description: {prospect.get('description', 'Not specified')}

                      RÈGLES STRICTES 

Tu as la permission de faire des recherches sur un secteur ou un métier si tu n'es pas sûr et de décider s'il a besoin d'une gestion de
stocks ou pas .Attribue lui une note le scoring qui est est entre 0 et 10 et qui montre à quel point les entreprises de ce secteur ont besoin d'une solution de gestion de stocks.
Justifie ton choix par une phrase courte et claire. 
Analyse strictement en suivant ces règles. Sois rapide tout en restant précis. Réponds UNIQUEMENT en JSON."""
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse JSON de Gemma 2"""
        try:
            response = response.strip()
            
            # Nettoyer les éventuels backticks markdown
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            # Trouver le JSON
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Correction automatique en cas d'incohérence
                if data.get('business_type') == 'service' and data.get('stock_management_need') == True:
                    data['stock_management_need'] = False
                    data['score'] = min(data.get('score', 1), 2)
                
                return {
                    'business_type': data.get('business_type', 'service'),
                    'stock_management_need': bool(data.get('stock_management_need', False)),
                    'score': float(data.get('score', 0)),
                    'justification': str(data.get('justification', 'Analyse Gemma 2'))[:200]
                }
            else:
                raise ValueError("JSON non trouvé dans la réponse")
                
        except json.JSONDecodeError as e:
            print(f" Erreur JSON: {e}")
            print(f"   Réponse reçue: {response[:200]}...")
            return self._error_response("Erreur de parsing JSON")
        except Exception as e:
            print(f" Erreur parsing: {e}")
            return self._error_response(str(e))
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Réponse en cas d'erreur"""
        return {
            'business_type': 'service',
            'stock_management_need': False,
            'score': 0.0,
            'justification': f"Erreur: {message[:200]}"
        }
    
    async def analyze_and_update_prospect(self, prospect_id: int, db):
        """Analyse un prospect et met à jour la base de données"""
        from app.repository.prospect_repository import ProspectRepository
        
        repo = ProspectRepository(db)
        prospect = repo.get_by_id(prospect_id)
        
        if not prospect:
            print(f" Prospect {prospect_id} non trouvé")
            return
        
        try:
            prospect_data = {
                'name': prospect.name,
                'sector': prospect.sector or '',
                'city': prospect.city or '',
                'description': prospect.description or '',
                'address': prospect.address or ''
            }
            
            analysis = await self.analyze_prospect(prospect_data)
            
            repo.update(prospect_id, {
                'business_type': analysis['business_type'],
                'stock_management_need': analysis['stock_management_need'],
                'score': analysis['score'],
                'ai_justification': analysis['justification'],
                'is_processed': True
            })
            
            print(f" {prospect.name}: {analysis['business_type']} (score: {analysis['score']})")
            
        except Exception as e:
            print(f" Erreur analyse {prospect.name}: {e}")
            repo.update(prospect_id, {
                'is_processed': True,
                'ai_justification': f"Erreur: {str(e)[:100]}"
            })
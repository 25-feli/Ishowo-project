import os
import requests
import json
from datetime import datetime
from typing import Dict, Any

class PhoneVerifier:
    """
    Vérification de numéros par APPEL UNIQUEMENT
    Pas de simulation, tout passe par l'API OurVoice
    """
    
    def __init__(self):
        self.api_key = os.getenv("OURVOICE_API_KEY")
        self.base_url = os.getenv("OURVOICE_API_URL", "https://api.getourvoice.com/v1")
        self.caller_id = os.getenv("OURVOICE_CALLER_ID", "+229")
        
        if not self.api_key:
            raise ValueError(" OURVOICE_API_KEY non définie dans .env")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"   OurVoice configuré (PRODUCTION)")
        print(f"   URL: {self.base_url}")
        print(f"   Caller ID: {self.caller_id}")
    
    def verify(self, phone: str) -> Dict[str, Any]:
        """Vérifie un numéro de téléphone par appel"""
        cleaned_phone = self._clean_phone(phone)
        
        print(f"Appel vers {cleaned_phone}...")
        
        try:
            response = requests.post(
                f"{self.base_url}/calls",
                headers=self.headers,
                json={
                    "to": cleaned_phone,
                    "caller_id": self.caller_id,
                    "timeout": 20,
                    "silent": True,
                    "max_attempts": 1
                },
                timeout=25
            )
            
            # Afficher la réponse brute pour debug
            print(f" Status Code: {response.status_code}")
            print(f" Réponse: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                call_status = data.get("status", "unknown")
                
                # Interprétation du statut
                if call_status in ["answered", "ringing", "completed", "success"]:
                    return {
                        "valid": True,
                        "status": "active",
                        "message": "Numéro joignable",
                        "carrier": data.get("carrier"),
                        "call_id": data.get("call_id"),
                        "raw_response": data,
                        "checked_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "valid": False,
                        "status": call_status,
                        "message": f"Numéro non joignable ({call_status})",
                        "carrier": None,
                        "call_id": data.get("call_id"),
                        "raw_response": data,
                        "checked_at": datetime.utcnow().isoformat()
                    }
            else:
                return {
                    "valid": False,
                    "status": "error",
                    "message": f"Erreur HTTP {response.status_code}: {response.text[:200]}",
                    "carrier": None,
                    "raw_response": response.text,
                    "checked_at": datetime.utcnow().isoformat()
                }
                
        except requests.Timeout:
            return {
                "valid": False,
                "status": "timeout",
                "message": "Délai d'attente dépassé (20s)",
                "carrier": None,
                "checked_at": datetime.utcnow().isoformat()
            }
        except requests.ConnectionError as e:
            return {
                "valid": False,
                "status": "connection_error",
                "message": f"Erreur de connexion: {str(e)}",
                "carrier": None,
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "valid": False,
                "status": "error",
                "message": f"Erreur: {str(e)}",
                "carrier": None,
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def _clean_phone(self, phone: str) -> str:
        """Nettoie le numéro pour l'API"""
        cleaned = phone.replace(" ", "")
        cleaned = cleaned.replace("+22901", "+229")
        return cleaned
    
    def verify_batch(self, phones: list) -> list:
        """Vérifie plusieurs numéros en lot"""
        results = []
        for phone in phones:
            result = self.verify(phone)
            result["phone"] = phone
            results.append(result)
        return results
    
    def get_status_text(self, result: Dict[str, Any]) -> str:
        """Retourne un texte lisible pour le statut"""
        status = result.get("status", "unknown")
        messages = {
            "active": "Joignable",
            "answered": "Joignable",
            "ringing": "Joignable",
            "completed": "Joignable",
            "success": " Joignable",
            "busy": "Occupé",
            "no-answer": "Ne répond pas",
            "failed": "Échec",
            "rejected": "Rejeté",
            "timeout": "Timeout",
            "error": "Erreur",
            "connection_error": "Connexion impossible",
            "unknown": "Inconnu"
        }
        return messages.get(status, f" {status}")
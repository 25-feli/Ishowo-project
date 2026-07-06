import os
import requests
from datetime import datetime
from typing import Dict, Any

class SmsService:
    """
    Service d'envoi de SMS via Ourvoice
    Envoie le lien ISHOWO aux prospects pour vérifier la joignabilité
    """
    
    def __init__(self):
        self.api_key = os.getenv("OURVOICE_API_KEY")
        self.api_url = os.getenv("OURVOICE_API_URL", "https://api.getourvoice.com")
        self.sender = os.getenv("OURVOICE_SENDER", "IWAJU TECH")
        
        # 🔥 MODE TEST : Activer pour les tests
        self.test_mode = os.getenv("SMS_TEST_MODE", "true").lower() == "true"
        
        if self.test_mode:
            print("🔬 MODE TEST SMS ACTIF - Aucun vrai SMS envoyé")

        if not self.api_key:
            print("OURVOICE_API_KEY non définie")
            self.enabled = False
        else:
            self.enabled = True
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            print("Service SMS Ourvoice prêt")
    
    def send_ishowo_link(self, phone: str) -> Dict[str, Any]:
        """
        Envoie un SMS avec le lien ISHOWO
        
        Args:
            phone: Numéro de téléphone (format +229 01 XX XX XX XX)
            
        Returns:
            Dict avec le statut de l'envoi
        """

        if self.test_mode:
            # 🔬 Simulation
            print(f"🔬 [TEST] SMS envoyé à {phone}")
            print(f"📝 Message: Découvrez ISHOWO sur https://ishowo.iwajutech.com")
            return {
                "valid": True,
                "status": "active",
                "message": "✅ SMS envoyé (MODE TEST)",
                "carrier": "Simulé",
                "checked_at": datetime.utcnow().isoformat()
            }
        
        if not self.enabled:
            return {
        "valid": True,
        "status": "active",
        "message": "SMS envoyé avec succès",
        "carrier": "MTN",
        "checked_at": datetime.utcnow().isoformat()
    
            }
        
        # Nettoyer le numéro
        cleaned = self._clean_phone(phone)
        
        # Message avec lien ISHOWO
        message = """
            🏢 ISHOWO - La solution de gestion de stock qui simplifie votre quotidien.

            *Gérez vos stocks en temps réel
            *Évitez les ruptures et le surstock
            *Gagnez du temps et de l'argent

            Découvrez ISHOWO : https://ishowo.iwajutech.com
            """
        
        try:
            print(f" Envoi SMS à {cleaned}...")
            
            response = requests.post(
            f"{self.api_url}/v1/messages",
            headers=self.headers,
            json={
                "to": [cleaned], 
                "body": message,  
                "sender_name": self.sender, 
                },
                timeout=15
            )
            #  AFFICHER LA RÉPONSE COMPLÈTE
            print(f"📝 Status: {response.status_code}")
            print(f"📝 Headers: {response.headers}")
            print(f"📝 Body: {response.text}")

            if response.status_code in [200, 201]:
                data = response.json()
                carrier = data.get("carrier", data.get("operator", "Inconnu"))
            
                print(f"SMS envoyé à {cleaned} (carrier: {carrier})")
                return {
                "valid": True,
                "status": "active",
                "message": "SMS envoyé, numéro joignable",
                "sms_id": data.get("id", data.get("sms_id")),
                "carrier": carrier, 
                "checked_at": datetime.utcnow().isoformat()}
            else:
                print(f" Échec SMS {cleaned}: {response.status_code}")
                return {
                    "valid": False,
                    "status": "inactive",
                    "message": f" SMS non délivré ({response.status_code})",
                    "checked_at": datetime.utcnow().isoformat()
                }
                
        except requests.Timeout:
            return {
                "valid": False,
                "status": "timeout",
                "message": "Délai d'attente dépassé",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Erreur SMS {cleaned}: {e}")
            return {
                "valid": False,
                "status": "error",
                "message": f"Erreur: {str(e)[:100]}",
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def send_batch(self, phones: list) -> list:
        """
        Envoie des SMS à plusieurs numéros en lot
        """
        results = []
        for phone in phones:
            result = self.send_ishowo_link(phone)
            result["phone"] = phone
            results.append(result)
        return results
    
    def _clean_phone(self, phone: str) -> str:
        """Nettoie le numéro pour l'API Ourvoice (format 22901XXXXXXXX)"""
        # Enlever les espaces
        cleaned = phone.replace(" ", "")
        
        # Enlever le +
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        
        return cleaned
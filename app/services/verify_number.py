import os
import uuid
import requests
from datetime import datetime
from typing import Dict, Any

class PhoneVerifier:
    """
    Service de vérification OurVoice avec webhook et message vocal
    """

    def __init__(self):
        self.api_key = os.getenv("OURVOICE_API_KEY")
        self.api_url = os.getenv("OURVOICE_API_URL", "https://api.getourvoice.com")
        self.caller_id = os.getenv("OURVOICE_CALLER_ID", "2290166477424")
        self.webhook_url = os.getenv("OURVOICE_WEBHOOK_URL", "https://ishowo-prospect.com/webhook/ourvoice")
        self.pending_requests = {}
        self.audio_url = os.getenv("OURVOICE_AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
        
        if not self.api_key:
            print(" OURVOICE_API_KEY non définie")
    
    def trigger_call(self, phone: str) -> Dict[str, Any]:
        """
        Lance un appel vocal vers le numéro avec un message ISHOWO
        """
        cleaned_phone = self._clean_phone(phone)
        request_id = str(uuid.uuid4())
        
        # Stocker la requête en attente
        self.pending_requests[request_id] = {
            "phone": [cleaned_phone],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        #  Payload pour l'appel avec message vocal
        payload = {
            "from": self.caller_id,
            "to": [cleaned_phone],
            "timeout": 15,
            "play_audio": False,
            "audio_url": self.audio_url, 
            "callback_url": f"{self.webhook_url}?request_id={request_id}",
            "max_attempts": 1
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"Appel vocal vers {cleaned_phone}...")
            response = requests.post(
                f"{self.api_url}/v1/calls",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "request_id": request_id,
                    "message": " Appel vocal lancé",
                    "call_id": data.get("call_id"),
                    "checked_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "request_id": request_id,
                    "message": f" Erreur OurVoice: {response.status_code}",
                    "error": response.text
                }
                
        except requests.Timeout:
            return {
                "success": False,
                "request_id": request_id,
                "message": "⏰ Timeout OurVoice"
            }
        except Exception as e:
            return {
                "success": False,
                "request_id": request_id,
                "message": f"❌ Erreur: {str(e)}"
            }
    
    def handle_webhook(self, request_id: str, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite le retour du webhook OurVoice
        """
        print(f"📩 [Webhook] Reçu pour request_id: {request_id}")
        
        pending = self.pending_requests.get(request_id)
        if not pending:
            return {"status": "error", "message": "Requête inconnue"}
        
        call_status = call_data.get("status", "unknown")
        
        # Statuts considérés comme "joignables"
        valid_statuses = ["ringing", "no-answer", "completed", "answered", "success"]
        is_valid = call_status in valid_statuses
        
        self.pending_requests[request_id]["status"] = "completed"
        self.pending_requests[request_id]["result"] = {
            "valid": is_valid,
            "status": call_status,
            "call_id": call_data.get("call_id"),
            "duration": call_data.get("duration", 0),
            "carrier": call_data.get("carrier"),
            "checked_at": datetime.utcnow().isoformat()
        }
        
        print(f"📊 Résultat: {' JOIGNABLE' if is_valid else ' NON JOIGNABLE'}")
        
        return {
            "status": "received",
            "valid": is_valid,
            "request_id": request_id,
            "phone": pending.get("phone"),
            "result": self.pending_requests[request_id]["result"]
        }
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'une requête"""
        pending = self.pending_requests.get(request_id)
        if not pending:
            return {"status": "not_found"}
        return pending
    
    def _clean_phone(self, phone: str) -> str:
        """Nettoie le numéro pour l'API Ourvoice (format 22901XXXXXXXX)"""
        # Enlever les espaces
        cleaned = phone.replace(" ", "")
        
        # Enlever le +
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        
        return cleaned
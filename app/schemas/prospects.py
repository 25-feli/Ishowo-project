from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ============ SCHÉMAS EXISTANTS ============
class ProspectCreate(BaseModel):
    """Schéma pour la création d'un prospect"""
    name: str
    phone: str
    sector: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    source: str = "unknown"

class ProspectResponse(BaseModel):
    """Schéma pour la réponse API"""
    id: int
    name: str
    phone: str
    sector: Optional[str]
    city: Optional[str]
    address: Optional[str]
    business_type: Optional[str]
    stock_management_need: bool
    score: float
    ai_justification: Optional[str]
    source: Optional[str]
    phone_validation: Optional[str]
    
    class Config:
        from_attributes = True

# ============ NOUVEAUX SCHÉMAS ============
class CollectResponse(BaseModel):
    """Réponse pour la collecte de prospects"""
    status: str = "success"
    total_extracted: int
    new_prospects: int
    duplicates: int
    errors: List[str] = []
    details: List[str] = []

class ProcessRequest(BaseModel):
    """Requête pour le traitement IA"""
    prospect_ids: Optional[List[int]] = None  

class BatchProcessResponse(BaseModel):
    """Réponse pour le traitement en lot"""
    total_processed: int
    success: int
    failed: int
    details: List[dict] = []
    status: Optional[str] = None
    message: Optional[str] = None

class AnalyzeResponse(BaseModel):
    """Réponse de l'analyse IA"""
    business_type: str
    stock_management_need: bool
    score: float
    justification: str

class VerifyResponse(BaseModel):
    """Réponse de la vérification téléphonique"""
    prospect_id: int
    prospect_name: str
    phone: str
    valid: bool
    status: str
    message: str
    carrier: Optional[str] = None
    checked_at: Optional[str] = None
    status_text: str

class ProspectsListResponse(BaseModel):
    """Réponse liste des prospects"""
    total: int
    prospects: List[dict]
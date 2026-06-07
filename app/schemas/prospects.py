from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class ProspectBase(BaseModel):
    """Schéma de base pour les prospects """
    name: str = Field(..., min_length=1, max_length=255)
    sector: Optional[str] = Field(None, max_length=150)
    city: Optional[str] = Field(None, max_length=100)
    phone: str
    description: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)
    
    @field_validator('phone')
    def validate_phone(cls, v):
        if not v or len(v.strip()) < 8:
            raise ValueError('Numéro de téléphone invalide')
        return v

class ProspectCreate(ProspectBase):
    """Schéma pour la création"""
    pass

class ProspectResponse(ProspectBase):
    """Schéma de réponse"""
    id: int
    business_type: Optional[str] = None
    stock_management_need: bool = False
    score: float = 0.0
    ai_justification: Optional[str] = None
    is_processed: bool = False
    created_at: datetime
    updated_at: datetime
    user_id: Optional[int] = None
    
    class Config:
        from_attributes = True
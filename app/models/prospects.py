from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from database.config import Base

class Prospect(Base):  
    __tablename__ = "prospects" 
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    sector = Column(String(150), nullable=True)
    city = Column(String(100), nullable=True)
    phone = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Champs d'analyse IA
    business_type = Column(String(50), nullable=True)
    stock_management_need = Column(Boolean, default=False)
    score = Column(Float, default=0.0)
    ai_justification = Column(Text, nullable=True)
    
    # Métadonnées
    source = Column(String(100), nullable=True)
    raw_data = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation avec User (si nécessaire)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    def __repr__(self):
        return f"<Prospect(id={self.id}, name='{self.name}', score={self.score})>"
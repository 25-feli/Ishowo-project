from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from datetime import datetime
from app.database.config import Base

class Prospect(Base):
    __tablename__ = "prospects"  
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, nullable=False)
    sector = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    business_type = Column(String(50), nullable=True)
    stock_management_need = Column(Boolean, default=False)
    score = Column(Float, default=0.0)
    ai_justification = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    source_url = Column(String(500), nullable=True)
    phone_validation = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
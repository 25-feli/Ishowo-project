from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database.config import Base

class ScrapingState(Base):
    __tablename__ = "scraping_state"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), unique=True, nullable=False)  # "africa", "showroom"
    last_page = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import re
import requests
from bs4 import BeautifulSoup
import random
import time
import os

# BASE DE DONNÉES SQLITE 
DATABASE_URL = "sqlite:///./prospects.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MODÈLE PROSPECT 
class Prospect(Base):
    __tablename__ = "prospects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, nullable=False)
    sector = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    business_type = Column(String(50), nullable=True)
    score = Column(Float, default=0.0)
    ai_justification = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# SCHÉMAS PYDANTIC
class ProspectResponse(BaseModel):
    id: int
    name: str
    phone: str
    sector: Optional[str]
    city: Optional[str]
    business_type: Optional[str]
    score: float
    ai_justification: Optional[str]
    
    class Config:
        from_attributes = True

class CollectResponse(BaseModel):
    total_extracted: int
    new_prospects: int
    duplicates: int

# NORMALISATION TÉLÉPHONE 
def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    cleaned = re.sub(r'[^\d]', '', phone)
    if cleaned.startswith('229'):
        cleaned = cleaned[3:]
    if len(cleaned) > 8:
        cleaned = cleaned[-8:]
    if len(cleaned) != 8:
        return ""
    return f"+229 01 {cleaned[0:2]} {cleaned[2:4]} {cleaned[4:6]} {cleaned[6:8]}"

# SCRAPING GO AFRICA (VERSION ROBUSTE)
def scrape_go_africa():
    prospects = []
    try:
        url = "https://www.goafricaonline.com/bj/annuaire-resultat?type=company&where=country-BJ"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Chercher les articles avec data-company-id
        articles = soup.find_all('article', attrs={'data-company-id': True})
        
        for article in articles:
            try:
                # Nom
                name_elem = article.find('h2')
                name = ""
                if name_elem:
                    link = name_elem.find('a')
                    name = link.get_text(strip=True) if link else name_elem.get_text(strip=True)
                
                # Téléphone
                phone_links = article.find_all('a', href=lambda x: x and 'tel:' in x)
                phone = ""
                for phone_link in phone_links:
                    phone_href = phone_link.get('href', '')
                    if 'tel:' in phone_href:
                        phone = phone_href.replace('tel:', '').strip()
                        break
                
                # Secteur
                sector_elem = article.find('div', class_=re.compile(r'text-brand-blue'))
                sector = sector_elem.get_text(strip=True) if sector_elem else ""
                
                # Ville
                address_elem = article.find('address')
                city = address_elem.get_text(strip=True) if address_elem else "Cotonou"
                if city:
                    city_lines = city.split('\n')
                    city = city_lines[-1].strip() if city_lines else "Cotonou"
                
                if name and phone:
                    normalized_phone = normalize_phone(phone)
                    if normalized_phone:
                        prospects.append({
                            'name': name[:100],
                            'phone': normalized_phone,
                            'sector': sector[:100],
                            'city': city[:100],
                            'description': ""
                        })
            except Exception:
                continue
        
        print(f"{len(prospects)} prospects trouvés")
        return prospects
        
    except Exception as e:
        print(f"Erreur scraping: {e}")
        return []


# IA MOCK (simule Ollama)
def mock_ai_analysis(name: str):
    name_lower = name.lower()
    
    if 'pharmacie' in name_lower or 'pharma' in name_lower:
        return {
            'business_type': 'pharmacie',
            'score': round(random.uniform(8.5, 9.8), 1),
            'justification': 'Pharmacie - besoin critique de gestion de stock pour les médicaments'
        }
    elif 'super' in name_lower or 'boutique' in name_lower or 'magasin' in name_lower:
        return {
            'business_type': 'commerce',
            'score': round(random.uniform(6.5, 8.5), 1),
            'justification': 'Commerce - besoin modéré de gestion de stock'
        }
    elif 'restaurant' in name_lower or 'bar' in name_lower:
        return {
            'business_type': 'restaurant',
            'score': round(random.uniform(5.0, 7.0), 1),
            'justification': 'Restaurant - besoin de suivi des stocks alimentaires'
        }
    else:
        return {
            'business_type': 'service',
            'score': round(random.uniform(2.0, 5.0), 1),
            'justification': 'Service - faible besoin de gestion de stock'
        }

# REPOSITORY 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ProspectRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, name, phone, sector, city, description):
        existing = self.db.query(Prospect).filter(Prospect.phone == phone).first()
        if existing:
            return None
        prospect = Prospect(
            name=name, phone=phone, sector=sector,
            city=city, description=description
        )
        self.db.add(prospect)
        self.db.commit()
        self.db.refresh(prospect)
        return prospect
    
    def get_all_unprocessed(self):
        return self.db.query(Prospect).filter(Prospect.is_processed == False).all()
    
    def update(self, prospect_id, data):
        prospect = self.db.query(Prospect).filter(Prospect.id == prospect_id).first()
        if prospect:
            for key, value in data.items():
                setattr(prospect, key, value)
            self.db.commit()
            self.db.refresh(prospect)
        return prospect
    
    def get_all_sorted(self):
        return self.db.query(Prospect).order_by(Prospect.score.desc()).all()

# API 
app = FastAPI(title="Prospect API pour ISHOWO")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    print("=" * 50)
    print("API ISHOWO démarrée")
    print("Base: SQLite (prospects.db)")
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("=" * 50)

@app.get("/")
async def root():
    return {"message": "API ISHOWO - Prospection intelligente", "status": "online"}

@app.post("/collect", response_model=CollectResponse)
async def collect(use_test_data: bool = False, db: Session = Depends(get_db)):
    """Collecte les prospects - use_test_data=True pour utiliser les données de test"""
    
    if use_test_data:
        raw_prospects = get_test_prospects()
        print("Utilisation des données de test")
    else:
        raw_prospects = scrape_go_africa()
        if not raw_prospects:
            print("Scraping vide, utilisation des données de test")
            raw_prospects = get_test_prospects()
    
    repo = ProspectRepository(db)
    new_count = 0
    for p in raw_prospects:
        result = repo.create(p['name'], p['phone'], p['sector'], p['city'], "")
        if result:
            new_count += 1
    
    return CollectResponse(
        total_extracted=len(raw_prospects),
        new_prospects=new_count,
        duplicates=len(raw_prospects) - new_count
    )

@app.post("/process")
async def process(db: Session = Depends(get_db)):
    """Analyse IA des prospects"""
    repo = ProspectRepository(db)
    prospects = repo.get_all_unprocessed()
    
    processed = 0
    for prospect in prospects:
        analysis = mock_ai_analysis(prospect.name)
        repo.update(prospect.id, {
            'business_type': analysis['business_type'],
            'score': analysis['score'],
            'ai_justification': analysis['justification'],
            'is_processed': True
        })
        processed += 1
    
    return {"processed": processed, "total": len(prospects), "message": "Analyse IA terminée"}

@app.get("/prospects", response_model=List[ProspectResponse])
async def get_prospects(db: Session = Depends(get_db)):
    """Liste des prospects triés par score"""
    repo = ProspectRepository(db)
    prospects = repo.get_all_sorted()
    return prospects



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
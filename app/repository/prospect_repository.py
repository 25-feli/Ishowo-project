import json
import os


from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.prospects import Prospect
from app.schemas.prospects import ProspectCreate
from app.models.scraping_state import ScrapingState

STATE_FILE = "scraping_state.json"

class ProspectRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, prospect_data: ProspectCreate) -> Optional[Prospect]:
        """Crée un nouveau prospect"""
        try:
            print(f"CRÉATION: {prospect_data.name} - {prospect_data.phone}")
            
            prospect = Prospect(
                name=prospect_data.name,
                phone=prospect_data.phone,
                sector=prospect_data.sector,
                city=prospect_data.city,
                description=prospect_data.description,
                source=prospect_data.source,
                is_processed=False,
                stock_management_need=False,
                score=0.0
            )
            
            self.db.add(prospect)
            self.db.commit()  
            self.db.refresh(prospect)
            
            print(f" PROSPECT CRÉÉ: ID={prospect.id}")
            return prospect
            
        except Exception as e:
            self.db.rollback()
            print(f"ERREUR CRÉATION: {e}")
            return None
    
    def check_duplicate(self, phone: str) -> bool:
        return self.db.query(Prospect).filter(Prospect.phone == phone).first() is not None
    
    def get_by_id(self, prospect_id: int) -> Optional[Prospect]:
        return self.db.query(Prospect).filter(Prospect.id == prospect_id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, sort_by_score: bool = True) -> List[Prospect]:
        query = self.db.query(Prospect)
        if sort_by_score:
            query = query.order_by(Prospect.score.desc())
        return query.offset(skip).limit(limit).all()
    
    def get_by_score_range(self, min_score: float, max_score: float = 10) -> List[Prospect]:
        return self.db.query(Prospect).filter(
            Prospect.score >= min_score,
            Prospect.score <= max_score
        ).order_by(Prospect.score.desc()).all()
    
    def get_all_unprocessed(self) -> List[Prospect]:
        return self.db.query(Prospect).filter(Prospect.is_processed == False).all()

    def get_all_unverified(self) -> List[Prospect]:
        return self.db.query(Prospect).filter(Prospect.phone_validation.is_(None)).all()
    
    def update(self, prospect_id: int, data: dict) -> Optional[Prospect]:
        prospect = self.get_by_id(prospect_id)
        if prospect:
            for key, value in data.items():
                setattr(prospect, key, value)
            try:
                self.db.commit()
                self.db.refresh(prospect)
                return prospect
            except Exception as e:
                self.db.rollback()
                print(f"Erreur mise à jour: {e}")
                return None
        return None
    

    def get_last_page(self, source: str) -> int:
        """Récupère la dernière page scrappée depuis un fichier JSON"""
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get(source, 1)
        except:
            return 1

    def update_last_page(self, source: str, page: int):
        """Met à jour la dernière page scrappée dans un fichier JSON"""
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}
        data[source] = page
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)

    def get_stats(self) -> dict:
        from sqlalchemy import func
        
        total = self.db.query(func.count(Prospect.id)).scalar() or 0
        analyzed = self.db.query(func.count(Prospect.id)).filter(
            Prospect.is_processed == True
        ).scalar() or 0
        verified = self.db.query(func.count(Prospect.id)).filter(
            Prospect.phone_validation.isnot(None)
        ).scalar() or 0
        high_score = self.db.query(func.count(Prospect.id)).filter(
        Prospect.score >= 7.0 
        ).scalar() or 0
        
        return {
            "total_prospects": total,
            "analyzed": analyzed,
            "verified": verified,
            "high_score":high_score,
            "pending_analysis": total - analyzed,
            "pending_verification": total - verified
        }
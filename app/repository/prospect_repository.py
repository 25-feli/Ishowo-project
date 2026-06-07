from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.prospects import Prospect
from app.schemas.prospects import ProspectCreate

class ProspectRepository:
    """Repository Pattern pour les prospects"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, item_data: ProspectCreate, user_id: Optional[int] = None) -> Prospect:
        """Crée un nouveau prospect"""
        db_item = Prospect(**item_data.dict())
        if user_id:
            db_item.user_id = user_id
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    def get_by_id(self, item_id: int) -> Optional[Prospect]:
        return self.db.query(Prospect).filter(Prospect.id == item_id).first()
    
    def get_by_phone(self, phone: str) -> Optional[Prospect]:
        return self.db.query(Prospect).filter(Prospect.phone == phone).first()
    
    def get_all_unprocessed(self) -> List[Prospect]:
        return self.db.query(Prospect).filter(Prospect.is_processed == False).all()
    
    def get_all(self, skip: int = 0, limit: int = 100, sort_by_score: bool = True) -> List[Prospect]:
        query = self.db.query(Prospect)
        if sort_by_score:
            query = query.order_by(Prospect.score.desc())
        return query.offset(skip).limit(limit).all()
    
    def update(self, item_id: int, update_data: dict) -> Optional[Prospect]:
        item = self.get_by_id(item_id)
        if item:
            for key, value in update_data.items():
                setattr(item, key, value)
            self.db.commit()
            self.db.refresh(item)
        return item
    
    def check_duplicate(self, phone: str, name: str = None) -> bool:
        query = self.db.query(Prospect).filter(Prospect.phone == phone)
        if name:
            query = query.filter(Prospect.name == name)
        return query.first() is not None
    
    def delete(self, prospect_id: int) -> bool:
        item = self.get_by_id(prospect_id)
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from database.config import get_db
from app.repository.prospect_repository import ProspectRepository
from services.scraper import ScraperService
from services.normaliseur import DataNormaliseur
from services.ai import AIService
from app.schemas.prospects import ProspectResponse, ProspectCreate
import os

router = APIRouter()

scraper_service = ScraperService(
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    google_cse_id=os.getenv("GOOGLE_CSE_ID")
)
ai_service = AIService()

@router.post("/collect")
async def collect_prospects(
    background_tasks: BackgroundTasks,
    source: str = "all",
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Collecte des prospects"""
    # ... même code que précédemment mais avec ProspectRepository
    pass

@router.post("/process")
async def process_items(
    item_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """Traitement IA des items"""
    # ... utilisation de ProspectRepository
    pass

@router.get("/items", response_model=List[ProspectResponse])
async def get_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Liste des items"""
    repo = ProspectRepository(db)
    items = repo.get_all(skip=skip, limit=limit)
    return items
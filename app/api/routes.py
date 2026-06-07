from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from database.config import get_db
from repository.prospect_repository import ProspectRepository
from services.scraper import ScraperService
from services.normaliseur import DataNormaliseur
from services.ai import AIService
from schemas.prospects import (
    ProspectResponse, CollectResponse, ProcessRequest, 
    BatchProcessResponse, ProspectCreate
)
import os

router = APIRouter()

# Initialisation des services
scraper_service = ScraperService(
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    google_cse_id=os.getenv("GOOGLE_CSE_ID")
)
ai_service = AIService()

@router.post("/collect", response_model=CollectResponse)
async def collect_prospects(
    background_tasks: BackgroundTasks,
    source: str = "all",
    limit: int = 20,
    query: str = "entreprises Benin",
    db: Session = Depends(get_db)
):
    """
    Lance la collecte de prospects depuis les sources configurées
    """
    try:
        # Collecte des données brutes
        raw_prospects = scraper_service.collect_prospects(
            source=source,
            limit=limit,
            query=query
        )
        
        if not raw_prospects:
            raise HTTPException(status_code=404, detail="Aucun prospect trouvé")
        
        # Normalisation et insertion
        repo = ProspectRepository(db)
        new_prospects = []
        duplicates = []
        
        for raw_data in raw_prospects:
            try:
                # Normalisation
                normalized = DataNormaliseur.normalize_prospect(raw_data)
                
                # Validation
                if DataNormaliseur.validate_prospect(normalized):
                    # Vérification des doublons
                    if not repo.check_duplicate(normalized.phone):
                        prospect = repo.create(normalized)
                        new_prospects.append(prospect)
                        
                        # Ajout au background task pour traitement IA
                        background_tasks.add_task(
                            ai_service.analyze_and_update_prospect,
                            prospect.id,
                            db
                        )
                    else:
                        duplicates.append({
                            "name": normalized.name,
                            "phone": normalized.phone
                        })
            except Exception as e:
                print(f"Erreur lors du traitement d'un prospect: {str(e)}")
                continue
        
        return CollectResponse(
            total_extracted=len(raw_prospects),
            new_prospects=len(new_prospects),
            duplicates=len(duplicates),
            details=[f"{p.name} ({p.phone})" for p in new_prospects[:5]]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la collecte: {str(e)}")

@router.post("/process", response_model=BatchProcessResponse)
async def process_prospects(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Traite les prospects avec l'IA pour le scoring et la classification
    """
    try:
        repo = ProspectRepository(db)
        
        # Récupération des prospects à traiter
        if request.prospect_ids:
            prospects = []
            for pid in request.prospect_ids:
                prospect = repo.get_by_id(pid)
                if prospect and not prospect.is_processed:
                    prospects.append(prospect)
        else:
            prospects = repo.get_all_unprocessed()
        
        if not prospects:
            return BatchProcessResponse(
                total_processed=0,
                success=0,
                failed=0,
                details=[]
            )
        
        processed = []
        failed = []
        
        for prospect in prospects:
            try:
                # Préparer les données pour l'IA
                prospect_data = {
                    'name': prospect.name,
                    'sector': prospect.sector,
                    'city': prospect.city,
                    'description': prospect.description
                }
                
                # Analyse IA
                analysis = await ai_service.analyze_prospect(prospect_data)
                
                # Mise à jour du prospect
                update_data = {
                    'business_type': analysis.business_type,
                    'stock_management_need': analysis.stock_management_need,
                    'score': analysis.score,
                    'ai_justification': analysis.justification,
                    'is_processed': True
                }
                
                updated = repo.update(prospect.id, update_data)
                if updated:
                    processed.append({
                        'id': prospect.id,
                        'name': prospect.name,
                        'score': analysis.score
                    })
                else:
                    failed.append({'id': prospect.id, 'reason': 'Erreur mise à jour'})
                    
            except Exception as e:
                failed.append({'id': prospect.id, 'reason': str(e)})
        
        return BatchProcessResponse(
            total_processed=len(prospects),
            success=len(processed),
            failed=len(failed),
            details=processed[:10]  # Limiter les détails dans la réponse
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@router.get("/prospects", response_model=List[ProspectResponse])
async def get_prospects(
    skip: int = 0,
    limit: int = 100,
    min_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Récupère la liste des prospects qualifiés triés par score
    """
    try:
        repo = ProspectRepository(db)
        
        if min_score is not None:
            prospects = repo.get_by_score_range(min_score, 10)
        else:
            prospects = repo.get_all(skip=skip, limit=limit, sort_by_score=True)
        
        return prospects
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "API ISHOWO - Prospection intelligente",
        "endpoints": {
            "docs": "/docs",
            "collect": "POST /collect",
            "process": "POST /process", 
            "prospects": "GET /prospects"
        }
    }

@router.get("/prospects/{prospect_id}", response_model=ProspectResponse)
async def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupère un prospect spécifique par son ID
    """
    repo = ProspectRepository(db)
    prospect = repo.get_by_id(prospect_id)
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")
    
    return prospect

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Statistiques sur les prospects
    """
    from sqlalchemy import func
    
    total = db.query(func.count(get_prospects.id)).sc
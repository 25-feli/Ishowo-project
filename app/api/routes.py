import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime


# IMPORTS CORRECTS
from app.database.config import get_db
from app.repository.prospect_repository import ProspectRepository
from app.services.scraper import ScraperService
from app.services.normaliseur import DataNormaliseur
from app.services.ai import AIService
from app.services.verify_number import PhoneVerifier
from app.schemas.prospects import (
    ProspectResponse, 
    CollectResponse, 
    ProcessRequest, 
    BatchProcessResponse,
    AnalyzeResponse,
    VerifyResponse,
    ProspectCreate
)
from app.models.prospects import Prospect

router = APIRouter()

# Initialisation des services
scraper_service = ScraperService()
ai_service = AIService()
phone_verifier = PhoneVerifier()


#============ ROUTE 1: COLLECT ============
@router.post("/collect", response_model=CollectResponse)
async def collect_prospects(
    background_tasks: BackgroundTasks,
    source: str = "all",
    limit: int = 15,
    max_pages: int = 300,
    query: str = "entreprises Benin",
    db: Session = Depends(get_db)
):
    """
    Lance la collecte de prospects
    """
    try:
        print(f"\n COLLECT: source={source}, limit={limit}")
        
        # 1. Collecte des données brutes
        raw_prospects = scraper_service.collect_prospects(
            source=source,
            limit=limit,
            max_pages=max_pages,
            query=query
        )
        
        if not raw_prospects:
            return CollectResponse(
                status="no_prospects",
                total_extracted=0,
                new_prospects=0,
                duplicates=0,
                errors=["Aucun prospect trouvé"]
            )
        
        # 2. Normalisation et insertion
        repo = ProspectRepository(db)
        new_prospects = []
        duplicates = []
        errors = []
        
        for raw_data in raw_prospects:
            try:
                # Normalisation
                normalized = DataNormaliseur.normalize_prospect(raw_data)
                print(f" Normalisé: {normalized.name} - {normalized.phone}")
                
                # Validation
                if DataNormaliseur.validate_prospect(normalized):
                    # Vérification doublon
                    if not repo.check_duplicate(normalized.phone):
                        # Création
                        prospect = repo.create(normalized)
                        if prospect:
                            new_prospects.append(prospect)
                            print(f" AJOUTÉ: {prospect.name} (ID: {prospect.id})")
                            
                            # Background task pour l'IA
                            background_tasks.add_task(
                                ai_service.analyze_and_update_prospect,
                                prospect.id,
                                db
                            )
                        else:
                            errors.append(f"Erreur création: {normalized.name}")
                    else:
                        duplicates.append({
                            "name": normalized.name,
                            "phone": normalized.phone
                        })
                        print(f"DOUBLON: {normalized.phone}")
                else:
                    errors.append(f"Validation échouée: {normalized.name}")
                    
            except Exception as e:
                print(f" Erreur traitement: {e}")
                errors.append(str(e))
                continue
        
        print(f"RÉSULTAT: {len(new_prospects)} nouveaux, {len(duplicates)} doublons, {len(errors)} erreurs")
        
        return CollectResponse(
            total_extracted=len(raw_prospects),
            new_prospects=len(new_prospects),
            duplicates=len(duplicates),
            errors=errors[:5],
            details=[f"{p.name} ({p.phone})" for p in new_prospects[:5]]
        )
        
    except Exception as e:
        print(f"ERREUR COLLECT: {e}")
        return CollectResponse(
            status="error",
            total_extracted=0,
            new_prospects=0,
            duplicates=0,
            errors=[str(e)]
        )

# ============ ROUTE 2: PROCESS-FULL ============
@router.post("/process-full")
async def process_full_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Pipeline complet :
    1. Analyse IA de tous les prospects
    2. Vérification téléphonique de tous les prospects
    (exécuté en arrière-plan)
    """
    repo = ProspectRepository(db)
    
    # Récupérer tous les prospects
    all_prospects = repo.get_all(skip=0, limit=1000)
    
    if not all_prospects:
        return {
            "status": "no_prospects",
            "message": "Aucun prospect à traiter",
            "total": 0
        }
    
    # Lancer le pipeline complet en arrière-plan
    background_tasks.add_task(
        process_full_pipeline_task,
        [p.id for p in all_prospects],
        db
    )
    
    return {
        "status": "processing",
        "total": len(all_prospects),
        "message": f"Pipeline complet démarré pour {len(all_prospects)} prospects"
    }


def process_full_pipeline_task(prospect_ids: List[int], db: Session):
    """Pipeline complet en arrière-plan"""
    repo = ProspectRepository(db)
    
    for i, pid in enumerate(prospect_ids):
        prospect = repo.get_by_id(pid)
        if not prospect:
            continue
        
        print(f"\n Traitement {i+1}/{len(prospect_ids)}: {prospect.name}")
        
        # 1. Analyse IA
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            analysis = loop.run_until_complete(
                ai_service.analyze_prospect({
                    'name': prospect.name,
                    'sector': prospect.sector or '',
                    'description': prospect.description or '',
                    'address': prospect.address or ''
                })
            )
            loop.close()
            
            repo.update(pid, {
                'business_type': analysis['business_type'],
                'stock_management_need': analysis['stock_management_need'],
                'score': analysis['score'],
                'ai_justification': analysis['justification'],
                'is_processed': True
            })
            
            print(f" IA: {analysis['business_type']} (score: {analysis['score']})")
            
        except Exception as e:
            print(f" IA erreur: {e}")
            repo.update(pid, {
                'is_processed': True,
                'ai_justification': f"Erreur: {str(e)[:100]}"
            })
        
        # 2. Vérification téléphonique
        if prospect.phone:
            try:
                verifier = PhoneVerifier()
                result = verifier.verify(prospect.phone)
                repo.update(pid, {
                    'phone_validation': json.dumps(result)
                })
                print(f" Tél: {'JOIGNABLE' if result.get('valid') else 'NON JOIGNABLE'}")
            except Exception as e:
                print(f" Tél erreur: {e}")


# ============ ROUTE 3: PROSPECTS (AFFICHAGE JSON) ============
@router.get("/prospects")
async def get_prospects_json_direct(
    db: Session = Depends(get_db),
    limit: int = 200,
    min_score: Optional[float] = None
):
    """
    Affiche les prospects en JSON avec toutes les analyses et vérifications
    """
    repo = ProspectRepository(db)
    
    # Récupérer les prospects
    if min_score:
        prospects = repo.get_by_score_range(min_score, 10)
    else:
        prospects = repo.get_all(skip=0, limit=limit, sort_by_score=True)
    
    # Formater les données COMPLÈTES
    results = []
    for p in prospects:
        # Décoder la vérification téléphonique
        phone_validation = None
        if p.phone_validation:
            try:
                phone_validation = json.loads(p.phone_validation)
            except:
                phone_validation = {"error": "Invalid JSON"}
        
        results.append({
            "id": p.id,
            "name": p.name,
            "phone": p.phone,
            "sector": p.sector,
            "city": p.city,
            "address": p.address,
            "description": p.description,
            "source": p.source,
            "source_url": p.source_url,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            # === ANALYSE IA ===
            "analysis": {
                "business_type": p.business_type,
                "stock_management_need": p.stock_management_need,
                "score": p.score,
                "justification": p.ai_justification,
                "analyzed": p.is_processed
            },
            # === VÉRIFICATION TÉLÉPHONIQUE ===
            "phone_verification": {
                "valid": phone_validation.get('valid', False) if phone_validation else None,
                "status": phone_validation.get('status', 'Non vérifié') if phone_validation else 'Non vérifié',
                "message": phone_validation.get('message', '') if phone_validation else '',
                "carrier": phone_validation.get('carrier', '') if phone_validation else '',
                "checked_at": phone_validation.get('checked_at', '') if phone_validation else ''
            } if phone_validation else None
        })
    
    return {
        "total": len(results),
        "count": len(results),
        "prospects": results
    }


# ============ ROUTE 4: PROSPECTS (EXPORT JSON) ============
@router.get("/prospects/export/json")
async def export_prospects_json(db: Session = Depends(get_db)):
    """
    Télécharge tous les prospects au format JSON
    """
    repo = ProspectRepository(db)
    prospects = repo.get_all(skip=0, limit=10000, sort_by_score=True)
    
    # Formater les données COMPLÈTES
    results = []
    for p in prospects:
        phone_validation = None
        if p.phone_validation:
            try:
                phone_validation = json.loads(p.phone_validation)
            except:
                phone_validation = {"error": "Invalid JSON"}
        
        results.append({
            "id": p.id,
            "name": p.name,
            "phone": p.phone,
            "sector": p.sector,
            "city": p.city,
            "address": p.address,
            "description": p.description,
            "source": p.source,
            "source_url": p.source_url,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "analysis": {
                "business_type": p.business_type,
                "stock_management_need": p.stock_management_need,
                "score": p.score,
                "justification": p.ai_justification,
                "analyzed": p.is_processed
            },
            "phone_verification": {
                "valid": phone_validation.get('valid', False) if phone_validation else None,
                "status": phone_validation.get('status', 'Non vérifié') if phone_validation else 'Non vérifié',
                "message": phone_validation.get('message', '') if phone_validation else '',
                "carrier": phone_validation.get('carrier', '') if phone_validation else '',
                "checked_at": phone_validation.get('checked_at', '') if phone_validation else ''
            } if phone_validation else None
        })
    
    json_data = json.dumps(results, indent=2, ensure_ascii=False)
    filename = f"prospects_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return Response(
        content=json_data,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ============ ROUTE 5: STATS ============
@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Statistiques"""
    repo = ProspectRepository(db)
    stats = repo.get_stats()
    return stats


# ============ ROUTE 6: TEST INSERT ============
@router.post("/test/insert")
async def test_insert(db: Session = Depends(get_db)):
    """Route de test pour insérer un prospect manuellement"""
    from app.services.normaliseur import normalize
    
    try:
        repo = ProspectRepository(db)
        
        # Créer un objet ProspectCreate (pas une classe personnalisée)
        test = ProspectCreate(
            name="ENTREPRISE TEST",
            phone=normalize("+229 01 12 34 56 78"),
            sector="Test",
            city="Cotonou",
            description="Description test",
            source="test_manual"
        )
        
        # Insérer
        result = repo.create(test)
        
        if result:
            return {
                "status": "success",
                "message": "Prospect test créé",
                "id": result.id,
                "name": result.name,
                "phone": result.phone
            }
        else:
            return {
                "status": "error",
                "message": "Échec de la création"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ============ ROUTE 7: ROOT ============
@router.get("/")
async def root():
    """Page d'accueil"""
    return {
        "service": "ISHOWO - Prospection intelligente",
        "version": "1.0.0",
        "endpoints": {
            "collect": "POST /collect",
            "process-full": "POST /process-full",
            "prospects": "GET /prospects",
            "prospects/export/json": "GET /prospects/export/json",
            "stats": "GET /stats",
            "test/insert": "POST /test/insert"
        },
        "docs": "/docs"
    }
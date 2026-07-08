import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import logging

# IMPORTS CORRECTS
from app.database.config import get_db
from app.database import SessionLocal
from app.repository.prospect_repository import ProspectRepository
from app.services.scraper import ScraperService
from app.services.normaliseur import DataNormaliseur
from app.services.ai import AIService
from app.services.verify_number import PhoneVerifier
from app.services.service_sms import SmsService  
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
executor = ThreadPoolExecutor(max_workers=10) 
logger = logging.getLogger(__name__)

# Initialisation des services
scraper_service = ScraperService()
ai_service = AIService()
phone_verifier = PhoneVerifier()
sms_service = SmsService() 


# ============ ROUTE 1: COLLECT ============
@router.post("/collect", response_model=CollectResponse)
async def collect_prospects(
    background_tasks: BackgroundTasks,
    source: str = "all",
    limit: int = 15,
    max_pages: int = 300,
    query: str = "entreprises Benin",
    db: Session = Depends(get_db)
):
    try:
        repo = ProspectRepository(db)
        
        # 1. Vérifier si la base est vide
        total_prospects = repo.count_all()
        
        # 2. Déterminer la page de départ
        if total_prospects == 0:
            page = 1
            print(f"\n Base vide → Démarrage à la page 1")
        else:
            # Récupérer la dernière page depuis le fichier JSON
            page = repo.get_last_page(source) or 1
            print(f"\n Base non vide → Continuation à la page {page}")
        
        print(f" COLLECT: source={source}, limit={limit}, page={page}")
        
        # 3. Collecte
        raw_prospects = scraper_service.collect_prospects(
            source=source,
            limit=limit,
            max_pages=max_pages,
            page=page,
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
        
        # 4. Traitement des prospects
        new_prospects = []
        duplicates = []
        errors = []
        
        for raw_data in raw_prospects:
            try:
                normalized = DataNormaliseur.normalize_prospect(raw_data)
                print(f"Normalisé: {normalized.name} - {normalized.phone}")
                
                if DataNormaliseur.validate_prospect(normalized):
                    if not repo.check_duplicate(normalized.phone):
                        prospect = repo.create(normalized)
                        
                        if prospect:
                            new_prospects.append(prospect)
                            print(f" AJOUTÉ: {prospect.name} (ID: {prospect.id})")
                            
                            if not prospect.is_processed:
                                background_tasks.add_task(
                                    ai_service.analyze_and_update_prospect,
                                    prospect.id,
                                    db
                                )
                            else:
                                print(f" {prospect.name} déjà analysé, ignoré.")
                        else:
                            errors.append(f"Erreur création: {normalized.name}")
                    else:
                        duplicates.append({
                            "name": normalized.name,
                            "phone": normalized.phone
                        })
                        print(f" DOUBLON: {normalized.phone}")
                else:
                    errors.append(f"Validation échouée: {normalized.name}")
                    
            except Exception as e:
                logger.error(f"Erreur traitement: {e}")
                errors.append(str(e))
                continue
        
        # 5. Mettre à jour la page (si des prospects ont été collectés)
        if raw_prospects:
            new_page = page + (len(raw_prospects) // 30) + 1
            repo.update_last_page(source, new_page)
            print(f"📄 Prochaine page: {new_page}")
        else:
            print(f"📭 Aucun prospect collecté, page inchangée")
        
        print(f"📊 RÉSULTAT: {len(new_prospects)} nouveaux, {len(duplicates)} doublons, {len(errors)} erreurs")
        
        return CollectResponse(
            total_extracted=len(raw_prospects),
            new_prospects=len(new_prospects),
            duplicates=len(duplicates),
            errors=errors[:5],
            details=[f"{p.name} ({p.phone})" for p in new_prospects[:5]]
        )
        
    except Exception as e:
        logger.error(f" ERREUR COLLECT: {e}")
        return CollectResponse(
            status="error",
            total_extracted=0,
            new_prospects=0,
            duplicates=0,
            errors=[str(e)]
        )
# ============ ROUTE 2: PROCESS-FULL (IA + SMS + APPEL) ============
@router.post("/process-full")
async def process_full_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Pipeline complet :
    1. Analyse IA de tous les prospects
    2. Vérification par SMS
    3. Vérification par appel (si SMS échoue)
    Logique OU : joignable si SMS ou Appel fonctionne
    """
    repo = ProspectRepository(db)
    all_prospects = repo.get_all(skip=0, limit=1000)

    if not all_prospects:
        return {
            "status": "no_prospects",
            "message": "Aucun prospect à traiter",
            "total": 0
        }

    prospect_ids = [p.id for p in all_prospects]
    background_tasks.add_task(process_full_pipeline_task, prospect_ids)

    return {
        "status": "processing",
        "total": len(prospect_ids),
        "message": f"Pipeline démarré pour {len(prospect_ids)} prospects"
    }


def process_one(pid: int) -> dict:
    """
    Traite un seul prospect avec IA + SMS + Appel (logique OU)
    """
    db = SessionLocal()
    try:
        repo = ProspectRepository(db)
        prospect = repo.get_by_id(pid)
        if not prospect:
            return {"pid": pid, "status": "not_found"}

        logger.info(f"Traitement: {prospect.name}")

        # 1. Analyse IA
        try:
            analysis = asyncio.run(
                ai_service.analyze_prospect({
                    'name': prospect.name,
                    'sector': prospect.sector or '',
                    'description': prospect.description or '',
                    'address': prospect.address or ''
                })
            )

            repo.update(pid, {
                'business_type': analysis['business_type'],
                'stock_management_need': analysis['stock_management_need'],
                'score': analysis['score'],
                'ai_justification': analysis['justification'],
                'is_processed': True
            })

            logger.info(f"IA: {prospect.name} -> {analysis['business_type']} (score: {analysis['score']})")

        except Exception as e:
            logger.error(f"IA erreur {prospect.name}: {e}")
            repo.update(pid, {
                'is_processed': True,
                'ai_justification': f"Erreur: {str(e)[:100]}"
            })

        # 2. VÉRIFICATION (SMS + Appel) - Logique OU
        sms_valid = False
        call_valid = False
        sms_result = None
        call_result = None
        
        if prospect.phone:
            # 2.1 Tentative SMS
            try:
                sms_result = sms_service.send_ishowo_link(prospect.phone)
                sms_valid = sms_result.get('valid', False)
                logger.info(f"📱 SMS: {prospect.name} -> {'OK' if sms_valid else 'ÉCHEC'}")
            except Exception as e:
                logger.error(f"SMS erreur {prospect.name}: {e}")
                sms_result = {"valid": False, "error": str(e)}
            
            # 2.2 Tentative Appel (si SMS échoue ou toujours)
            # On tente l'appel dans tous les cas pour avoir une double vérification
            try:
                call_result = phone_verifier.trigger_call(prospect.phone)
                call_valid = call_result.get('success', False)
                logger.info(f" Appel: {prospect.name} -> {' OK' if call_valid else 'ÉCHEC'}")
            except Exception as e:
                logger.error(f"Appel erreur {prospect.name}: {e}")
                call_result = {"success": False, "error": str(e)}
            
            # 2.3 Logique OU : joignable si SMS OU Appel OK
            is_joignable = sms_valid or call_valid
            
            # 2.4 Synthèse
            verification_result = {
                "valid": is_joignable,
                "sms": {
                    "valid": sms_valid,
                    "details": sms_result
                },
                "call": {
                    "valid": call_valid,
                    "details": call_result
                },
                "method": "sms_or_call",
                "checked_at": datetime.utcnow().isoformat()
            }
            
            repo.update(pid, {
                'phone_validation': json.dumps(verification_result)
            })
            
            logger.info(f"JOIGNABLE: {prospect.name} -> {'OUI' if is_joignable else ' NON'} (SMS: {sms_valid}, Appel: {call_valid})")

        return {"pid": pid, "status": "done"}

    except Exception as e:
        logger.exception(f" Erreur inattendue pour le prospect {pid}")
        return {"pid": pid, "status": "error", "message": str(e)}

    finally:
        db.close()


def process_full_pipeline_task(prospect_ids: List[int]):
    """Pipeline complet en arrière-plan (IA + SMS + Appel)"""
    logger.info(f" Lancement du pipeline complet pour {len(prospect_ids)} prospects...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_one, pid): pid for pid in prospect_ids}

        for future in as_completed(futures):
            pid = futures[future]
            try:
                result = future.result(timeout=120)  # Timeout plus long pour les appels
                logger.info(f"✅ Prospect {pid} terminé: {result.get('status')}")
            except Exception as e:
                logger.error(f" Prospect {pid} a échoué: {e}")

    logger.info(f"Pipeline complet terminé pour {len(prospect_ids)} prospects")

# ============ ROUTE : VÉRIFICATION PAR APPEL (SPÉCIFIQUE) ============
@router.post("/verify-call/{prospect_id}")
async def verify_prospect_by_call(
    prospect_id: int,
    db: Session = Depends(get_db)
):
    """
    Vérifie un prospect en lançant un appel vocal
    """
    repo = ProspectRepository(db)
    prospect = repo.get_by_id(prospect_id)
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")
    
    # Lancer l'appel
    result = phone_verifier.trigger_call(prospect.phone)
    
    # Mettre à jour le prospect
    repo.update(prospect_id, {
        'phone_validation': json.dumps(result)
    })
    
    return {
        "prospect_id": prospect_id,
        "prospect_name": prospect.name,
        "phone": prospect.phone,
        "call_sent": result.get("success", False),
        "message": result.get("message"),
        "checked_at": result.get("checked_at")
    }

# ============ ROUTE : VÉRIFICATION UNIFIÉE (SMS + APPEL) ============
@router.post("/verify/{prospect_id}")
async def verify_prospect(
    prospect_id: int,
    method: str = "sms",  # "sms" ou "call"
    db: Session = Depends(get_db)
):
    """
    Vérifie un prospect par SMS ou appel vocal
    - method: "sms" ou "call"
    """
    repo = ProspectRepository(db)
    prospect = repo.get_by_id(prospect_id)
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")
    
    if method == "sms":
        result = sms_service.send_ishowo_link(prospect.phone)
    elif method == "call":
        result = phone_verifier.trigger_call(prospect.phone)
    else:
        raise HTTPException(status_code=400, detail="Méthode invalide. Utilise 'sms' ou 'call'")
    
    repo.update(prospect_id, {
        'phone_validation': json.dumps(result)
    })
    
    return {
        "prospect_id": prospect_id,
        "prospect_name": prospect.name,
        "phone": prospect.phone,
        "method": method,
        "valid": result.get("valid", result.get("success", False)),
        "message": result.get("message"),
        "checked_at": result.get("checked_at")
    }

# ============ ROUTE 5: PROSPECTS (AFFICHAGE JSON) ============
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
    
    if min_score:
        prospects = repo.get_by_score_range(min_score, 10)
    else:
        prospects = repo.get_all(skip=0, limit=limit, sort_by_score=True)
    
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
    
    return {
        "total": len(results),
        "count": len(results),
        "prospects": results
    }

# ============ ROUTE : EXPORT PROSPECTS EXPLOITABLES ============
@router.get("/prospects/export/exploitable/csv")
async def export_exploitable_csv(db: Session = Depends(get_db)):
    """
    Télécharge uniquement les prospects exploitables au format CSV
    Critères : score > 5 ET joignables (phone_validation.valid = True)
    """
    import csv
    from io import StringIO
    from fastapi import Response
    
    repo = ProspectRepository(db)
    all_prospects = repo.get_all(skip=0, limit=10000, sort_by_score=True)
    
    # Filtrer les prospects exploitables
    exploitable = []
    for p in all_prospects:
        phone_validation = None
        if p.phone_validation:
            try:
                phone_validation = json.loads(p.phone_validation)
            except:
                pass
        
        # Critères : score > 5 ET joignable
        if p.score and p.score > 5 and phone_validation and phone_validation.get('valid', False):
            exploitable.append({
                "prospect": p,
                "validation": phone_validation
            })
    
    if not exploitable:
        # Retourner un CSV vide avec un message
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Message'])
        writer.writerow(['Aucun prospect exploitable trouvé'])
        csv_data = output.getvalue()
        output.close()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=aucun_exploitable.csv"
            }
        )
    
    # Créer le CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    writer.writerow([
        'ID', 'Nom', 'Téléphone', 'Secteur', 'Ville',
        'Adresse', 'Type Business', 'Score', 'Besoin Stock',
        'Joignable', 'Opérateur', 'Justification IA'
    ])
    
    # Données
    for item in exploitable:
        p = item["prospect"]
        validation = item["validation"]
        
        writer.writerow([
            p.id,
            p.name,
            p.phone,
            p.sector or '',
            p.city or '',
            p.address or '',
            p.business_type or '',
            p.score or 0,
            'Oui' if p.stock_management_need else 'Non',
            'Oui' if validation.get('valid') else 'Non',
            validation.get('carrier', '') or validation.get('sms', {}).get('carrier', ''),
            p.ai_justification or ''
        ])
    
    csv_data = output.getvalue()
    output.close()
    
    filename = f"prospects_exploitables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# ============ ROUTE 6: PROSPECTS (EXPORT JSON) ============
@router.get("/prospects/export/json")
async def export_prospects_json(db: Session = Depends(get_db)):
    """
    Télécharge tous les prospects au format JSON
    """
    repo = ProspectRepository(db)
    prospects = repo.get_all(skip=0, limit=10000, sort_by_score=True)
    
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

# ============ ROUTE 6*: PROSPECTS (EXPORT CSV) ============
@router.get("/prospects/export/csv")
async def export_prospects_csv(db: Session = Depends(get_db)):
    """
    Télécharge tous les prospects au format CSV
    """
    import csv
    from io import StringIO
    from fastapi import Response
    
    repo = ProspectRepository(db)
    prospects = repo.get_all(skip=0, limit=10000, sort_by_score=True)
    
    # Créer le CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    writer.writerow([
        'ID', 'Nom', 'Téléphone', 'Secteur', 'Ville',
        'Adresse', 'Type Business', 'Score', 'Besoin Stock',
        'Joignable', 'Opérateur', 'Justification IA'
    ])
    
    # Données
    for p in prospects:
        phone_validation = None
        if p.phone_validation:
            try:
                phone_validation = json.loads(p.phone_validation)
            except:
                pass
        
        writer.writerow([
            p.id,
            p.name,
            p.phone,
            p.sector or '',
            p.city or '',
            p.address or '',
            p.business_type or '',
            p.score or 0,
            'Oui' if p.stock_management_need else 'Non',
            'Oui' if (phone_validation and phone_validation.get('valid')) else 'Non',
            phone_validation.get('carrier', '') if phone_validation else '',
            p.ai_justification or ''
        ])
    
    csv_data = output.getvalue()
    output.close()
    
    filename = f"prospects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
# ============ ROUTE 7: STATS ============
@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Statistiques"""
    repo = ProspectRepository(db)
    stats = repo.get_stats()
    return stats


# ============ ROUTE 8: TEST INSERT ============
@router.post("/test/insert")
async def test_insert(db: Session = Depends(get_db)):
    """Route de test pour insérer un prospect manuellement"""
    from app.services.normaliseur import normalize
    
    try:
        repo = ProspectRepository(db)
        
        test = ProspectCreate(
            name="ENTREPRISE TEST",
            phone=normalize("+229 01 47 86 32 52"),
            sector="Test",
            city="Cotonou",
            description="Description test",
            source="test_manual"
        )
        
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


# ============ ROUTE 9: ROOT ============
@router.get("/")
async def root():
    """Page d'accueil"""
    return {
        "service": "ISHOWO - Prospection intelligente",
        "version": "1.0.0",
        "endpoints": {
            "collect": "POST /collect - Collecte des prospects",
            "process-full": "POST /process-full - Pipeline complet (IA + SMS)",
            "verify-all-sms": "POST /verify-all-sms - Envoi SMS à tous",
            "prospects": "GET /prospects - Liste des prospects",
            "prospects/export/json": "GET /prospects/export/json - Export JSON",
            "stats": "GET /stats - Statistiques",
            "test/insert": "POST /test/insert - Insertion de test"
        },
        "docs": "/docs"
    }
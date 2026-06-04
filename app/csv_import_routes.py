"""
CSV Import & Bulk Operations Routes
15 REST API endpoints for CSV imports, exports, bulk operations
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
from app.database import get_db
from app.csv_import_integration import (
    CSVValidator, CSVDeduplicator, CSVImportManager, CSVExporter,
    BulkOperationManager, ImportStatus, BulkOperationType, ImportResultStatus
)
from app.crm_models import ImportJob, ImportResult, BulkOperation, BulkOperationResult
from pydantic import BaseModel

router = APIRouter(prefix="/api/crm/imports", tags=["CSV Import & Bulk Operations"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class FileUploadRequest(BaseModel):
    """File upload request"""
    file_name: str
    file_size: int


class ImportValidationResponse(BaseModel):
    """Import validation response"""
    job_id: str
    is_valid: bool
    row_count: int
    errors: List[str]
    warnings: List[str]


class ImportExecuteRequest(BaseModel):
    """Import execution request"""
    handle_duplicates: str = "skip"  # skip, update, merge


class ImportJobResponse(BaseModel):
    """Import job response"""
    job_id: str
    file_name: str
    status: str
    row_count: int
    processed_count: int
    success_count: int
    duplicate_count: int
    error_count: int
    created_at: str
    completed_at: Optional[str]


class ImportResultResponse(BaseModel):
    """Individual import result"""
    row_index: int
    status: str
    customer_id: Optional[str]
    error_message: Optional[str]


class ExportRequest(BaseModel):
    """Export request"""
    filters: Optional[Dict[str, Any]] = None


class BulkUpdateRequest(BaseModel):
    """Bulk update request"""
    customer_ids: List[str]
    updates: Dict[str, Any]


class BulkDeleteRequest(BaseModel):
    """Bulk delete request"""
    customer_ids: List[str]
    reason: Optional[str] = None


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    operation_id: str
    operation_type: str
    status: str
    customer_count: int
    success_count: int
    error_count: int
    created_at: str


# ============================================================================
# IMPORT ENDPOINTS
# ============================================================================

@router.post("/upload", response_model=ImportJobResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload CSV file for import (creates pending job)"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be CSV format")
        
        # Read file
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Parse CSV
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # Create import job
        job = CSVImportManager.create_import_job(
            db=db,
            file_name=file.filename,
            file_size=len(contents),
            row_count=len(df),
            created_by="api_user"
        )
        
        return ImportJobResponse(
            job_id=job.id,
            file_name=job.file_name,
            status=job.status,
            row_count=job.row_count,
            processed_count=0,
            success_count=0,
            duplicate_count=0,
            error_count=0,
            created_at=job.created_at.isoformat(),
            completed_at=None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ImportJobResponse])
async def list_imports(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all import jobs with optional filtering"""
    query = db.query(ImportJob)
    
    if status:
        query = query.filter(ImportJob.status == status)
    
    jobs = query.order_by(ImportJob.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        ImportJobResponse(
            job_id=job.id,
            file_name=job.file_name,
            status=job.status,
            row_count=job.row_count,
            processed_count=job.processed_count,
            success_count=job.success_count,
            duplicate_count=job.duplicate_count,
            error_count=job.error_count,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None
        )
        for job in jobs
    ]


@router.get("/{job_id}", response_model=ImportJobResponse)
async def get_import_job(job_id: str, db: Session = Depends(get_db)):
    """Get import job details"""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    return ImportJobResponse(
        job_id=job.id,
        file_name=job.file_name,
        status=job.status,
        row_count=job.row_count,
        processed_count=job.processed_count,
        success_count=job.success_count,
        duplicate_count=job.duplicate_count,
        error_count=job.error_count,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )


@router.post("/{job_id}/validate", response_model=ImportValidationResponse)
async def validate_import(
    job_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Validate CSV structure and data (no import yet)"""
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")
        
        # Read file
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # Validate structure
        is_valid, struct_errors = CSVValidator.validate_csv_structure(df)
        
        # Validate rows
        row_errors = []
        csv_dups = CSVDeduplicator.check_csv_duplicates(df.to_dict('records'))
        
        if csv_dups:
            row_errors.append(f"Found {len(csv_dups)} duplicate records within CSV")
        
        for idx, row in df.iterrows():
            row_valid, errors = CSVValidator.validate_row(row.to_dict())
            if not row_valid:
                row_errors.extend([f"Row {idx}: {e}" for e in errors])
        
        # Update job status
        all_errors = struct_errors + row_errors
        CSVImportManager.update_job_status(
            db, job_id, ImportStatus.VALIDATED, all_errors
        )
        
        return ImportValidationResponse(
            job_id=job_id,
            is_valid=len(all_errors) == 0,
            row_count=len(df),
            errors=all_errors[:100],  # Limit to 100 errors
            warnings=[]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/execute", response_model=ImportJobResponse)
async def execute_import(
    job_id: str,
    request: ImportExecuteRequest,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Execute validated import in background"""
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")
        
        # Update status
        CSVImportManager.update_job_status(db, job_id, ImportStatus.PROCESSING)
        
        # Read file
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # Add background task for processing
        background_tasks.add_task(
            process_csv_import,
            job_id=job_id,
            rows=df.to_dict('records'),
            handle_duplicates=request.handle_duplicates
        )
        
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        return ImportJobResponse(
            job_id=job.id,
            file_name=job.file_name,
            status=job.status,
            row_count=job.row_count,
            processed_count=job.processed_count,
            success_count=job.success_count,
            duplicate_count=job.duplicate_count,
            error_count=job.error_count,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_csv_import(
    job_id: str,
    rows: List[Dict[str, Any]],
    handle_duplicates: str
):
    """Background task for CSV import processing"""
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        success = 0
        duplicate = 0
        error = 0
        
        for idx, row in enumerate(rows):
            status, customer_id, error_msg = CSVImportManager.process_csv_row(
                db, job_id, idx, row
            )
            
            if status == ImportResultStatus.DUPLICATE:
                duplicate += 1
                if handle_duplicates == "update":
                    status, customer_id, error_msg = CSVImportManager.process_csv_row(
                        db, job_id, idx, row, customer_id=customer_id
                    )
                    success += 1
            elif status == ImportResultStatus.SUCCESS:
                success += 1
            else:
                error += 1
            
            # Record result
            CSVImportManager.create_import_result(
                db, job_id, idx, status, customer_id, error_msg, row
            )
        
        # Update job
        job.processed_count = len(rows)
        job.success_count = success
        job.duplicate_count = duplicate
        job.error_count = error
        job.status = ImportStatus.COMPLETED.value
        job.completed_at = datetime.utcnow()
        db.commit()
    
    except Exception as e:
        job.status = ImportStatus.FAILED.value
        job.updated_at = datetime.utcnow()
        db.commit()
    
    finally:
        db.close()


@router.post("/{job_id}/cancel")
async def cancel_import(job_id: str, db: Session = Depends(get_db)):
    """Cancel in-progress import"""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    if job.status not in [ImportStatus.PENDING.value, ImportStatus.PROCESSING.value]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed import")
    
    CSVImportManager.update_job_status(db, job_id, ImportStatus.CANCELLED)
    
    return {"message": "Import cancelled", "job_id": job_id}


@router.get("/{job_id}/results", response_model=List[ImportResultResponse])
async def get_import_results(
    job_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get import results for job"""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    query = db.query(ImportResult).filter(ImportResult.job_id == job_id)
    
    if status:
        query = query.filter(ImportResult.status == status)
    
    results = query.order_by(ImportResult.row_index).offset(skip).limit(limit).all()
    
    return [
        ImportResultResponse(
            row_index=r.row_index,
            status=r.status,
            customer_id=r.customer_id,
            error_message=r.error_message
        )
        for r in results
    ]


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@router.post("/export")
async def export_customers(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """Export customers to CSV file"""
    try:
        csv_bytes, filename = CSVExporter.export_customers(db, request.filters)
        
        return {
            "filename": filename,
            "size_bytes": len(csv_bytes),
            "status": "ready",
            "data": csv_bytes.decode('utf-8')[:1000]  # Preview first 1000 chars
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BULK OPERATION ENDPOINTS
# ============================================================================

@router.post("/bulk-update", response_model=BulkOperationResponse)
async def bulk_update_properties(
    request: BulkUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Bulk update customer properties"""
    if not request.customer_ids:
        raise HTTPException(status_code=400, detail="customer_ids required")
    
    if len(request.customer_ids) > 10000:
        raise HTTPException(status_code=400, detail="Maximum 10000 customers per operation")
    
    operation = BulkOperationManager.create_bulk_operation(
        db,
        BulkOperationType.PROPERTY_UPDATE,
        request.customer_ids,
        request.updates,
        "api_user"
    )
    
    background_tasks.add_task(
        BulkOperationManager.execute_bulk_update,
        operation_id=operation.id,
        customer_ids=request.customer_ids,
        updates=request.updates
    )
    
    return BulkOperationResponse(
        operation_id=operation.id,
        operation_type=operation.operation_type,
        status=operation.status,
        customer_count=operation.customer_count,
        success_count=0,
        error_count=0,
        created_at=operation.created_at.isoformat()
    )


@router.post("/bulk-delete", response_model=BulkOperationResponse)
async def bulk_delete_customers(
    request: BulkDeleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Bulk delete (soft delete) customers"""
    if not request.customer_ids:
        raise HTTPException(status_code=400, detail="customer_ids required")
    
    if len(request.customer_ids) > 10000:
        raise HTTPException(status_code=400, detail="Maximum 10000 customers per operation")
    
    operation = BulkOperationManager.create_bulk_operation(
        db,
        BulkOperationType.DELETE,
        request.customer_ids,
        {"reason": request.reason},
        "api_user"
    )
    
    background_tasks.add_task(
        BulkOperationManager.execute_bulk_delete,
        operation_id=operation.id,
        customer_ids=request.customer_ids
    )
    
    return BulkOperationResponse(
        operation_id=operation.id,
        operation_type=operation.operation_type,
        status=operation.status,
        customer_count=operation.customer_count,
        success_count=0,
        error_count=0,
        created_at=operation.created_at.isoformat()
    )


@router.get("/bulk/{operation_id}", response_model=BulkOperationResponse)
async def get_bulk_operation(
    operation_id: str,
    db: Session = Depends(get_db)
):
    """Get bulk operation status"""
    operation = db.query(BulkOperation).filter(
        BulkOperation.id == operation_id
    ).first()
    
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    return BulkOperationResponse(
        operation_id=operation.id,
        operation_type=operation.operation_type,
        status=operation.status,
        customer_count=operation.customer_count,
        success_count=operation.success_count,
        error_count=operation.error_count,
        created_at=operation.created_at.isoformat()
    )


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/summary")
async def import_analytics_summary(db: Session = Depends(get_db)):
    """Get import analytics summary"""
    jobs = db.query(ImportJob).all()
    
    total_imported = sum(j.success_count for j in jobs)
    total_duplicates = sum(j.duplicate_count for j in jobs)
    total_errors = sum(j.error_count for j in jobs)
    
    return {
        "total_imports": len(jobs),
        "total_customers_imported": total_imported,
        "total_duplicates": total_duplicates,
        "total_errors": total_errors,
        "success_rate": (
            total_imported / (total_imported + total_duplicates + total_errors)
            if (total_imported + total_duplicates + total_errors) > 0
            else 0
        )
    }


@router.get("/analytics/by-date")
async def import_analytics_by_date(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get import analytics by date"""
    from datetime import timedelta
    
    jobs = db.query(ImportJob).filter(
        ImportJob.created_at >= datetime.utcnow() - timedelta(days=days)
    ).all()
    
    analytics = {}
    for job in jobs:
        date_key = job.created_at.date().isoformat()
        
        if date_key not in analytics:
            analytics[date_key] = {
                "imports": 0,
                "customers": 0,
                "duplicates": 0,
                "errors": 0
            }
        
        analytics[date_key]["imports"] += 1
        analytics[date_key]["customers"] += job.success_count
        analytics[date_key]["duplicates"] += job.duplicate_count
        analytics[date_key]["errors"] += job.error_count
    
    return analytics


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check for import service"""
    return {
        "status": "healthy",
        "service": "CSV Import & Bulk Operations",
        "timestamp": datetime.utcnow().isoformat()
    }

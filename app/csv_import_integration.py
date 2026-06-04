"""
CSV Import & Bulk Operations Integration
Handles CSV uploads, validation, deduplication, bulk operations
"""

import io
import csv
import json
import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.crm_models import (
    Customer, ImportJob, ImportResult, BulkOperation,
    BulkOperationResult
)


class ImportStatus(str, Enum):
    """Import job status"""
    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkOperationType(str, Enum):
    """Bulk operation types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PROPERTY_UPDATE = "property_update"


class ImportResultStatus(str, Enum):
    """Individual record import status"""
    SUCCESS = "success"
    DUPLICATE = "duplicate"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    SKIPPED = "skipped"


class CSVValidator:
    """Validates CSV structure and data"""
    
    REQUIRED_COLUMNS = {"email", "phone", "first_name", "last_name"}
    OPTIONAL_COLUMNS = {
        "company", "job_title", "address", "city", "state", 
        "country", "postal_code", "industry", "company_size"
    }
    ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
    
    @staticmethod
    def validate_csv_structure(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate CSV has required columns
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        missing_cols = CSVValidator.REQUIRED_COLUMNS - set(df.columns)
        
        if missing_cols:
            errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        
        invalid_cols = set(df.columns) - CSVValidator.ALL_COLUMNS
        if invalid_cols:
            errors.append(f"Unknown columns: {', '.join(invalid_cols)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate individual row data
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for col in CSVValidator.REQUIRED_COLUMNS:
            if not row.get(col) or str(row.get(col, "")).strip() == "":
                errors.append(f"Missing required field: {col}")
        
        # Validate email format
        email = str(row.get("email", "")).strip()
        if email and "@" not in email:
            errors.append(f"Invalid email format: {email}")
        
        # Validate phone (basic check)
        phone = str(row.get("phone", "")).strip()
        if phone and len(phone.replace("+", "").replace("-", "")) < 10:
            errors.append(f"Invalid phone format: {phone}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CSV row data"""
        normalized = {}
        
        for key, value in row.items():
            if pd.isna(value):
                normalized[key] = None
            else:
                value_str = str(value).strip()
                
                if key == "email":
                    normalized[key] = value_str.lower()
                elif key == "phone":
                    # E.164 normalization for Indian numbers
                    phone = value_str.replace(" ", "").replace("-", "")
                    if phone.isdigit() and len(phone) == 10:
                        normalized[key] = f"+91{phone}"
                    else:
                        normalized[key] = phone if not phone.startswith("+") else phone
                else:
                    normalized[key] = value_str if value_str else None
        
        return normalized


class CSVDeduplicator:
    """Deduplicates CSV records against CRM"""
    
    @staticmethod
    def find_matching_customer(
        db: Session,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[Customer]:
        """
        Find matching customer using multi-level matching
        Returns: Customer if found, None otherwise
        """
        # Level 1: Exact email match
        if email:
            customer = db.query(Customer).filter(
                Customer.email == email,
                Customer.deleted_at.is_(None)
            ).first()
            if customer:
                return customer
        
        # Level 2: Exact phone match
        if phone:
            customer = db.query(Customer).filter(
                Customer.phone == phone,
                Customer.deleted_at.is_(None)
            ).first()
            if customer:
                return customer
        
        # Level 3: Email + Phone match (either field)
        if email or phone:
            conditions = []
            if email:
                conditions.append(Customer.email == email)
            if phone:
                conditions.append(Customer.phone == phone)
            
            customer = db.query(Customer).filter(
                or_(*conditions),
                Customer.deleted_at.is_(None)
            ).first()
            if customer:
                return customer
        
        # Level 4: First name + Last name match
        if first_name and last_name:
            customer = db.query(Customer).filter(
                Customer.first_name == first_name,
                Customer.last_name == last_name,
                Customer.deleted_at.is_(None)
            ).first()
            if customer:
                return customer
        
        return None
    
    @staticmethod
    def check_csv_duplicates(rows: List[Dict[str, Any]]) -> Dict[int, List[int]]:
        """
        Check for duplicates within CSV itself
        Returns: {row_index: [duplicate_row_indexes]}
        """
        duplicates = {}
        seen = {}
        
        for idx, row in enumerate(rows):
            # Create composite key
            email = row.get("email", "").lower() if row.get("email") else None
            phone = row.get("phone") if row.get("phone") else None
            
            key = (email, phone)
            
            if key in seen:
                if idx not in duplicates:
                    duplicates[idx] = [seen[key]]
                else:
                    duplicates[idx].append(seen[key])
                
                # Also mark original
                if seen[key] not in duplicates:
                    duplicates[seen[key]] = [idx]
                else:
                    duplicates[seen[key]].append(idx)
            else:
                seen[key] = idx
        
        return duplicates


class CSVImportManager:
    """Manages CSV import jobs"""
    
    @staticmethod
    def create_import_job(
        db: Session,
        file_name: str,
        file_size: int,
        row_count: int,
        created_by: str
    ) -> ImportJob:
        """Create new import job"""
        job = ImportJob(
            id=str(uuid.uuid4()),
            file_name=file_name,
            file_size=file_size,
            row_count=row_count,
            status=ImportStatus.PENDING.value,
            validation_errors=[],
            processed_count=0,
            success_count=0,
            duplicate_count=0,
            error_count=0,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        return job
    
    @staticmethod
    def update_job_status(
        db: Session,
        job_id: str,
        status: ImportStatus,
        validation_errors: Optional[List[str]] = None
    ) -> ImportJob:
        """Update import job status"""
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = status.value
        if validation_errors is not None:
            job.validation_errors = validation_errors
        job.updated_at = datetime.utcnow()
        
        db.commit()
        return job
    
    @staticmethod
    def process_csv_row(
        db: Session,
        job_id: str,
        row_index: int,
        row_data: Dict[str, Any],
        customer_id: Optional[str] = None
    ) -> Tuple[ImportResultStatus, Optional[str], Optional[str]]:
        """
        Process single CSV row
        Returns: (status, customer_id, error_message)
        """
        # Normalize data
        normalized = CSVValidator.normalize_row(row_data)
        
        # Validate row
        is_valid, errors = CSVValidator.validate_row(normalized)
        if not is_valid:
            return ImportResultStatus.VALIDATION_ERROR, None, "; ".join(errors)
        
        try:
            # Check for existing customer
            existing = CSVDeduplicator.find_matching_customer(
                db,
                email=normalized.get("email"),
                phone=normalized.get("phone"),
                first_name=normalized.get("first_name"),
                last_name=normalized.get("last_name")
            )
            
            if existing and not customer_id:
                # Duplicate found
                return ImportResultStatus.DUPLICATE, existing.id, None
            
            if customer_id:
                # Update existing customer
                customer = db.query(Customer).filter(
                    Customer.id == customer_id
                ).first()
                if not customer:
                    return ImportResultStatus.PROCESSING_ERROR, None, "Customer not found"
                
                # Update fields
                customer.email = normalized.get("email") or customer.email
                customer.phone = normalized.get("phone") or customer.phone
                customer.first_name = normalized.get("first_name") or customer.first_name
                customer.last_name = normalized.get("last_name") or customer.last_name
                customer.company = normalized.get("company") or customer.company
                customer.job_title = normalized.get("job_title") or customer.job_title
                customer.updated_at = datetime.utcnow()
                
                db.commit()
                return ImportResultStatus.SUCCESS, customer.id, None
            else:
                # Create new customer
                customer = Customer(
                    id=str(uuid.uuid4()),
                    email=normalized.get("email"),
                    phone=normalized.get("phone"),
                    first_name=normalized.get("first_name"),
                    last_name=normalized.get("last_name"),
                    company=normalized.get("company"),
                    job_title=normalized.get("job_title"),
                    address=normalized.get("address"),
                    city=normalized.get("city"),
                    state=normalized.get("state"),
                    country=normalized.get("country"),
                    postal_code=normalized.get("postal_code"),
                    source="csv_import",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(customer)
                db.commit()
                return ImportResultStatus.SUCCESS, customer.id, None
        
        except Exception as e:
            return ImportResultStatus.PROCESSING_ERROR, None, str(e)
    
    @staticmethod
    def create_import_result(
        db: Session,
        job_id: str,
        row_index: int,
        status: ImportResultStatus,
        customer_id: Optional[str] = None,
        error_message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> ImportResult:
        """Create import result record"""
        result = ImportResult(
            id=str(uuid.uuid4()),
            job_id=job_id,
            row_index=row_index,
            status=status.value,
            customer_id=customer_id,
            error_message=error_message,
            data=data or {},
            created_at=datetime.utcnow()
        )
        db.add(result)
        db.commit()
        return result
    
    @staticmethod
    def get_job_analytics(db: Session, job_id: str) -> Dict[str, Any]:
        """Get analytics for import job"""
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        results = db.query(ImportResult).filter(
            ImportResult.job_id == job_id
        ).all()
        
        status_counts = {}
        for result in results:
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "job_id": job_id,
            "file_name": job.file_name,
            "total_rows": job.row_count,
            "processed_count": job.processed_count,
            "success_count": job.success_count,
            "duplicate_count": job.duplicate_count,
            "error_count": job.error_count,
            "status_breakdown": status_counts,
            "duration_seconds": int((job.updated_at - job.created_at).total_seconds()),
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }


class CSVExporter:
    """Exports customer data to CSV"""
    
    @staticmethod
    def export_customers(
        db: Session,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        """
        Export customers to CSV
        Returns: (csv_bytes, filename)
        """
        query = db.query(Customer).filter(Customer.deleted_at.is_(None))
        
        # Apply filters
        if filters:
            if filters.get("source"):
                query = query.filter(Customer.source == filters["source"])
            if filters.get("created_after"):
                query = query.filter(Customer.created_at >= filters["created_after"])
        
        customers = query.all()
        
        # Create CSV in memory
        output = io.StringIO()
        fieldnames = [
            "customer_id", "email", "phone", "first_name", "last_name",
            "company", "job_title", "address", "city", "state", 
            "country", "postal_code", "source", "created_at"
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for customer in customers:
            writer.writerow({
                "customer_id": customer.id,
                "email": customer.email,
                "phone": customer.phone,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "company": customer.company,
                "job_title": customer.job_title,
                "address": customer.address,
                "city": customer.city,
                "state": customer.state,
                "country": customer.country,
                "postal_code": customer.postal_code,
                "source": customer.source,
                "created_at": customer.created_at.isoformat() if customer.created_at else ""
            })
        
        csv_bytes = output.getvalue().encode('utf-8')
        filename = f"customers_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return csv_bytes, filename


class BulkOperationManager:
    """Manages bulk operations (update, delete)"""
    
    @staticmethod
    def create_bulk_operation(
        db: Session,
        operation_type: BulkOperationType,
        customer_ids: List[str],
        operation_data: Dict[str, Any],
        created_by: str
    ) -> BulkOperation:
        """Create new bulk operation"""
        operation = BulkOperation(
            id=str(uuid.uuid4()),
            operation_type=operation_type.value,
            customer_count=len(customer_ids),
            operation_data=operation_data,
            status="pending",
            success_count=0,
            error_count=0,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(operation)
        db.commit()
        
        # Store customer IDs in operation data for processing
        operation.customer_ids_list = customer_ids
        return operation
    
    @staticmethod
    def execute_bulk_update(
        db: Session,
        operation_id: str,
        customer_ids: List[str],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute bulk property update"""
        operation = db.query(BulkOperation).filter(
            BulkOperation.id == operation_id
        ).first()
        
        if not operation:
            raise ValueError(f"Operation {operation_id} not found")
        
        operation.status = "processing"
        operation.updated_at = datetime.utcnow()
        db.commit()
        
        success_count = 0
        error_count = 0
        
        for customer_id in customer_ids:
            try:
                customer = db.query(Customer).filter(
                    Customer.id == customer_id,
                    Customer.deleted_at.is_(None)
                ).first()
                
                if not customer:
                    error_count += 1
                    BulkOperationManager.create_result(
                        db, operation_id, customer_id, "error", "Customer not found"
                    )
                    continue
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(customer, key):
                        setattr(customer, key, value)
                
                customer.updated_at = datetime.utcnow()
                db.commit()
                success_count += 1
                BulkOperationManager.create_result(
                    db, operation_id, customer_id, "success"
                )
            
            except Exception as e:
                error_count += 1
                BulkOperationManager.create_result(
                    db, operation_id, customer_id, "error", str(e)
                )
        
        operation.status = "completed"
        operation.success_count = success_count
        operation.error_count = error_count
        operation.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "operation_id": operation_id,
            "success_count": success_count,
            "error_count": error_count,
            "total": len(customer_ids)
        }
    
    @staticmethod
    def execute_bulk_delete(
        db: Session,
        operation_id: str,
        customer_ids: List[str]
    ) -> Dict[str, Any]:
        """Execute bulk soft delete"""
        operation = db.query(BulkOperation).filter(
            BulkOperation.id == operation_id
        ).first()
        
        if not operation:
            raise ValueError(f"Operation {operation_id} not found")
        
        operation.status = "processing"
        db.commit()
        
        success_count = 0
        error_count = 0
        
        for customer_id in customer_ids:
            try:
                customer = db.query(Customer).filter(
                    Customer.id == customer_id
                ).first()
                
                if not customer:
                    error_count += 1
                    continue
                
                # Soft delete
                customer.deleted_at = datetime.utcnow()
                db.commit()
                success_count += 1
                BulkOperationManager.create_result(
                    db, operation_id, customer_id, "success"
                )
            
            except Exception as e:
                error_count += 1
                BulkOperationManager.create_result(
                    db, operation_id, customer_id, "error", str(e)
                )
        
        operation.status = "completed"
        operation.success_count = success_count
        operation.error_count = error_count
        operation.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "operation_id": operation_id,
            "success_count": success_count,
            "error_count": error_count,
            "total": len(customer_ids)
        }
    
    @staticmethod
    def create_result(
        db: Session,
        operation_id: str,
        customer_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> BulkOperationResult:
        """Create bulk operation result"""
        result = BulkOperationResult(
            id=str(uuid.uuid4()),
            operation_id=operation_id,
            customer_id=customer_id,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow()
        )
        db.add(result)
        db.commit()
        return result

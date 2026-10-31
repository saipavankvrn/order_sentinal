import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.order import AuditLog
from backend.app.core.logging import logger


class AuditService:
    """Application-level append-only audit logging service.
    Audit records cannot be modified or deleted through the application's exposed API.
    """

    @staticmethod
    def log_event(
        db: Session,
        correlation_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str,
        summary: str,
        order_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        metadata_str = json.dumps(metadata) if metadata else None
        log_entry = AuditLog(
            correlation_id=correlation_id,
            order_id=order_id,
            incident_id=incident_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            summary=summary,
            metadata_json=metadata_str
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(f"AUDIT [{event_type}] | Order: {order_id} | Actor: {actor_type}:{actor_id} | {summary}")
        return log_entry

    @staticmethod
    def get_logs(
        db: Session,
        order_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        limit: int = 50,
        page: int = 1
    ) -> List[AuditLog]:
        query = db.query(AuditLog)
        if order_id:
            query = query.filter(AuditLog.order_id == order_id)
        if incident_id:
            query = query.filter(AuditLog.incident_id == incident_id)
        if actor_type:
            query = query.filter(AuditLog.actor_type == actor_type)

        offset = (page - 1) * limit
        return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()


audit_service = AuditService()


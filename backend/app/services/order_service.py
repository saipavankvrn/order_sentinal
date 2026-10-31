import uuid
import threading
from typing import Optional, Tuple, List, Dict
from sqlalchemy.orm import Session
from backend.app.models.order import Order, OrderEvent, Incident
from backend.app.schemas.order import OrderCreate, OrderJourneyResponse, JourneyStageSummary, OrderEventResponse
from backend.app.services.simulator import simulator
from backend.app.services.detector import detector
from backend.app.services.audit_service import audit_service
from backend.app.core.logging import logger


class OrderService:
    """Manages order creation, journey orchestration, and stage progression."""

    _continuation_locks: Dict[str, threading.Lock] = {}
    _continuation_locks_guard = threading.Lock()

    @classmethod
    def _get_order_lock(cls, order_id: str) -> threading.Lock:
        with cls._continuation_locks_guard:
            if order_id not in cls._continuation_locks:
                cls._continuation_locks[order_id] = threading.Lock()
            return cls._continuation_locks[order_id]

    @staticmethod
    def create_order(
        db: Session,
        order_in: OrderCreate,
        custom_order_id: Optional[str] = None,
        is_demo_order: Optional[bool] = None,
        demo_session_id: Optional[str] = None
    ) -> Order:
        if custom_order_id and custom_order_id.strip():
            existing = db.query(Order).filter_by(order_id=custom_order_id.strip()).first()
            if existing:
                order_id = f"{custom_order_id.strip()}-{uuid.uuid4().hex[:4].upper()}"
            else:
                order_id = custom_order_id.strip()
        else:
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        correlation_id = f"corr-{uuid.uuid4().hex}"
        is_demo = is_demo_order if is_demo_order is not None else bool(getattr(order_in, "is_demo_order", False))
        session_id = demo_session_id or getattr(order_in, "demo_session_id", None)
        customer_id = f"CUST-DEMO-{uuid.uuid4().hex[:6].upper()}" if is_demo else f"CUST-{uuid.uuid4().hex[:6].upper()}"

        order = Order(
            order_id=order_id,
            correlation_id=correlation_id,
            customer_id=customer_id,
            customer_name=order_in.customer_name,
            customer_email=order_in.customer_email,
            product_sku=order_in.product_sku,
            product_name=order_in.product_name,
            order_amount=order_in.order_amount,
            currency=order_in.currency,
            current_stage="CUSTOMER_ORDER",
            order_status="PENDING",
            payment_status="PENDING",
            inventory_status="PENDING",
            fulfilment_status="PENDING",
            is_demo_order=is_demo,
            demo_session_id=session_id
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        audit_service.log_event(
            db=db,
            correlation_id=correlation_id,
            order_id=order_id,
            event_type="ORDER_CREATED",
            actor_type="SYSTEM",
            actor_id="ORDER_SERVICE",
            summary=f"Synthetic order created for {order_in.customer_name} ({order_in.product_name}).",
            metadata={"amount": order_in.order_amount, "sku": order_in.product_sku}
        )

        return order

    @classmethod
    def execute_journey(
        cls,
        db: Session,
        order: Order,
        inject_inventory_503: bool = False,
        inject_fulfilment_delay: bool = False,
        inject_inventory_422: bool = False
    ) -> Tuple[Order, Optional[Incident]]:
        """Executes the 7-stage order journey. Stops if an intermediate failure occurs."""
        logger.info(f"Initiating order journey for {order.order_id} (inject_503={inject_inventory_503}, inject_delay={inject_fulfilment_delay}, inject_422={inject_inventory_422})")

        # Stage 1: Customer Order Ingestion
        order.order_status = "PROCESSING"
        order.current_stage = "CUSTOMER_ORDER"
        s1_status, s1_dur, s1_event_stat, s1_err, s1_msg = simulator.process_customer_order(
            order.order_id, {"sku": order.product_sku}
        )
        cls._record_event(db, order, "CUSTOMER_ORDER", "order_service", "/v1/orders/ingest", s1_status, s1_dur, s1_event_stat, s1_err, s1_msg)

        # Stage 2: Address Validation
        order.current_stage = "ADDRESS_VALIDATION"
        s2_status, s2_dur, s2_event_stat, s2_err, s2_msg = simulator.validate_address(
            order.order_id, {"customer": order.customer_name}
        )
        cls._record_event(db, order, "ADDRESS_VALIDATION", "address_service", "/v1/address/validate", s2_status, s2_dur, s2_event_stat, s2_err, s2_msg)

        # Stage 3: Payment Processing
        order.current_stage = "PAYMENT"
        payment_idemp = f"pay_{order.order_id}"
        s3_status, s3_dur, s3_event_stat, s3_err, s3_msg = simulator.capture_payment(
            order.order_id, float(order.order_amount), payment_idemp
        )
        cls._record_event(db, order, "PAYMENT", "payment_service", "/v1/payments/capture", s3_status, s3_dur, s3_event_stat, s3_err, s3_msg)
        if s3_status == 200:
            order.payment_status = "CAPTURED"

        # Stage 4: Inventory Reservation
        order.current_stage = "INVENTORY"
        if inject_inventory_503:
            simulator.inject_fault(order.order_id, "HTTP_503")
        elif inject_inventory_422:
            simulator.inject_fault(order.order_id, "HTTP_422")

        s4_status, s4_dur, s4_event_stat, s4_err, s4_msg = simulator.reserve_inventory(
            order.order_id, order.product_sku
        )
        event_inv = cls._record_event(
            db, order, "INVENTORY", "inventory_service", "/v1/inventory/reserve",
            s4_status, s4_dur, s4_event_stat, s4_err, s4_msg
        )

        # Evaluate failure at Inventory stage
        if s4_status == 503:
            # Failure detected! Order remains in PROCESSING (stage blocked pending resolution)
            order.inventory_status = "PENDING"
            db.commit()

            incident = detector.process_telemetry_event(db, order, event_inv)
            return order, incident

        if s4_status == 422:
            # Permanent business rejection! Order remains in PROCESSING (stage blocked pending HITL decision)
            order.inventory_status = "REJECTED"
            db.commit()

            incident = detector.process_telemetry_event(db, order, event_inv)
            return order, incident

        # If inventory succeeded normally, continue
        order.inventory_status = "RESERVED"
        db.commit()

        # If fulfilment delay requested (Scenario 2), inject latency and evaluate SLA breach
        if inject_fulfilment_delay:
            order.current_stage = "FULFILMENT"
            s5_status, s5_dur, s5_event_stat, s5_err, s5_msg = simulator.allocate_fulfilment(order.order_id, force_delay=True)
            event_fulfilment = cls._record_event(
                db, order, "FULFILMENT", "fulfilment_service", "/v1/fulfilment/allocate",
                s5_status, s5_dur, s5_event_stat, s5_err, s5_msg
            )
            # Evaluate SLA breach via detector engine
            incident = detector.process_telemetry_event(db, order, event_fulfilment)
            return order, incident

        cls.resume_remaining_stages(db, order)
        return order, None

    @classmethod
    def resume_remaining_stages(cls, db: Session, order: Order):
        """Resumes remaining stages after successful recovery (handles recovery at INVENTORY or FULFILMENT)."""
        # Exact-once execution guard: skip if already completed
        if order.order_status == "COMPLETED" or order.current_stage == "NOTIFICATION":
            logger.info(f"Order {order.order_id} journey already completed. Skipping remaining stages.")
            return

        # Case A: If at INVENTORY (Scenario 1 post-recovery or clean run continuation)
        if order.current_stage == "INVENTORY":
            rows = db.query(Order).filter(
                Order.order_id == order.order_id,
                Order.order_status == "PROCESSING",
                Order.inventory_status == "RESERVED",
                Order.current_stage == "INVENTORY"
            ).update({"current_stage": "FULFILMENT"})
            db.commit()

            if rows == 0:
                logger.info(f"Continuation race detected for order {order.order_id}: already claimed. Skipping.")
                return

            db.refresh(order)
            logger.info(f"Resuming Stage 5 (FULFILMENT) for order {order.order_id}")

            s5_status, s5_dur, s5_event_stat, s5_err, s5_msg = simulator.allocate_fulfilment(order.order_id)
            cls._record_event(db, order, "FULFILMENT", "fulfilment_service", "/v1/fulfilment/allocate", s5_status, s5_dur, s5_event_stat, s5_err, s5_msg)
            if s5_status != 200:
                order.fulfilment_status = "FAILED"
                order.order_status = "PROCESSING"
                db.commit()
                logger.error(f"Stage 5 (FULFILMENT) failed for order {order.order_id}: {s5_msg}")
                return
            order.fulfilment_status = "ALLOCATED"
            db.commit()

        # Case B: If at FULFILMENT (Scenario 2 post-expedite continuation or Case A continuation)
        if order.current_stage == "FULFILMENT":
            rows = db.query(Order).filter(
                Order.order_id == order.order_id,
                Order.order_status == "PROCESSING",
                Order.current_stage == "FULFILMENT"
            ).update({"current_stage": "DELIVERY"})
            db.commit()

            if rows == 0:
                logger.info(f"Delivery continuation already claimed for order {order.order_id}. Skipping.")
                return

            db.refresh(order)
            logger.info(f"Resuming Stage 6 (DELIVERY) for order {order.order_id}")

            s6_status, s6_dur, s6_event_stat, s6_err, s6_msg = simulator.dispatch_logistics(order.order_id)
            cls._record_event(db, order, "DELIVERY", "logistics_service", "/v1/logistics/dispatch", s6_status, s6_dur, s6_event_stat, s6_err, s6_msg)
            if s6_status != 200:
                order.fulfilment_status = "FAILED"
                order.order_status = "PROCESSING"
                db.commit()
                logger.error(f"Stage 6 (DELIVERY) failed for order {order.order_id}: {s6_msg}")
                return
            order.fulfilment_status = "DELIVERED"
            db.commit()

        # Case C: Stage 7 (NOTIFICATION)
        if order.current_stage == "DELIVERY":
            rows = db.query(Order).filter(
                Order.order_id == order.order_id,
                Order.order_status == "PROCESSING",
                Order.current_stage == "DELIVERY"
            ).update({"current_stage": "NOTIFICATION"})
            db.commit()

            if rows == 0:
                logger.info(f"Notification continuation already claimed for order {order.order_id}. Skipping.")
                return

            db.refresh(order)
            logger.info(f"Resuming Stage 7 (NOTIFICATION) for order {order.order_id}")

            s7_status, s7_dur, s7_event_stat, s7_err, s7_msg = simulator.send_notification(order.order_id)
            cls._record_event(db, order, "NOTIFICATION", "notification_service", "/v1/notifications/send", s7_status, s7_dur, s7_event_stat, s7_err, s7_msg)
            if s7_status != 200:
                order.order_status = "PROCESSING"
                db.commit()
                logger.error(f"Stage 7 (NOTIFICATION) failed for order {order.order_id}: {s7_msg}")
                return

            # All 7 stages completed!
            order.order_status = "COMPLETED"
            db.commit()

            audit_service.log_event(
                db=db,
                correlation_id=order.correlation_id,
                order_id=order.order_id,
                event_type="ORDER_COMPLETED",
                actor_type="SYSTEM",
                actor_id="ORDER_SERVICE",
                summary="All seven journey stages completed successfully. Order marked COMPLETED.",
                metadata={"final_stage": "NOTIFICATION", "status": "COMPLETED"}
            )

    @classmethod
    def resume_remaining_stages_background(cls, order_id: str):
        """Background task handler for post-resolution journey continuation with thread-safety."""
        from backend.app.db.session import SessionLocal

        # Acquire per-order execution lock to serialize concurrent background tasks
        order_lock = cls._get_order_lock(order_id)
        with order_lock:
            db = SessionLocal()
            try:
                order = db.query(Order).filter_by(order_id=order_id).first()
                if order:
                    cls.resume_remaining_stages(db, order)
            except Exception as e:
                logger.error(f"Error during background continuation for order {order_id}: {e}")
            finally:
                db.close()

    @staticmethod
    def _record_event(
        db: Session,
        order: Order,
        stage: str,
        service: str,
        endpoint: str,
        status: int,
        duration: int,
        event_stat: str,
        err_code: str = "",
        err_msg: str = ""
    ) -> OrderEvent:
        event = OrderEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            order_id=order.order_id,
            correlation_id=order.correlation_id,
            stage=stage,
            service_name=service,
            endpoint=endpoint,
            http_method="POST",
            http_status=status,
            duration_ms=duration,
            event_status=event_stat,
            payload_summary=f"Request to {endpoint}",
            error_code=err_code if err_code else None,
            error_message=err_msg if err_msg else None
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_order_journey(db: Session, order_id: str) -> Optional[OrderJourneyResponse]:
        order = db.query(Order).filter_by(order_id=order_id).first()
        if not order:
            return None

        # Build chronological stage summaries
        stages_summary = []
        stage_names = [
            "CUSTOMER_ORDER",
            "ADDRESS_VALIDATION",
            "PAYMENT",
            "INVENTORY",
            "FULFILMENT",
            "DELIVERY",
            "NOTIFICATION"
        ]

        events_by_stage = {}
        for ev in order.events:
            if ev.stage not in events_by_stage:
                events_by_stage[ev.stage] = []
            events_by_stage[ev.stage].append(ev)

        for st in stage_names:
            evs = events_by_stage.get(st, [])
            if evs:
                latest = evs[-1]
                stages_summary.append(
                    JourneyStageSummary(
                        stage_name=st,
                        status=latest.event_status,
                        duration_ms=latest.duration_ms,
                        http_status=latest.http_status,
                        timestamp=latest.timestamp,
                        error_message=latest.error_message
                    )
                )

        raw_events = [OrderEventResponse.model_validate(e) for e in order.events]

        return OrderJourneyResponse(
            order_id=order.order_id,
            correlation_id=order.correlation_id,
            current_stage=order.current_stage,
            order_status=order.order_status,
            stages=stages_summary,
            raw_events=raw_events
        )


order_service = OrderService()

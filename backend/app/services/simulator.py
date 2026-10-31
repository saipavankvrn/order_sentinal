import json
import time
from typing import Dict, Any, Tuple, Optional
from backend.app.core.logging import logger


class DownstreamServiceSimulator:
    """Simulates multi-hop microservices across the 7-stage order journey."""

    def __init__(self):
        # In-memory domain state stores to verify state mutations
        self._inventory_reservations: Dict[str, Dict[str, Any]] = {}
        self._payment_captures: Dict[str, Dict[str, Any]] = {}
        self._fulfilment_allocations: Dict[str, Dict[str, Any]] = {}
        self._injected_faults: Dict[str, str] = {}  # order_id -> fault_type (e.g. "HTTP_503", "SLA_DELAY")
        self._fault_attempt_counts: Dict[str, int] = {}

    def inject_fault(self, order_id: str, fault_type: str):
        """Injects a specific simulated failure for an order."""
        self._injected_faults[order_id] = fault_type
        self._fault_attempt_counts[order_id] = 0

    def clear_fault(self, order_id: str):
        self._injected_faults.pop(order_id, None)
        self._fault_attempt_counts.pop(order_id, None)

    # -------------------------------------------------------------------------
    # Stage 1: Customer Order Ingestion (order_service)
    # -------------------------------------------------------------------------
    def process_customer_order(self, order_id: str, payload: dict) -> Tuple[int, int, str, str, str]:
        """Returns: http_status, duration_ms, event_status, error_code, error_message"""
        duration_ms = 45
        return 200, duration_ms, "SUCCESS", "", ""

    # -------------------------------------------------------------------------
    # Stage 2: Address Validation (address_service)
    # -------------------------------------------------------------------------
    def validate_address(self, order_id: str, payload: dict) -> Tuple[int, int, str, str, str]:
        duration_ms = 112
        return 200, duration_ms, "SUCCESS", "", ""

    # -------------------------------------------------------------------------
    # Stage 3: Payment Processing (payment_service) - With Idempotency Guard
    # -------------------------------------------------------------------------
    def capture_payment(self, order_id: str, amount: float, idempotency_key: str) -> Tuple[int, int, str, str, str]:
        duration_ms = 420
        # Guard: Never blindly re-charge or duplicate payment capture
        if order_id in self._payment_captures:
            logger.info(f"Payment already captured for order {order_id}. Idempotency honored.")
            return 200, 50, "SUCCESS", "", ""

        self._payment_captures[order_id] = {
            "amount": amount,
            "idempotency_key": idempotency_key,
            "captured_at": time.time(),
            "status": "CAPTURED"
        }
        return 200, duration_ms, "SUCCESS", "", ""

    # -------------------------------------------------------------------------
    # Stage 4: Inventory Reservation (inventory_service)
    # -------------------------------------------------------------------------
    def reserve_inventory(
        self,
        order_id: str,
        sku: str,
        quantity: int = 1,
        is_retry: bool = False,
        force_fail: bool = False
    ) -> Tuple[int, int, str, str, str]:
        duration_ms = 350

        # Check for injected fault
        fault = self._injected_faults.get(order_id)
        if fault in ["HTTP_422", "OUT_OF_STOCK"]:
            # Hard business rejection: physical inventory depleted
            logger.warning(f"Simulating HTTP 422 Out-of-Stock rejection at inventory_service for order {order_id} (SKU: {sku})")
            return (
                422,
                duration_ms,
                "FAILED",
                "OUT_OF_STOCK",
                f"Product SKU '{sku}' is out of stock at designated primary warehouse hub."
            )

        if fault == "HTTP_503":
            # If force_fail is requested or if it's the initial call (not retry)
            attempts = self._fault_attempt_counts.get(order_id, 0)
            if not is_retry or force_fail:
                self._fault_attempt_counts[order_id] = attempts + 1
                logger.warning(f"Simulating HTTP 503 Service Unavailable at inventory_service for order {order_id}")
                return (
                    503,
                    duration_ms,
                    "FAILED",
                    "HTTP_503_SERVICE_UNAVAILABLE",
                    "Inventory replica connection pool exhausted; downstream service unavailable."
                )
            else:
                # Retry call clears the transient fault and succeeds
                logger.info(f"Retry attempt succeeded on inventory_service for order {order_id}")
                self.clear_fault(order_id)

        # Successful reservation - write to downstream inventory store
        self._inventory_reservations[order_id] = {
            "sku": sku,
            "quantity": quantity,
            "reservation_id": f"RES-{order_id}",
            "reserved_at": time.time(),
            "status": "CONFIRMED"
        }
        return 200, duration_ms, "SUCCESS", "", ""

    @staticmethod
    def validate_substitution_parameters(
        substitute_sku: str,
        alternate_hub: str,
        original_sku: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Validates operator substitution parameters before adapter execution."""
        if not substitute_sku or not isinstance(substitute_sku, str) or not substitute_sku.strip():
            return False, "Invalid substitute SKU: Field is required and cannot be empty."

        sku_clean = substitute_sku.strip()
        if not sku_clean.startswith("SKU-"):
            return False, f"Invalid substitute SKU '{sku_clean}': Must be a valid SKU identifier starting with 'SKU-'."

        if original_sku and sku_clean == original_sku:
            return False, f"Invalid substitute SKU '{sku_clean}': Cannot substitute with the identical depleted SKU."

        if not alternate_hub or not isinstance(alternate_hub, str) or not alternate_hub.strip():
            return False, "Invalid alternate warehouse hub: Field is required and cannot be empty."

        hub_clean = alternate_hub.strip()
        if not hub_clean.startswith("HUB-"):
            return False, f"Invalid alternate warehouse hub '{hub_clean}': Must be a valid warehouse identifier starting with 'HUB-'."

        return True, "Parameters validated successfully."

    def execute_substitution(
        self,
        order_id: str,
        substitute_sku: str,
        alternate_hub: str,
        quantity: int = 1,
        force_fail: bool = False
    ) -> Tuple[int, int, str, str, str]:
        """Executes operator-approved SKU substitution and alternate hub stock reservation."""
        duration_ms = 320

        if force_fail:
            logger.error(f"Simulating downstream substitution failure for order {order_id}")
            return (
                500,
                duration_ms,
                "FAILED",
                "SUBSTITUTION_EXECUTION_FAILED",
                "Downstream inventory service failed to reallocate stock at alternate hub."
            )

        # Clear fault for order
        self.clear_fault(order_id)

        # Write to downstream inventory reservations domain store
        self._inventory_reservations[order_id] = {
            "sku": substitute_sku,
            "hub": alternate_hub,
            "quantity": quantity,
            "reservation_id": f"RES-{order_id}-SUB",
            "reserved_at": time.time(),
            "status": "CONFIRMED"
        }
        logger.info(f"Inventory substitution executed for order {order_id}: SKU {substitute_sku} reserved at {alternate_hub}")
        return 200, duration_ms, "SUCCESS", "", ""

    def verify_inventory_state(self, order_id: str) -> Tuple[bool, str]:
        """Downstream state verification probe. Does not trust HTTP 200 alone."""
        reservation = self._inventory_reservations.get(order_id)
        if reservation and reservation.get("status") == "CONFIRMED":
            hub_info = f" at warehouse {reservation['hub']}" if "hub" in reservation else ""
            details = (
                f"Verified: Reservation {reservation['reservation_id']} confirmed in inventory domain. "
                f"SKU {reservation['sku']} successfully reserved{hub_info}."
            )
            return True, details
        return False, "Verification failed: No confirmed reservation found in inventory service domain."

    # -------------------------------------------------------------------------
    # Stage 5: Warehouse Fulfilment (fulfilment_service)
    # -------------------------------------------------------------------------
    def allocate_fulfilment(
        self,
        order_id: str,
        force_delay: bool = False
    ) -> Tuple[int, int, str, str, str]:
        # Check for injected SLA delay fault (10,000ms latency vs 5,000ms demo SLA threshold)
        is_delayed = force_delay or (self._injected_faults.get(order_id) == "SLA_DELAY")

        if is_delayed:
            duration_ms = 10000
            logger.warning(f"Simulating excessive fulfilment latency (10000ms) on fulfilment_service for order {order_id}")
            self._fulfilment_allocations[order_id] = {
                "order_id": order_id,
                "status": "QUEUED",
                "priority": "STANDARD",
                "allocated_at": time.time(),
                "duration_ms": duration_ms
            }
            return 200, duration_ms, "SUCCESS", "", ""

        # Normal execution
        duration_ms = 180
        self._fulfilment_allocations[order_id] = {
            "order_id": order_id,
            "status": "ALLOCATED",
            "priority": "STANDARD",
            "allocated_at": time.time(),
            "duration_ms": duration_ms
        }
        return 200, duration_ms, "SUCCESS", "", ""

    def expedite_fulfilment(
        self,
        order_id: str,
        force_fail: bool = False
    ) -> Tuple[int, int, str, str, str]:
        """Executes priority queue elevation for a delayed fulfilment stage."""
        duration_ms = 150
        if force_fail:
            logger.warning(f"Simulating failed expedite dispatch for order {order_id}")
            return (
                500,
                duration_ms,
                "FAILED",
                "EXPEDITE_FAILED",
                "Downstream fulfilment gateway rejected priority elevation."
            )

        current = self._fulfilment_allocations.get(order_id, {})
        self._fulfilment_allocations[order_id] = {
            "order_id": order_id,
            "status": "ALLOCATED",
            "priority": "EXPEDITED",
            "allocated_at": current.get("allocated_at", time.time()),
            "expedited_at": time.time(),
            "duration_ms": duration_ms
        }
        self.clear_fault(order_id)
        logger.info(f"Order {order_id} packaging priority successfully elevated to EXPEDITED in fulfilment domain.")
        return 200, duration_ms, "SUCCESS", "", ""

    def verify_fulfilment_state(self, order_id: str) -> Tuple[bool, str]:
        """Downstream state verification probe for warehouse fulfilment. Does not trust HTTP 200 alone."""
        allocation = self._fulfilment_allocations.get(order_id)
        if allocation and allocation.get("priority") == "EXPEDITED" and allocation.get("status") == "ALLOCATED":
            details = (
                f"Verified: Order {order_id} packaging priority elevated to EXPEDITED in warehouse fulfilment domain store. "
                f"Allocation confirmed."
            )
            return True, details
        return False, "Verification failed: Fulfilment domain store does not confirm expedited priority status."

    # -------------------------------------------------------------------------
    # Stage 6: Logistics Dispatch (logistics_service)
    # -------------------------------------------------------------------------
    def dispatch_logistics(self, order_id: str) -> Tuple[int, int, str, str, str]:
        duration_ms = 210
        return 200, duration_ms, "SUCCESS", "", ""

    # -------------------------------------------------------------------------
    # Stage 7: Customer Notification (notification_service)
    # -------------------------------------------------------------------------
    def send_notification(self, order_id: str) -> Tuple[int, int, str, str, str]:
        duration_ms = 85
        return 200, duration_ms, "SUCCESS", "", ""


simulator = DownstreamServiceSimulator()


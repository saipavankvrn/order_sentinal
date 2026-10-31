from typing import Tuple, Dict, Any
from backend.app.models.order import Incident
from backend.app.core.logging import logger


class PolicyEngine:
    """Deterministic Policy-as-Code engine.
    Serves as the absolute boundary between advisory recommendations and system mutations.
    """

    MAX_RETRIES = 3

    @classmethod
    def evaluate_action(
        cls,
        incident: Incident,
        proposed_action: str
    ) -> Tuple[bool, str, int, bool]:
        """
        Evaluates candidate action against policy rules.
        Returns:
            (authorized: bool, reason: str, backoff_sec: int, escalate: bool)
        """
        # Rule 1: Check retry limits (max 3 retries after initial failure)
        # retry_count reflects retries already executed.
        if incident.retry_count >= cls.MAX_RETRIES:
            logger.warning(
                f"Policy rejected action: Incident {incident.incident_id} exhausted max retries "
                f"({incident.retry_count}/{cls.MAX_RETRIES})."
            )
            return False, f"Maximum retry attempts ({cls.MAX_RETRIES}) exhausted. Automatic retry prohibited.", 0, True

        # Rule 2: Guard against blind retries on payment or customer order creation
        if incident.stage in ["CUSTOMER_ORDER", "PAYMENT"] and proposed_action == "RETRY_WITH_BACKOFF":
            logger.critical(f"Policy violation: Attempted blind retry on privileged stage: {incident.stage}")
            return False, f"Blind retry prohibited on {incident.stage}. Manual verification required.", 0, True

        # Rule 3: Technical transient errors (e.g. HTTP 503)
        if incident.failure_type == "HTTP_503" and proposed_action == "RETRY_WITH_BACKOFF":
            # Attempt number will be retry_count + 1
            next_attempt = incident.retry_count + 1
            # Exponential backoff: attempt 1 -> 1s, attempt 2 -> 2s, attempt 3 -> 4s
            backoff_sec = 2 ** (next_attempt - 1)
            return True, f"Policy authorized retry attempt {next_attempt} with {backoff_sec}s backoff.", backoff_sec, False

        # Rule 4: Guard against destructive or blind actions on SLA delay (Scenario 2)
        if incident.failure_category == "ORDER_DELAY" or incident.failure_type == "SLA_BREACH":
            if proposed_action in ["CANCEL_ORDER", "AUTOMATIC_CANCELLATION", "CANCEL", "REASSIGN_WAREHOUSE"]:
                logger.warning(f"Policy violation: Destructive action '{proposed_action}' rejected for delayed order {incident.order_id}.")
                return False, "Policy violation: Automatic order cancellation or warehouse reassignment is prohibited for SLA delays.", 0, False

            if proposed_action == "RETRY_WITH_BACKOFF":
                logger.warning(f"Policy violation: Blind technical retry rejected for SLA delay on {incident.order_id}.")
                return False, "Policy violation: Blind retries prohibited for SLA delay bottlenecks. Use non-destructive expedite actions.", 0, False

            if proposed_action in ["EXPEDITE_FULFILMENT", "EXPEDITE_FULFILMENT_QUEUE"]:
                return True, "Policy authorized: Non-destructive priority queue expedition authorized for fulfilment SLA bottleneck.", 0, False

        # Rule 5: Hard business rejections require human approval and strictly prohibit auto-retries
        if incident.failure_category == "ORDER_REJECTION" or incident.failure_type in ["OUT_OF_STOCK", "HTTP_422"]:
            logger.warning(f"Policy violation: Automated action '{proposed_action}' rejected for hard business rejection on {incident.order_id}.")
            if proposed_action == "RETRY_WITH_BACKOFF":
                return False, "Policy violation: Blind technical retries are strictly prohibited for hard business rejections (OUT_OF_STOCK). Human approval required.", 0, False
            return False, "Hard business rejection prohibited from automated execution. Operator decision via Human Approval Queue is required.", 0, False

        return False, f"Action '{proposed_action}' not authorized for failure type '{incident.failure_type}'.", 0, False


policy_engine = PolicyEngine()


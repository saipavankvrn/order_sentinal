import json
from typing import Dict, Any, List
from backend.app.core.config import settings
from backend.app.core.logging import logger


class AdvisoryRCAEngine:
    """Advisory Root Cause Analysis engine with deterministic fallback.
    Gemini API is advisory only. It possesses zero permissions to modify order states.
    """

    def analyze_incident(
        self,
        incident_id: str,
        order_id: str,
        stage: str,
        service_name: str,
        failure_type: str,
        recent_events: List[Dict[str, Any]],
        error_message: str
    ) -> Dict[str, Any]:
        """Produces a structured advisory RCA diagnosis."""
        evidence_list = []
        for evt in recent_events:
            status_desc = f"HTTP {evt.get('http_status')} on {evt.get('endpoint')}"
            if evt.get("error_message"):
                status_desc += f" ({evt.get('error_message')})"
            evidence_list.append(status_desc)

        if error_message and error_message not in evidence_list:
            evidence_list.append(f"Observed error: {error_message}")

        # Attempt Gemini API if configured
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                diagnosis = self._call_gemini_api(
                    stage=stage,
                    service_name=service_name,
                    failure_type=failure_type,
                    evidence_list=evidence_list,
                    error_message=error_message
                )
                if diagnosis:
                    logger.info(f"RCA generated successfully via Gemini [{settings.GEMINI_MODEL_ID}]")
                    return diagnosis
            except Exception as e:
                logger.warning(f"Gemini RCA call failed ({e}). Activating deterministic fallback.")

        # Deterministic Fallback Engine
        logger.info("Generating RCA via internal deterministic rule engine.")
        return self._generate_deterministic_fallback(
            stage=stage,
            service_name=service_name,
            failure_type=failure_type,
            evidence_list=evidence_list,
            error_message=error_message
        )

    def _call_gemini_api(
        self,
        stage: str,
        service_name: str,
        failure_type: str,
        evidence_list: List[str],
        error_message: str
    ) -> Dict[str, Any]:
        """Calls Google GenAI SDK for advisory diagnosis."""
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=30000)
        )

        prompt = f"""
You are an expert site reliability and root cause analysis operations agent.
Analyze the following telemetry incident in a multi-hop e-commerce order journey:

Failing Stage: {stage}
Failing Service: {service_name}
Failure Code: {failure_type}
Error Details: {error_message}
Observed Telemetry Evidence:
{json.dumps(evidence_list, indent=2)}

Domain Classification & Action Guidelines:
- If failure_type is 'HTTP_503' or transient error:
  failure_category must be "API_ERROR"
  recommended_action must be "RETRY_WITH_BACKOFF"
  risk_level must be "LOW"
- If failure_type is 'SLA_BREACH' or fulfilment delay:
  failure_category must be "ORDER_DELAY"
  recommended_action must be "EXPEDITE_FULFILMENT"
  risk_level must be "LOW"
- If failure_type is 'OUT_OF_STOCK' or 'HTTP_422' permanent business rejection:
  failure_category must be "ORDER_REJECTION"
  recommended_action must be "SUBSTITUTE_SKU_AND_REALLOCATE"
  risk_level must be "HIGH"

Provide an advisory root cause analysis in valid JSON strictly adhering to this schema:
{{
  "failure_category": "ORDER_DELAY | ORDER_REJECTION | API_ERROR",
  "affected_service": "{service_name}",
  "observed_evidence": {json.dumps(evidence_list)},
  "probable_root_cause": "concise narrative of why it failed",
  "evidence_strength": "HIGH",
  "corroborating_signals_count": {len(evidence_list)},
  "recommended_action": "EXPEDITE_FULFILMENT | SUBSTITUTE_SKU_AND_REALLOCATE | RETRY_WITH_BACKOFF",
  "risk_level": "LOW | HIGH | MEDIUM",
  "explanation": "concise evidence-grounded explanation"
}}
Do NOT include internal chain-of-thought. Do not wrap in markdown tags if possible, output raw JSON.
"""
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )

        content = response.text.strip()
        data = json.loads(content)
        data["model_source"] = settings.GEMINI_MODEL_ID
        data["prompt_tokens"] = getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") else 0
        return data

    def _generate_deterministic_fallback(
        self,
        stage: str,
        service_name: str,
        failure_type: str,
        evidence_list: List[str],
        error_message: str
    ) -> Dict[str, Any]:
        """Deterministic rule engine providing reliable identical diagnosis when offline."""
        if failure_type == "HTTP_503":
            category = "API_ERROR"
            root_cause = "Transient database connection pool starvation on inventory replica node. Downstream service is alive but experiencing momentary backpressure."
            evidence = evidence_list if evidence_list else [
                "Endpoint POST /v1/inventory/reserve returned HTTP 503 Service Unavailable",
                "Execution round-trip latency recorded at 350ms",
                "Downstream inventory service reported replica connection pool exhausted"
            ]
            action = "RETRY_WITH_BACKOFF"
            risk = "LOW"
            explanation = "HTTP 503 is a standard transient failure code. The order has not progressed beyond inventory reservation. An exponential backoff retry with a unique idempotency key is policy-approved."
        elif failure_type == "SLA_BREACH" or stage == "FULFILMENT":
            category = "ORDER_DELAY"
            root_cause = "Warehouse picking station queue congestion and automated packaging conveyor backpressure in regional fulfilment center."
            evidence = evidence_list if evidence_list else [
                "Stage FULFILMENT duration exceeded configured illustrative demo SLA threshold (5000ms)",
                "Packaging station telemetry reports high queue depth",
                "Order status transitioned to DELAYED pending priority resolution"
            ]
            action = "EXPEDITE_FULFILMENT"
            risk = "LOW"
            explanation = "Warehouse fulfilment latency breached the SLA threshold. The order is delayed but inventory is reserved and payment captured. Policy strictly prohibits automatic cancellation. Non-destructive priority queue expedition is authorized."
        elif failure_type in ["OUT_OF_STOCK", "HTTP_422"] or stage == "INVENTORY":
            category = "ORDER_REJECTION"
            root_cause = "Inventory reservation failed: Primary product SKU is out-of-stock at designated regional distribution warehouse hub."
            evidence = evidence_list if evidence_list else [
                "Endpoint POST /v1/inventory/reserve returned HTTP 422 Unprocessable Entity",
                "Downstream inventory service reported zero physical stock available for SKU",
                "Prior stages completed cleanly (Address validated, Payment captured successfully)"
            ]
            action = "SUBSTITUTE_SKU_AND_REALLOCATE"
            risk = "HIGH"
            explanation = "Physical inventory depleted for requested product SKU. Automatic technical retry is strictly prohibited for permanent business rejections. Human-in-the-Loop approval is required to review evidence and authorize SKU substitution or alternate warehouse hub allocation."
        else:
            category = "API_ERROR"
            root_cause = f"Service failure detected on {service_name} with status {failure_type}."
            evidence = evidence_list if evidence_list else [f"Observed error: {error_message}"]
            action = "RETRY_WITH_BACKOFF"
            risk = "MEDIUM"
            explanation = f"Failure detected at {stage}. Policy review required before further action."

        return {
            "failure_category": category,
            "affected_service": service_name,
            "observed_evidence": evidence,
            "probable_root_cause": root_cause,
            "evidence_strength": "HIGH",
            "corroborating_signals_count": len(evidence),
            "recommended_action": action,
            "risk_level": risk,
            "explanation": explanation,
            "model_source": "DETERMINISTIC_FALLBACK",
            "prompt_tokens": 0
        }


rca_engine = AdvisoryRCAEngine()


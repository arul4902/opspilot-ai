import re
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.core.llm import get_llm_client
from backend.app.core.logging import logger


SUPPORTED_INTENTS = [
    "ORDER_TRACKING",
    "DELIVERY_DELAY",
    "PAYMENT_FAILURE",
    "PAYMENT_DEDUCTED_ORDER_MISSING",
    "REFUND_REQUEST",
    "RETURN_REQUEST",
    "ORDER_CANCELLATION",
    "PRODUCT_INFORMATION",
    "POLICY_QUERY",
    "GENERAL_SUPPORT",
]


class ExtractedEntities(BaseModel):
    order_number: Optional[str] = None
    order_id: Optional[int] = None
    transaction_reference: Optional[str] = None
    customer_id: Optional[int] = None
    product_query: Optional[str] = None
    reason: Optional[str] = None


class IntentClassificationResult(BaseModel):
    intent: str
    confidence: float
    entities: ExtractedEntities
    reasoning: str


class IntentClassifier:
    def __init__(self):
        self.llm = get_llm_client()

    def classify(self, query: str) -> IntentClassificationResult:
        """
        Classifies incoming customer request using LLM + deterministic regex entity extraction.
        """
        # 1. Deterministic entity extraction regexes
        entities = ExtractedEntities()

        order_match = re.search(r'\b(ORD-\d{4}-\d{4})\b', query, re.IGNORECASE)
        if order_match:
            entities.order_number = order_match.group(1).upper()
            try:
                entities.order_id = int(entities.order_number.split("-")[-1])
            except Exception:
                pass

        txn_match = re.search(r'\b(TXN-\d{4}-\d+)\b', query, re.IGNORECASE)
        if txn_match:
            entities.transaction_reference = txn_match.group(1).upper()

        cust_match = re.search(r'\b(CUST-\d{4})\b', query, re.IGNORECASE)
        if cust_match:
            try:
                entities.customer_id = int(cust_match.group(1).split("-")[-1]) - 1000
            except Exception:
                pass

        # 2. LLM Intent Prompting
        system_prompt = (
            "You are an expert E-commerce Operations Intent Classifier. "
            f"Classify the customer's request into EXACTLY ONE of the following intents: {SUPPORTED_INTENTS}. "
            "Output JSON only with keys: 'intent', 'confidence', 'extracted_entities', 'reasoning'."
        )
        user_prompt = f"Classify intent for Customer Query: \"{query}\""

        try:
            raw_response = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt, json_mode=True)
            # Parse response
            # Clean possible markdown wrapping ```json ... ```
            clean_json = re.sub(r'^```json\s*|\s*```$', '', raw_response.strip(), flags=re.MULTILINE)
            data = json.loads(clean_json)

            intent = data.get("intent", "GENERAL_SUPPORT")
            if intent not in SUPPORTED_INTENTS:
                intent = "GENERAL_SUPPORT"

            confidence = float(data.get("confidence", 0.90))
            reasoning = data.get("reasoning", "Classified via intent analysis.")

            # Merge any LLM extracted entities with regex entities
            llm_entities = data.get("extracted_entities", {})
            if not entities.order_number and llm_entities.get("order_number"):
                entities.order_number = str(llm_entities["order_number"]).upper()
            if not entities.transaction_reference and llm_entities.get("transaction_reference"):
                entities.transaction_reference = str(llm_entities["transaction_reference"]).upper()

            return IntentClassificationResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"Intent classification failed: {e}. Falling back to rule-based classification.")
            # Deterministic fallback classification
            q_lower = query.lower()
            intent = "GENERAL_SUPPORT"
            if "policy" in q_lower or "window" in q_lower or "return policy" in q_lower:
                intent = "POLICY_QUERY"
            elif "deducted" in q_lower and ("missing" in q_lower or "no order" in q_lower or "not confirmed" in q_lower):
                intent = "PAYMENT_DEDUCTED_ORDER_MISSING"
            elif "delay" in q_lower or "late" in q_lower or "not arrived" in q_lower:
                intent = "DELIVERY_DELAY"
            elif "track" in q_lower or "where is" in q_lower or "delivery" in q_lower:
                intent = "ORDER_TRACKING"
            elif "failed" in q_lower or "decline" in q_lower or "payment" in q_lower:
                intent = "PAYMENT_FAILURE"
            elif "refund" in q_lower:
                intent = "REFUND_REQUEST"
            elif "return" in q_lower or "exchange" in q_lower:
                intent = "RETURN_REQUEST"
            elif "cancel" in q_lower:
                intent = "ORDER_CANCELLATION"

            return IntentClassificationResult(
                intent=intent,
                confidence=0.85,
                entities=entities,
                reasoning="Rule-based fallback classifier."
            )


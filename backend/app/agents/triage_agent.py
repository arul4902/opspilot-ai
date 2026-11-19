from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.models import Customer
from backend.app.agents.intent_classifier import IntentClassifier, IntentClassificationResult


class TriageContext:
    def __init__(
        self,
        query: str,
        customer_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        self.query = query
        self.customer_id = customer_id
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.customer_name: Optional[str] = None
        self.classification: Optional[IntentClassificationResult] = None
        self.active_order_ref: Optional[str] = None
        self.active_txn_ref: Optional[str] = None


class TriageAgent:
    """
    Triage Agent: The first line of autonomous operations.
    Responsible for intent classification, entity extraction, and customer context resolution.
    """
    def __init__(self, db: Session):
        self.db = db
        self.classifier = IntentClassifier()

    def triage(
        self,
        query: str,
        customer_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> TriageContext:
        ctx = TriageContext(query, customer_id, conversation_id, user_id)

        # Classify intent & extract entities
        classification = self.classifier.classify(query)
        ctx.classification = classification

        # Resolve customer identity
        if customer_id:
            cust = self.db.query(Customer).filter(Customer.id == customer_id).first()
            if cust:
                ctx.customer_name = cust.name
                ctx.customer_id = cust.id
        elif classification.entities.customer_id:
            cust = self.db.query(Customer).filter(Customer.id == classification.entities.customer_id).first()
            if cust:
                ctx.customer_name = cust.name
                ctx.customer_id = cust.id

        # Resolve primary order and transaction references
        if classification.entities.order_number:
            ctx.active_order_ref = classification.entities.order_number
        elif classification.entities.order_id:
            ctx.active_order_ref = f"ORD-{classification.entities.order_id}"

        if classification.entities.transaction_reference:
            ctx.active_txn_ref = classification.entities.transaction_reference

        return ctx


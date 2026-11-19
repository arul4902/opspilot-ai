import re
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


class BaseLLMClient(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name string."""
        pass

    @property
    @abstractmethod
    def is_live(self) -> bool:
        """Whether this client uses a live external LLM API."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        """Generate response from LLM."""
        pass


class MockLLMClient(BaseLLMClient):
    """
    Intelligent deterministic mock client for offline testing, local demoing,
    and CI/CD without mandatory paid external API keys.
    """
    @property
    def provider_name(self) -> str:
        return "Deterministic Demo Engine (Offline Guardrails)"

    @property
    def is_live(self) -> bool:
        return False
    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        combined = f"{system_prompt or ''} {prompt}".lower()

        # Intent classification detection - only when json_mode or explicit classification prompt
        if json_mode or "triage classification" in combined or "classify intent" in combined or "classify the customer" in combined or "classify customer request" in combined:
            # Extract customer query from prompt
            query_match = re.search(r'customer query:\s*["\']?(.*?)["\']?\s*(?:\n|$)', prompt, re.IGNORECASE)
            query = query_match.group(1).lower() if query_match else prompt.lower()

            # Check order numbers
            order_match = re.search(r'ord-\d{4}-\d{4}', prompt, re.IGNORECASE)
            order_ref = order_match.group(0).upper() if order_match else None

            # Check transaction references
            txn_match = re.search(r'txn-\d{4}-\d+', prompt, re.IGNORECASE)
            txn_ref = txn_match.group(0).upper() if txn_match else None

            intent = "GENERAL_SUPPORT"
            if "policy" in query or "window" in query or "warranty" in query or "how many days" in query:
                intent = "POLICY_QUERY"
            elif "deducted" in query and ("no order" in query or "not confirmed" in query or "missing" in query):
                intent = "PAYMENT_DEDUCTED_ORDER_MISSING"
            elif "delay" in query or "late" in query or "not arrived" in query:
                intent = "DELIVERY_DELAY"
            elif "track" in query or "where is" in query or "delivery status" in query or "arrive" in query:
                intent = "ORDER_TRACKING"
            elif "refund" in query:
                intent = "REFUND_REQUEST"
            elif "return" in query or "exchange" in query:
                intent = "RETURN_REQUEST"
            elif "payment failed" in query or "declined" in query or "payment issue" in query or "payment error" in query or "failed" in query:
                intent = "PAYMENT_FAILURE"
            elif "cancel" in query:
                intent = "ORDER_CANCELLATION"
            elif "product" in query or "specs" in query or "feature" in query:
                intent = "PRODUCT_INFORMATION"

            return json.dumps({
                "intent": intent,
                "confidence": 0.95,
                "extracted_entities": {
                    "order_number": order_ref,
                    "transaction_reference": txn_ref
                },
                "reasoning": f"Query analyzed with intent pattern match for {intent}."
            })

        # Final response synthesis
        is_approval = "requires human approval: true" in prompt.lower()
        order_match = re.search(r'ord-\d{4}-\d{4}', prompt, re.IGNORECASE)
        order_str = order_match.group(0).upper() if order_match else "your order"

        resp_parts = [
            f"Thank you for contacting OpsPilot Support regarding {order_str}.",
            "I have investigated your inquiry against our live database, transaction telemetry, and enterprise policy records."
        ]

        if "delay" in prompt.lower() or "weather" in prompt.lower():
            resp_parts.append("Our tracking telemetry confirms your shipment encountered a courier weather delay past our guaranteed SLA. Per our Shipping Delay SLA Policy (POL-LOG-2026-v2), a courtesy credit has been recommended.")
        elif "orphan" in prompt.lower() or "payment_deducted_order_missing" in prompt.lower():
            resp_parts.append("We verified that your payment was captured successfully, but an automated checkout session drop prevented order creation. Per our Payment Discrepancy Policy (POL-PAY-2026-v2), this has been escalated for immediate fulfillment or full refund.")
        elif "failed" in prompt.lower() or "payment_failure" in prompt.lower():
            resp_parts.append("Our payment gateway records confirm the transaction was declined by the issuing bank. Please retry using an alternative payment method.")
        elif "return" in prompt.lower() or "exchange" in prompt.lower():
            resp_parts.append("Under our 30-Day Return Policy (POL-RET-2026-v2), your request has been validated and authorized. A prepaid return shipping label has been dispatched.")
        elif "refund" in prompt.lower():
            resp_parts.append("Under our Refund Policy (POL-REF-2026-v2), your refund request has been verified against eligible delivered items.")
        elif "policy" in prompt.lower():
            resp_parts.append("Under OpsPilot Policy POL-RET-2026-v2, items may be returned within 30 calendar days of delivery in original condition with tags attached.")

        if is_approval:
            resp_parts.append("IMPORTANT: As this involves a consequential operational action, it has been staged for Human-In-The-Loop review in our operations approval queue.")
        else:
            resp_parts.append("All operational steps and citations have been recorded in the immutable audit log.")

        return " ".join(resp_parts)


class GeminiLLMClient(BaseLLMClient):
    """
    Google Gemini API client using standard HTTPX REST endpoint.
    """
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    @property
    def provider_name(self) -> str:
        return f"Google Gemini ({self.model_name})"

    @property
    def is_live(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        if not self.api_key:
            logger.warning("Gemini API key is not set. Falling back to MockLLMClient.")
            return MockLLMClient().generate(prompt, system_prompt, json_mode)

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System instructions: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body: Dict[str, Any] = {"contents": contents}
        if json_mode:
            body["generationConfig"] = {"responseMimeType": "application/json"}

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(self.endpoint, json=body)
                res.raise_for_status()
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
        except Exception as e:
            logger.error(f"Gemini API invocation failed: {e}. Falling back to mock client.")
            return MockLLMClient().generate(prompt, system_prompt, json_mode)


class OpenAILLMClient(BaseLLMClient):
    """
    OpenAI-compatible LLM client.
    """
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return f"OpenAI Compatible ({self.model_name})"

    @property
    def is_live(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        if not self.api_key:
            logger.warning("OpenAI API key is not set. Falling back to MockLLMClient.")
            return MockLLMClient().generate(prompt, system_prompt, json_mode)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI API invocation failed: {e}. Falling back to mock client.")
            return MockLLMClient().generate(prompt, system_prompt, json_mode)


def get_llm_client() -> BaseLLMClient:
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMClient(api_key=settings.GEMINI_API_KEY, model_name=settings.LLM_MODEL_NAME)
    elif provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMClient(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model_name=settings.LLM_MODEL_NAME
        )
    return MockLLMClient()


from typing import Dict, Type, List, Optional
from sqlalchemy.orm import Session
from backend.app.tools.base import BaseTool
from backend.app.tools.tools import (
    GetOrderDetailsTool,
    GetPaymentDetailsTool,
    CheckDeliveryStatusTool,
    SearchReturnPolicyTool,
    CreateReturnRequestTool,
    InitiateRefundRequestTool,
    CreateSupportTicketTool,
    EscalateToHumanTool,
    SearchCustomerHistoryTool,
)


class ToolRegistry:
    def __init__(self, db: Session):
        self.db = db
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        tool_classes = [
            GetOrderDetailsTool,
            GetPaymentDetailsTool,
            CheckDeliveryStatusTool,
            SearchReturnPolicyTool,
            CreateReturnRequestTool,
            InitiateRefundRequestTool,
            CreateSupportTicketTool,
            EscalateToHumanTool,
            SearchCustomerHistoryTool,
        ]
        for cls in tool_classes:
            tool_instance = cls(self.db)
            self.tools[tool_instance.name] = tool_instance

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.tools.values()
        ]


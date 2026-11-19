import time
import json
from abc import ABC, abstractmethod
from typing import Type, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from backend.app.models.models import ToolExecutionLog, ToolExecutionStatus
from backend.app.core.logging import logger


class BaseTool(ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    def __init__(self, db: Session):
        self.db = db

    def run(
        self,
        arguments: Dict[str, Any],
        agent_run_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes the tool with schema validation, execution timing, error recovery,
        and automatic logging into tool_execution_logs.
        """
        start_time = time.time()
        status_val = ToolExecutionStatus.SUCCESS.value
        error_msg = None
        output_dict: Dict[str, Any] = {}

        # 1. Validate Input
        try:
            validated_input = self.input_schema(**arguments)
        except ValidationError as ve:
            duration_ms = int((time.time() - start_time) * 1000)
            err = f"Tool argument validation failed for '{self.name}': {ve.errors()}"
            logger.error(err)
            self._log_execution(
                agent_run_id=agent_run_id,
                arguments=arguments,
                result={"success": False, "error": err},
                status=ToolExecutionStatus.FAILED.value,
                error_message=err,
                duration_ms=duration_ms
            )
            return {"success": False, "error": err}

        # 2. Execute concrete tool logic
        try:
            result_obj = self._execute(validated_input, agent_run_id=agent_run_id, user_id=user_id)
            if isinstance(result_obj, BaseModel):
                output_dict = result_obj.model_dump(mode="json")
            elif isinstance(result_obj, dict):
                output_dict = result_obj
            else:
                output_dict = {"result": str(result_obj)}
        except Exception as e:
            status_val = ToolExecutionStatus.FAILED.value
            error_msg = str(e)
            logger.exception(f"Execution failed for tool '{self.name}': {e}")
            output_dict = {"success": False, "error": f"Internal execution error: {str(e)}"}

        duration_ms = int((time.time() - start_time) * 1000)

        # 3. Log execution
        self._log_execution(
            agent_run_id=agent_run_id,
            arguments=arguments,
            result=output_dict,
            status=status_val,
            error_message=error_msg,
            duration_ms=duration_ms
        )

        return output_dict

    def _log_execution(
        self,
        agent_run_id: Optional[int],
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        status: str,
        error_message: Optional[str],
        duration_ms: int
    ):
        if not agent_run_id:
            return
        try:
            log_entry = ToolExecutionLog(
                agent_run_id=agent_run_id,
                tool_name=self.name,
                input_arguments_json=json.dumps(arguments),
                output_result_json=json.dumps(result),
                status=status,
                error_message=error_message,
                duration_ms=duration_ms,
                executed_at=datetime.now(timezone.utc)
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log tool execution: {e}")

    @abstractmethod
    def _execute(
        self,
        input_data: BaseModel,
        agent_run_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> BaseModel:
        """Concrete tool implementation logic."""
        pass


"""
Core Agent Framework
Production-grade agent interface with versioning, registry, and composability.
"""
import logging
import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentOutput(BaseModel):
    """Standard agent output wrapper."""
    agent_name: str
    agent_version: str
    status: AgentStatus
    output: Dict[str, Any]
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    execution_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "parsing_agent",
                "agent_version": "1.0.0",
                "status": "success",
                "output": {"case_id": "abc123", "spec": {}},
                "errors": [],
                "warnings": [],
                "execution_time_ms": 125.5,
                "timestamp": "2026-01-15T12:00:00Z"
            }
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Prompt Runner platform.
    
    All agents MUST:
    1. Define input_schema and output_schema (Pydantic models)
    2. Implement execute() method
    3. Support version tracking
    4. Return AgentOutput wrapper
    5. Handle errors gracefully
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def input_schema(self) -> Type[BaseModel]:
        """Return Pydantic model for input validation."""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        """Return Pydantic model for output validation."""
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any], trace_id: Optional[str] = None) -> AgentOutput:
        """
        Execute the agent logic.
        
        Args:
            input_data: Validated input dictionary
            trace_id: Optional trace ID for distributed tracing
            
        Returns:
            AgentOutput with status, output, errors, warnings
        """
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input against input_schema."""
        try:
            self.input_schema(**input_data)
            return True
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output against output_schema."""
        try:
            self.output_schema(**output_data)
            return True
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False
    
    def run(self, input_data: Dict[str, Any], trace_id: Optional[str] = None) -> AgentOutput:
        """
        Public method to run the agent with validation and error handling.
        
        This wraps execute() with standard logging, timing, and validation.
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data):
                return AgentOutput(
                    agent_name=self.name,
                    agent_version=self.version,
                    status=AgentStatus.FAILED,
                    output={},
                    errors=["Input validation failed"],
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            
            # Execute
            self.logger.info(f"[{trace_id}] Starting {self.name} v{self.version}")
            result = self.execute(input_data, trace_id)
            
            # Validate output
            if not self.validate_output(result.output):
                self.logger.warning(f"Output validation failed for {self.name}")
                result.warnings.append("Output validation warning (may be partial)")
            
            result.execution_time_ms = (time.time() - start_time) * 1000
            self.logger.info(f"[{trace_id}] Completed {self.name} in {result.execution_time_ms:.1f}ms")
            
            return result
        
        except Exception as e:
            self.logger.error(f"[{trace_id}] {self.name} failed: {e}", exc_info=True)
            return AgentOutput(
                agent_name=self.name,
                agent_version=self.version,
                status=AgentStatus.FAILED,
                output={},
                errors=[str(e)],
                execution_time_ms=(time.time() - start_time) * 1000,
            )


class AgentRegistry:
    """
    Global registry for agent discovery, versioning, and composition.
    """
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    _instances: Dict[str, BaseAgent] = {}
    
    @classmethod
    def register(cls, agent_class: Type[BaseAgent]):
        """Register an agent class."""
        instance = agent_class()
        key = f"{instance.name}:v{instance.version}"
        cls._agents[key] = agent_class
        cls._instances[key] = instance
        logger.info(f"Registered agent: {key}")
        return agent_class
    
    @classmethod
    def get(cls, name: str, version: str = None) -> Optional[BaseAgent]:
        """
        Get an agent instance.
        
        If version is None, returns latest version.
        """
        if version:
            key = f"{name}:v{version}"
            return cls._instances.get(key)
        
        # Find latest version
        matching = [k for k in cls._instances.keys() if k.startswith(f"{name}:v")]
        if matching:
            # Sort by version (simple sort, assumes semantic versioning)
            latest = sorted(matching)[-1]
            return cls._instances[latest]
        
        return None
    
    @classmethod
    def list_agents(cls) -> List[Dict[str, str]]:
        """List all registered agents."""
        return [
            {"name": k.split(":v")[0], "version": k.split(":v")[1]}
            for k in cls._instances.keys()
        ]
    
    @classmethod
    def get_versions(cls, name: str) -> List[str]:
        """Get all versions of an agent."""
        matching = [k for k in cls._instances.keys() if k.startswith(f"{name}:v")]
        return [k.split(":v")[1] for k in sorted(matching)]


def agent(cls):
    """Decorator to auto-register agents."""
    return AgentRegistry.register(cls)

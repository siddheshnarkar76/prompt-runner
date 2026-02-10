"""
Agent Template (Copy this to create new agents)

Steps:
1. Copy this file to agents/your_agent_name.py
2. Replace TemplateAgent with YourAgent
3. Implement input_schema, output_schema, execute()
4. Add @agent decorator
5. Register in agent_registry()
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from core.agent import BaseAgent, AgentOutput, AgentStatus, agent


class TemplateInput(BaseModel):
    """Define your input schema here."""
    param1: str = Field(..., description="First parameter")
    param2: Optional[int] = Field(None, description="Optional parameter")
    
    class Config:
        json_schema_extra = {
            "example": {
                "param1": "value",
                "param2": 42
            }
        }


class TemplateOutput(BaseModel):
    """Define your output schema here."""
    result: str = Field(..., description="Result of processing")
    status_code: int = Field(0, description="Status code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "result": "processed value",
                "status_code": 0
            }
        }


@agent
class TemplateAgent(BaseAgent):
    """
    Template Agent - Replace this with your agent description.
    
    Inputs:
        - param1 (str): ...
        - param2 (int, optional): ...
    
    Outputs:
        - result (str): ...
        - status_code (int): ...
    """
    
    def __init__(self):
        super().__init__(name="template_agent", version="1.0.0")
    
    @property
    def input_schema(self):
        return TemplateInput
    
    @property
    def output_schema(self):
        return TemplateOutput
    
    def execute(self, input_data: Dict[str, Any], trace_id: Optional[str] = None) -> AgentOutput:
        """
        Implement your agent logic here.
        """
        try:
            # Validate input (optional, done by run() but useful for clarity)
            input_obj = TemplateInput(**input_data)
            
            # Your logic here
            result = f"Processed {input_obj.param1}"
            
            # Prepare output
            output = {
                "result": result,
                "status_code": 0
            }
            
            return AgentOutput(
                agent_name=self.name,
                agent_version=self.version,
                status=AgentStatus.SUCCESS,
                output=output,
                errors=[],
                warnings=[]
            )
        
        except Exception as e:
            self.logger.error(f"Template agent failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                agent_version=self.version,
                status=AgentStatus.FAILED,
                output={},
                errors=[str(e)],
                warnings=[]
            )


# Usage example
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    agent = TemplateAgent()
    result = agent.run({
        "param1": "test",
        "param2": 100
    })
    
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Time: {result.execution_time_ms:.1f}ms")

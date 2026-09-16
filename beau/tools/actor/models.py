from pydantic import BaseModel

class EvaluatorOutput(BaseModel):
    is_success: bool
    feedback: str
    needs_confirm: bool = False
    command: str = ""

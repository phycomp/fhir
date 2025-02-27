#1.2 定義 FHIR 資源模型 根據 FHIR 標準定義 Patient 資源的模型：

# models.py
from pydantic import BaseModel, Field
from typing import Optional
import uuid

class Patient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resourceType: str = "Patient"
    name: str
    gender: Optional[str]
    birthDate: Optional[str]

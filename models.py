from typing import List, Optional
from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None


class TableStatus(BaseModel):
    exists: bool
    schema_name: str
    table_name: str
    columns: List[ColumnInfo] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    indexes: List[str] = Field(default_factory=list)


class AgentInput(BaseModel):
    database_type: str = "PostgreSQL"
    database_url: Optional[str] = None
    schema_name: str
    object_type: str = "TABLE"
    table_name: str
    table_instructions: str


class AgentOutput(BaseModel):
    success: bool
    action: str  # "CREATED_TABLE" | "ALTERED_TABLE" | "NO_OP"
    schema_name: str
    table_name: str
    generated_sql: str
    explanation: str
    before_columns: List[ColumnInfo] = Field(default_factory=list)
    after_columns: List[ColumnInfo] = Field(default_factory=list)
    error: Optional[str] = None

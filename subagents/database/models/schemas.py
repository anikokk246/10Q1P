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


class DDLTaskInput(BaseModel):
    database_url: Optional[str] = None
    schema_name: str = Field(description="PostgreSQL schema name (e.g. public)")
    object_type: str = Field(default="TABLE", description="DDL object type")
    table_name: str = Field(description="Target table name")
    table_instructions: str = Field(description="Instructions for columns, data types, constraints, indexes")


class DDLTaskOutput(BaseModel):
    success: bool
    action: str  # "CREATED_TABLE" | "ALTERED_TABLE" | "NO_OP"
    schema_name: str
    table_name: str
    generated_sql: str
    explanation: str
    before_columns: List[ColumnInfo] = Field(default_factory=list)
    after_columns: List[ColumnInfo] = Field(default_factory=list)
    error: Optional[str] = None

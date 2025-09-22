"""Pydantic schemas for certification profiles."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class CertificationDomain(BaseModel):
    """Certification domain schema."""
    name: str = Field(..., description="Domain name")
    weight_percentage: int = Field(..., ge=1, le=100, description="Domain weight percentage")
    topics: List[str] = Field(..., description="List of topics in this domain")


class CertificationProfileBase(BaseModel):
    """Base certification profile schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Certification name")
    version: str = Field(..., min_length=1, max_length=100, description="Certification version")
    provider: str = Field(..., min_length=1, max_length=255, description="Certification provider")
    description: Optional[str] = Field(None, description="Certification description")
    exam_code: Optional[str] = Field(None, max_length=50, description="Official exam code")
    passing_score: Optional[int] = Field(None, ge=0, le=100, description="Passing score percentage")
    exam_duration_minutes: Optional[int] = Field(None, ge=1, description="Exam duration in minutes")
    question_count: Optional[int] = Field(None, ge=1, description="Number of questions in exam")
    exam_domains: List[CertificationDomain] = Field(..., description="Exam domains and weightings")
    prerequisites: Optional[List[str]] = Field(default_factory=list, description="Prerequisites")
    recommended_experience: Optional[str] = Field(None, description="Recommended experience")
    is_active: bool = Field(default=True, description="Whether profile is active")

    @validator('exam_domains')
    def validate_domain_weights(cls, domains):
        """Validate that domain weights sum to 100%."""
        total_weight = sum(domain.weight_percentage for domain in domains)
        if total_weight != 100:
            raise ValueError(f"Domain weights must sum to 100%, got {total_weight}%")
        return domains

    @validator('name', 'provider')
    def validate_non_empty_strings(cls, v):
        """Validate that strings are not empty after stripping."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class CertificationProfileCreate(CertificationProfileBase):
    """Schema for creating certification profiles."""
    pass


class CertificationProfileUpdate(BaseModel):
    """Schema for updating certification profiles."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    version: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    exam_code: Optional[str] = Field(None, max_length=50)
    passing_score: Optional[int] = Field(None, ge=0, le=100)
    exam_duration_minutes: Optional[int] = Field(None, ge=1)
    question_count: Optional[int] = Field(None, ge=1)
    exam_domains: Optional[List[CertificationDomain]] = Field(None)
    prerequisites: Optional[List[str]] = Field(None)
    recommended_experience: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)

    @validator('exam_domains')
    def validate_domain_weights(cls, domains):
        """Validate that domain weights sum to 100% if provided."""
        if domains is not None:
            total_weight = sum(domain.weight_percentage for domain in domains)
            if total_weight != 100:
                raise ValueError(f"Domain weights must sum to 100%, got {total_weight}%")
        return domains


class CertificationProfileResponse(CertificationProfileBase):
    """Schema for certification profile responses."""
    id: UUID = Field(..., description="Profile unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CertificationProfileSummary(BaseModel):
    """Summary schema for certification profiles."""
    id: UUID
    name: str
    version: str
    provider: str
    exam_code: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
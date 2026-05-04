from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


FamiliarityRating = Literal["unknown", "weak", "okay", "strong"]
GapSeverity = Literal["high", "medium", "low"]


class AnalyzeMaterialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: str = Field(
        min_length=80,
        max_length=20000,
        description="Pasted college STEM study material to analyze.",
    )
    subject: Optional[str] = Field(default=None, max_length=80)
    level: Optional[str] = Field(default=None, max_length=80)


class TargetConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)


class PrerequisiteConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    supports: list[str] = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)


class FamiliarityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class AnalyzeMaterialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_concepts: list[TargetConcept] = Field(min_length=1)
    prerequisites: list[PrerequisiteConcept] = Field(min_length=1)
    familiarity_checks: list[FamiliarityCheck] = Field(min_length=1)


class ScaffoldPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis: AnalyzeMaterialResponse
    ratings: dict[str, FamiliarityRating] = Field(min_length=1)


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    severity: GapSeverity
    why_it_blocks_learning: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class ScaffoldPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gaps: list[Gap] = Field(min_length=1)
    study_sequence: list[str] = Field(min_length=1)
    confidence_notes: list[str] = Field(min_length=1)

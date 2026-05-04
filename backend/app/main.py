from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AnalyzeMaterialRequest,
    AnalyzeMaterialResponse,
    ScaffoldPlanRequest,
    ScaffoldPlanResponse,
)
from app.services.anthropic_learning import (
    AnthropicLearningService,
    InvalidAIResponseError,
    LearningServiceError,
    MissingAPIKeyError,
)

load_dotenv()

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app = FastAPI(title="Keystone AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_learning_service() -> AnthropicLearningService:
    return AnthropicLearningService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": "keystone-ai"}


@app.post("/api/analyze-material", response_model=AnalyzeMaterialResponse)
async def analyze_material(
    request: AnalyzeMaterialRequest,
    learning_service: AnthropicLearningService = Depends(get_learning_service),
) -> AnalyzeMaterialResponse:
    try:
        return await learning_service.analyze_material(
            material=request.material,
            subject=request.subject,
            level=request.level,
        )
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InvalidAIResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="Keystone received an incomplete AI response. Please retry the analysis.",
        ) from exc
    except LearningServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/scaffold-plan", response_model=ScaffoldPlanResponse)
async def scaffold_plan(
    request: ScaffoldPlanRequest,
    learning_service: AnthropicLearningService = Depends(get_learning_service),
) -> ScaffoldPlanResponse:
    try:
        return await learning_service.scaffold_plan(
            analysis=request.analysis,
            ratings=request.ratings,
        )
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InvalidAIResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="Keystone received an incomplete AI response. Please retry the plan.",
        ) from exc
    except LearningServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

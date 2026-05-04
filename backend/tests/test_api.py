from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_learning_service
from app.schemas import AnalyzeMaterialResponse, ScaffoldPlanResponse


class FakeLearningService:
    async def analyze_material(self, material: str, subject: str | None, level: str | None):
        assert "derivative" in material.lower()
        assert subject == "Calculus"
        assert level == "college"
        return AnalyzeMaterialResponse(
            target_concepts=[
                {
                    "id": "chain-rule",
                    "title": "Chain rule",
                    "summary": "Differentiate nested functions by multiplying outer and inner rates.",
                    "evidence": ["differentiate composite functions like sin(x^2)"],
                }
            ],
            prerequisites=[
                {
                    "id": "function-composition",
                    "title": "Function composition",
                    "why_it_matters": "The chain rule depends on seeing one function inside another.",
                    "supports": ["chain-rule"],
                    "evidence": ["composite functions like sin(x^2)"],
                }
            ],
            familiarity_checks=[
                {
                    "concept_id": "function-composition",
                    "prompt": "How comfortable are you rewriting sin(x^2) as f(g(x))?",
                }
            ],
        )

    async def scaffold_plan(self, analysis: AnalyzeMaterialResponse, ratings: dict[str, str]):
        assert analysis.target_concepts[0].id == "chain-rule"
        assert ratings == {"function-composition": "weak"}
        return ScaffoldPlanResponse(
            gaps=[
                {
                    "concept_id": "function-composition",
                    "title": "Function composition",
                    "severity": "high",
                    "why_it_blocks_learning": "A weak grasp makes nested rates hard to follow.",
                    "next_step": "Practice identifying inner and outer functions before differentiating.",
                }
            ],
            study_sequence=[
                "Identify inner and outer functions in five examples.",
                "Differentiate the outer function while holding the inner expression fixed.",
                "Multiply by the derivative of the inner expression.",
            ],
            confidence_notes=["Based on one pasted excerpt and one self-rating."],
        )


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def client() -> TestClient:
    return TestClient(app)


def calculus_material() -> str:
    return (
        "To calculate the derivative of a composite function such as sin(x^2), "
        "the chain rule tells us to differentiate the outer function and multiply "
        "by the derivative of the inner function. This appears often in college calculus."
    )


def test_health_reports_keystone_project():
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "project": "keystone-ai"}


def test_analyze_material_rejects_too_short_material():
    response = client().post("/api/analyze-material", json={"material": "too short"})

    assert response.status_code == 422
    assert "at least 80 characters" in str(response.json()["detail"])


def test_analyze_material_returns_friendly_error_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client().post(
        "/api/analyze-material",
        json={"material": calculus_material(), "subject": "Calculus", "level": "college"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Add ANTHROPIC_API_KEY to run Keystone analysis."


def test_analyze_material_uses_learning_service():
    app.dependency_overrides[get_learning_service] = lambda: FakeLearningService()

    response = client().post(
        "/api/analyze-material",
        json={"material": calculus_material(), "subject": "Calculus", "level": "college"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_concepts"][0]["title"] == "Chain rule"
    assert body["prerequisites"][0]["supports"] == ["chain-rule"]
    assert body["familiarity_checks"][0]["concept_id"] == "function-composition"


def test_scaffold_plan_uses_student_familiarity_ratings():
    app.dependency_overrides[get_learning_service] = lambda: FakeLearningService()

    response = client().post(
        "/api/scaffold-plan",
        json={
            "analysis": {
                "target_concepts": [
                    {
                        "id": "chain-rule",
                        "title": "Chain rule",
                        "summary": "Differentiate nested functions.",
                        "evidence": ["sin(x^2)"],
                    }
                ],
                "prerequisites": [
                    {
                        "id": "function-composition",
                        "title": "Function composition",
                        "why_it_matters": "Required for seeing nested functions.",
                        "supports": ["chain-rule"],
                        "evidence": ["sin(x^2)"],
                    }
                ],
                "familiarity_checks": [
                    {
                        "concept_id": "function-composition",
                        "prompt": "Can you identify inner and outer functions?",
                    }
                ],
            },
            "ratings": {"function-composition": "weak"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["gaps"][0]["severity"] == "high"
    assert "inner and outer" in body["study_sequence"][0]

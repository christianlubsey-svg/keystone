from __future__ import annotations

import json

import pytest

from app.services.anthropic_learning import (
    AnthropicLearningService,
    InvalidAIResponseError,
)


def test_parse_json_response_accepts_required_analysis_shape():
    payload = {
        "target_concepts": [
            {
                "id": "electric-field",
                "title": "Electric field",
                "summary": "Force per unit charge at a point.",
                "evidence": ["electric field around a point charge"],
            }
        ],
        "prerequisites": [
            {
                "id": "vector-direction",
                "title": "Vector direction",
                "why_it_matters": "Fields require magnitude and direction.",
                "supports": ["electric-field"],
                "evidence": ["field lines point away from positive charges"],
            }
        ],
        "familiarity_checks": [
            {
                "concept_id": "vector-direction",
                "prompt": "How comfortable are you decomposing vectors into components?",
            }
        ],
    }

    result = AnthropicLearningService.parse_analysis_json(json.dumps(payload))

    assert result.target_concepts[0].id == "electric-field"
    assert result.prerequisites[0].supports == ["electric-field"]
    assert result.familiarity_checks[0].concept_id == "vector-direction"


def test_parse_json_response_rejects_malformed_json():
    with pytest.raises(InvalidAIResponseError, match="structured JSON"):
        AnthropicLearningService.parse_analysis_json("not json")


def test_parse_json_response_rejects_missing_required_keys():
    with pytest.raises(InvalidAIResponseError, match="target_concepts"):
        AnthropicLearningService.parse_analysis_json("{}")


def test_parse_scaffold_json_accepts_ranked_gap_shape():
    payload = {
        "gaps": [
            {
                "concept_id": "vector-direction",
                "title": "Vector direction",
                "severity": "medium",
                "why_it_blocks_learning": "Field reasoning breaks down without direction.",
                "next_step": "Draw three vectors and label their direction.",
            }
        ],
        "study_sequence": ["Review vector arrows before reading field diagrams."],
        "confidence_notes": ["Based on the pasted excerpt and self-ratings."],
    }

    result = AnthropicLearningService.parse_scaffold_json(json.dumps(payload))

    assert result.gaps[0].concept_id == "vector-direction"
    assert result.study_sequence == ["Review vector arrows before reading field diagrams."]

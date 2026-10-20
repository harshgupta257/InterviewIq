from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.ai.schemas import AnswerEvaluation, QuestionSet
from app.ai.structured import extract_json
from app.services.scoring import compute_average, to_percentage
from tests.conftest import EVALUATION, question_set


class TestScoring:
    def test_spec_example(self) -> None:
        avg = compute_average(4, 3, 4, 5)
        assert avg == Decimal("4.00")
        assert to_percentage(avg) == 80.0

    @pytest.mark.parametrize(
        ("scores", "pct"),
        [((1, 1, 1, 1), 20.0), ((5, 5, 5, 5), 100.0), ((3, 4, 4, 4), 75.0), ((2, 3, 3, 3), 55.0)],
    )
    def test_percentages(self, scores: tuple[int, int, int, int], pct: float) -> None:
        assert to_percentage(compute_average(*scores)) == pct

    @pytest.mark.parametrize("bad", [0, 6, -1, 3.5, True])
    def test_rejects_out_of_range(self, bad: object) -> None:
        with pytest.raises(ValueError):
            compute_average(bad, 3, 3, 3)  # type: ignore[arg-type]


class TestQuestionSchema:
    def test_valid_set(self) -> None:
        assert len(QuestionSet.model_validate(question_set()).questions) == 8

    def test_case_study_accepted_in_design_slot(self) -> None:
        cats = [
            "technical",
            "technical",
            "project_deepdive",
            "project_deepdive",
            "behavioral",
            "behavioral",
            "case_study",
            "motivation",
        ]
        QuestionSet.model_validate(question_set(cats))

    @pytest.mark.parametrize("n", [7, 9])
    def test_wrong_count(self, n: int) -> None:
        data = question_set()
        data["questions"] = (data["questions"] * 2)[:n]
        with pytest.raises(ValidationError, match="exactly 8"):
            QuestionSet.model_validate(data)

    def test_invalid_category(self) -> None:
        data = question_set()
        data["questions"][0]["category"] = "trivia"
        with pytest.raises(ValidationError):
            QuestionSet.model_validate(data)

    def test_wrong_distribution(self) -> None:
        cats = ["technical"] * 4 + ["behavioral"] * 2 + ["system_design", "motivation"]
        with pytest.raises(ValidationError, match="distribution"):
            QuestionSet.model_validate(question_set(cats))

    def test_missing_field(self) -> None:
        data = question_set()
        del data["questions"][3]["why_this_question"]
        with pytest.raises(ValidationError):
            QuestionSet.model_validate(data)

    def test_duplicate_questions(self) -> None:
        data = question_set()
        data["questions"][1]["question_text"] = data["questions"][0]["question_text"]
        with pytest.raises(ValidationError, match="unique"):
            QuestionSet.model_validate(data)


class TestEvaluationSchema:
    def test_valid(self) -> None:
        assert AnswerEvaluation.model_validate(EVALUATION).relevance == 5

    @pytest.mark.parametrize("bad", [0, 6, 3.5, "high", None])
    def test_score_range(self, bad: object) -> None:
        with pytest.raises(ValidationError):
            AnswerEvaluation.model_validate({**EVALUATION, "clarity": bad})

    def test_reason_required(self) -> None:
        with pytest.raises(ValidationError):
            AnswerEvaluation.model_validate({**EVALUATION, "specificity_reason": ""})

    def test_model_supplied_percentage_is_ignored(self) -> None:
        ev = AnswerEvaluation.model_validate({**EVALUATION, "overall_percentage": 99})
        assert not hasattr(ev, "overall_percentage")


class TestExtractJson:
    def test_code_fence(self) -> None:
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_leading_prose(self) -> None:
        assert extract_json('Here you go: {"a": 2} hope that helps') == {"a": 2}

    def test_garbage(self) -> None:
        with pytest.raises(ValueError):
            extract_json("not json at all")

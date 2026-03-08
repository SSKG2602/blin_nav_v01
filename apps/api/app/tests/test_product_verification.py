from app.agent.product_verification import verify_product_against_intent
from app.schemas.page_understanding import ProductCandidate
from app.schemas.product_verification import ProductIntentSpec, VerificationDecision


def test_verify_product_clear_match() -> None:
    intent = ProductIntentSpec(
        raw_query="pedigree dog food 3kg",
        brand="Pedigree",
        product_name="dog food",
        size_text="3kg",
    )
    candidate = ProductCandidate(
        title="Pedigree Adult Dog Food, Chicken and Vegetables, 3kg",
        variant_text="Adult dry food",
        price_text="₹799",
    )

    result = verify_product_against_intent(intent, candidate)

    assert result.decision == VerificationDecision.MATCH
    assert set(result.matched_fields) == {"brand", "product_name", "size_text"}
    assert result.confidence >= 0.80


def test_verify_product_partial_match() -> None:
    intent = ProductIntentSpec(
        raw_query="pedigree cat food",
        brand="Pedigree",
        product_name="cat food",
    )
    candidate = ProductCandidate(
        title="Pedigree Adult Dog Food, 3kg",
        price_text="₹799",
    )

    result = verify_product_against_intent(intent, candidate)

    assert result.decision == VerificationDecision.PARTIAL_MATCH
    assert "brand" in result.matched_fields
    assert "product_name" in result.mismatched_fields


def test_verify_product_mismatch() -> None:
    intent = ProductIntentSpec(
        raw_query="whiskas cat food",
        brand="Whiskas",
        product_name="cat food",
    )
    candidate = ProductCandidate(
        title="Pedigree Adult Dog Food, 3kg",
        price_text="₹799",
    )

    result = verify_product_against_intent(intent, candidate)

    assert result.decision == VerificationDecision.MISMATCH
    assert set(result.mismatched_fields) == {"brand", "product_name"}


def test_verify_product_insufficient_evidence() -> None:
    intent = ProductIntentSpec(
        raw_query="pedigree dog food",
        brand="Pedigree",
    )

    result = verify_product_against_intent(intent, None)

    assert result.decision == VerificationDecision.INSUFFICIENT_EVIDENCE
    assert result.matched_fields == []
    assert "brand" in result.missing_fields


def test_verify_product_ambiguous_variant_case() -> None:
    intent = ProductIntentSpec(
        raw_query="pedigree puppy dog food",
        brand="Pedigree",
        product_name="dog food",
        variant="puppy",
    )
    candidate = ProductCandidate(
        title="Pedigree Adult Dog Food, 3kg",
        variant_text=None,
    )

    result = verify_product_against_intent(intent, candidate)

    assert result.decision == VerificationDecision.AMBIGUOUS
    assert "brand" in result.matched_fields
    assert "product_name" in result.matched_fields
    assert "variant" in result.missing_fields


def test_verify_product_variant_precision_reports_selected_and_available_options() -> None:
    intent = ProductIntentSpec(
        raw_query="pedigree dog food 3kg",
        brand="Pedigree",
        product_name="dog food",
        size_text="3kg",
    )
    candidate = ProductCandidate(
        title="Pedigree Adult Dog Food",
        brand_text="Pedigree",
        variant_text="10kg",
        variant_options=["1kg", "3kg", "10kg"],
    )

    result = verify_product_against_intent(intent, candidate)

    assert result.decision == VerificationDecision.PARTIAL_MATCH
    assert result.expected_variant_text == "3kg"
    assert result.selected_variant_text == "10kg"
    assert "3kg" in result.available_variant_options
    assert result.comparison_summary is not None
    assert "requested variant" in result.comparison_summary.lower()

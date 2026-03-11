from app.agent.perception import classify_page_understanding
from app.schemas.page_understanding import PageType


def test_classify_search_results_page() -> None:
    raw_data = {
        "page_type": "search_results",
        "page_title": "dog food results",
        "product_candidates": [
            {
                "title": "Pedigree Adult Dry Dog Food, Chicken and Vegetables, 3kg",
                "price_text": "₹799",
                "url": "https://demo.nopcommerce.com/pedigree-dry-dog-food",
            },
            {
                "title": "Drools Focus Adult Dog Food, 3kg",
                "price_text": "₹699",
                "url": "https://demo.nopcommerce.com/drools-focus-adult-dog-food",
            },
        ],
    }

    result = classify_page_understanding(raw_data)

    assert result.page_type == PageType.SEARCH_RESULTS
    assert len(result.product_candidates) == 2
    assert result.primary_product is not None
    assert "Pedigree" in (result.primary_product.title or "")
    assert result.confidence >= 0.70


def test_classify_product_detail_page() -> None:
    raw_data = {
        "is_product_detail": True,
        "url": "https://demo.nopcommerce.com/build-your-own-computer",
        "product_title": "Pedigree Adult Dry Dog Food 3kg",
        "price_text": "₹799",
        "availability_text": "In stock",
    }

    result = classify_page_understanding(raw_data)

    assert result.page_type == PageType.PRODUCT_DETAIL
    assert result.primary_product is not None
    assert result.primary_product.title == "Pedigree Adult Dry Dog Food 3kg"
    assert result.primary_product.price_text == "₹799"


def test_classify_cart_page() -> None:
    raw_data = {
        "url": "https://demo.nopcommerce.com/cart",
        "cart_item_count": "2 items",
    }

    result = classify_page_understanding(raw_data)

    assert result.page_type == PageType.CART
    assert result.cart_item_count == 2
    assert result.confidence >= 0.65


def test_classify_unknown_page() -> None:
    raw_data = {
        "mystery_flag": "1",
        "page_title": "untitled page",
    }

    result = classify_page_understanding(raw_data)

    assert result.page_type == PageType.UNKNOWN
    assert result.notes is not None
    assert result.confidence <= 0.40


def test_classify_blocked_page_keeps_unknown_with_low_confidence() -> None:
    raw_data = {
        "page_type": "access_denied",
        "blocked_page": True,
        "page_title": "Access Denied",
        "notes": "The demo store blocked the runtime browser session.",
    }

    result = classify_page_understanding(raw_data)

    assert result.page_type == PageType.UNKNOWN
    assert result.notes == "The demo store blocked the runtime browser session."
    assert result.confidence <= 0.10

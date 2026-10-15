import pytest
from django.core.exceptions import ValidationError

from apps.guests.validators import mask_document, normalize_document, normalize_phone, normalize_rut


@pytest.mark.parametrize(
    "value,expected",
    [
        ("12.345.678-5", "12345678-5"),
        ("123456785", "12345678-5"),
        (" 12345678-5 ", "12345678-5"),
        ("1.000.005-k", "1000005-K"),
        ("1000005K", "1000005-K"),
        ("1.000.013-0", "1000013-0"),
        ("01.000.005-K", "1000005-K"),
        ("1-9", "1-9"),
    ],
)
def test_rut_normalization_and_modulo_11(value, expected):
    assert normalize_rut(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "0-0",
        "12345678-9",
        "1000005-0",
        "1000013-K",
        "12345678",
        "12.34.5678-5",
        "12..345.678-5",
        "12345678--5",
        "ABC-1",
        "１２３４５６７８-５",
        "123456789-0",
        None,
        123456785,
    ],
)
def test_invalid_rut_rejected_without_echoing_identifier(value):
    with pytest.raises(ValidationError):
        normalize_rut(value)


def test_alternative_document_and_phone_do_not_require_chilean_rut():
    assert normalize_document("passport", " p-test-001 ") == "P-TEST-001"
    assert normalize_document("other", "id / test 99") == "ID / TEST 99"
    assert normalize_phone("+56 (9) 0000-0000") == "+56900000000"
    assert normalize_phone("") == ""
    assert mask_document("1-9") == "••••"
    assert "12345678-5" not in mask_document("12345678-5")


@pytest.mark.parametrize(
    "document_type,value",
    [("passport", "<script>"), ("other", "---"), ("other", "A\nB"), ("unknown", "123")],
)
def test_alternative_document_validation(document_type, value):
    with pytest.raises(ValidationError):
        normalize_document(document_type, value)

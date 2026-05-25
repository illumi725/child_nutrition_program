from core.parser import (
    calculate_match_score,
    clean_name,
    safe_float,
    split_beneficiary_name,
)


def test_split_beneficiary_name_comma_format():
    ln, fn, mn = split_beneficiary_name("DELA CRUZ, JUAN MIGUEL")
    assert ln == "DELA CRUZ"
    assert fn == "JUAN"
    assert mn == "MIGUEL"


def test_split_beneficiary_name_suffix():
    ln, fn, mn = split_beneficiary_name("JUAN DELA CRUZ JR")
    assert ln == "CRUZ"
    assert "JR" in fn
    assert "JUAN" in fn or "DELA" in fn


def test_split_compound_firstname_with_surname_dict():
    surname_dict = {"SANTOS"}
    ln, fn, mn = split_beneficiary_name("MARIA CLARA, ANA LUZ")
    ln2, fn2, mn2 = split_beneficiary_name(
        "MARIA CLARA, ANA LUZ", surname_dict=surname_dict
    )
    assert ln == ln2 == "MARIA CLARA"
    assert mn2 == ""


def test_calculate_match_score_exact():
    excel = {
        "lastname": "Dela Cruz",
        "firstname": "Juan",
        "middlename": "",
        "birthday": "2018-01-15",
    }
    db = {
        "lastname": "DELA CRUZ",
        "firstname": "JUAN",
        "middlename": "",
        "birthday": "2018-01-15",
    }
    score, match_type = calculate_match_score(excel, db)
    assert score >= 90
    assert match_type.lower() in ("exact", "fuzzy", "potential")


def test_safe_float_invalid():
    assert safe_float("not-a-number") is None
    assert safe_float(None) is None


def test_clean_name_strips_punctuation():
    assert clean_name("O'Brien, Pat.") == "O BRIEN PAT."

from core.password_utils import hash_access_code, is_hashed_access_code, verify_access_code


def test_hash_and_verify():
    hashed = hash_access_code("secret123")
    assert is_hashed_access_code(hashed)
    assert verify_access_code("secret123", hashed)
    assert not verify_access_code("wrong", hashed)


def test_legacy_plaintext_still_works():
    assert verify_access_code("plain", "plain")
    assert not is_hashed_access_code("plain")

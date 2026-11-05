import re


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    """Digits only, last 10 (drops +91 / leading 0) so formats compare equal."""
    return re.sub(r"\D", "", phone)[-10:]

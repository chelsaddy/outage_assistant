import re


def normalize_phone(raw: str) -> str:
    """Turn what a customer types ('868-555-1000', '555 1000') into E.164 (+18685551000).

    7 digits assume the Trinidad and Tobago area code; 10 digits assume country code 1.
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 7:
        digits = "1868" + digits
    elif len(digits) == 10:
        digits = "1" + digits
    return "+" + digits

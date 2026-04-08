import base64
import hashlib
import hmac

APP_ID = "R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv"
_APP_SECRET = "1ve5Qk9GXfUhKAn1svnKwpAlxXkMarru"


def sign_payload(msg: bytes) -> bytes:
    return hmac.new(_APP_SECRET.encode(), msg, hashlib.sha256).digest()


def build_phone_number(username: str, country_code: str) -> str:
    if username.startswith("+"):
        return username
    if username.startswith(country_code.lstrip("+")):
        return "+" + username
    return country_code + username

if __name__ == "__main__":
    from regions import REGIONS
    import base64
    encoded = base64.b64encode(str(REGIONS).encode())
    secret_map = "L8KDAMO6wpomxpYZwrHhu4AuEjQKBy8nwoMHNB7DmwoWwrvCsSYGw4wDAxs="
    key = bytes(encoded[ord(ch)] for ch in base64.b64decode(secret_map).decode())
    print(key.decode())  # ← 这就是 _APP_SECRET 的值
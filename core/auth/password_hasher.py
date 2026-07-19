import base64,hashlib,hmac,secrets

ITERATIONS=300000
PREFIX="pbkdf2_sha256"


def hash_password(password:str)->str:
    salt=secrets.token_bytes(32);digest=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),salt,ITERATIONS)
    return f"{PREFIX}${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password:str,stored_hash:str)->bool:
    try:
        algorithm,iterations,salt_text,digest_text=stored_hash.split("$",3)
        if algorithm!=PREFIX:return False
        actual=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),base64.b64decode(salt_text),int(iterations));return hmac.compare_digest(actual,base64.b64decode(digest_text))
    except Exception:return False


def needs_rehash(stored_hash:str)->bool:
    try:algorithm,iterations,_,_=stored_hash.split("$",3);return algorithm!=PREFIX or int(iterations)<ITERATIONS
    except Exception:return True

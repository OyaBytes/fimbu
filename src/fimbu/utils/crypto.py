"""
Oya's crypto functions and utilities.
"""
from __future__ import annotations
from typing import Sequence, cast
import hashlib
import hmac
import secrets
import base64
import asyncio

from fimbu.conf import settings
from fimbu.utils.encoding import force_bytes
from passlib.context import CryptContext



__all__ = ["PasswordManager"]


class PasswordManager:
    """Thin wrapper around `passlib`."""

    def __init__(self, hash_schemes: Sequence[str] | None = None) -> None:
        """Construct a PasswordManager.

        Args:
            hash_schemes: The encryption schemes to use. Defaults to ["argon2"].
        """
        if hash_schemes is None:
            hash_schemes = ["argon2"]
        self.context = CryptContext(schemes=hash_schemes, deprecated="auto")

    
    @staticmethod
    def get_encryption_key(secret: str) -> bytes:
        """Get Encryption Key.

        Args:
            secret (str): Secret key used for encryption

        Returns:
            bytes: a URL safe encoded version of secret
        """
        if len(secret) <= 32:
            secret = f"{secret:<32}"[:32]
        return base64.urlsafe_b64encode(secret.encode())


    async def get_password_hash(self, password: str | bytes) -> str:
        """Get password hash.

        Args:
            password: Plain password
        Returns:
            str: Hashed password
        """
        return await asyncio.get_running_loop().run_in_executor(None, self.context.hash, password)


    async def verify_password(self, plain_password: str | bytes, hashed_password: str) -> bool:
        """Verify Password.

        Args:
            plain_password (str | bytes): The string or byte password
            hashed_password (str): the hash of the password

        Returns:
            bool: True if password matches hash.
        """
        valid, _ = await asyncio.get_running_loop().run_in_executor(
            None,
            self.context.verify_and_update,
            plain_password,
            hashed_password,
        )
        return bool(valid)


    def verify_and_update(self, password: str, password_hash: str | None) -> tuple[bool, str | None]:
        """Verify a password and rehash it if the hash is deprecated.

        Args:
            password: The password to verify.
            password_hash: The hash to verify against.
        """
        return cast("tuple[bool, str | None]", self.context.verify_and_update(password, password_hash))



class InvalidAlgorithm(ValueError):
    """Algorithm is not supported by hashlib."""
    pass


def salted_hmac(key_salt, value, secret=None, *, algorithm="sha1"):
    """
    Return the HMAC of 'value', using a key generated from key_salt and a
    secret (which defaults to settings.SECRET_KEY). Default algorithm is SHA1,
    but any algorithm name supported by hashlib can be passed.

    A different key_salt should be passed in for every application of HMAC.
    """
    if secret is None:
        secret = settings.SECRET_KEY

    key_salt = force_bytes(key_salt)
    secret = force_bytes(secret)
    try:
        hasher = getattr(hashlib, algorithm)
    except AttributeError as e:
        raise InvalidAlgorithm(
            "%r is not an algorithm accepted by the hashlib module." % algorithm
        ) from e
    # We need to generate a derived key from our base key.  We can do this by
    # passing the key_salt and our base key through a pseudo-random function.
    key = hasher(key_salt + secret).digest()
    # If len(key_salt + secret) > block size of the hash algorithm, the above
    # line is redundant and could be replaced by key = key_salt + secret, since
    # the hmac module does the same thing for keys longer than the block size.
    # However, we need to ensure that we *always* do this.
    return hmac.new(key, msg=force_bytes(value), digestmod=hasher)


RANDOM_STRING_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def get_random_string(length, allowed_chars=RANDOM_STRING_CHARS):
    """
    Return a securely generated random string.

    The bit length of the returned value can be calculated with the formula:
        log_2(len(allowed_chars)^length)

    For example, with default `allowed_chars` (26+26+10), this gives:
      * length: 12, bit length =~ 71 bits
      * length: 22, bit length =~ 131 bits
    """
    return "".join(secrets.choice(allowed_chars) for i in range(length))


def constant_time_compare(val1, val2):
    """Return True if the two strings are equal, False otherwise."""
    return secrets.compare_digest(force_bytes(val1), force_bytes(val2))


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    """Return the hash of password using pbkdf2."""
    if digest is None:
        digest = hashlib.sha256
    dklen = dklen or None
    password = force_bytes(password)
    salt = force_bytes(salt)
    return hashlib.pbkdf2_hmac(digest().name, password, salt, iterations, dklen)


def get_random_secret_key(length:int):
    """
    Return a 50 character random string usable as a SECRET_KEY setting value.
    """
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    return get_random_string(length, chars)

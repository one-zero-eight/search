__all__ = ["TokenRepository"]

import time

from authlib.jose import JWTClaims
from authlib.jose import jwt, JoseError
from pydantic import BaseModel

from src.modules.innohassle_accounts import innohassle_accounts


class UserTokenData(BaseModel):
    innohassle_id: str


class TokenRepository:
    @classmethod
    def decode_token(cls, token: str) -> JWTClaims:
        now = time.time()
        pub_key = innohassle_accounts.get_public_key()
        payload = jwt.decode(token, pub_key)
        payload.validate_exp(now, leeway=0)
        payload.validate_iat(now, leeway=0)
        return payload

    @classmethod
    async def verify_user_token(cls, token: str, credentials_exception) -> UserTokenData:
        try:
            payload = cls.decode_token(token)
            innohassle_id: str = payload.get("uid")
            if innohassle_id is None:
                raise credentials_exception
            return UserTokenData(innohassle_id=innohassle_id)
        except JoseError:
            raise credentials_exception

    @classmethod
    def verify_parser_token(cls, token: str, credentials_exception) -> bool:
        try:
            payload = cls.decode_token(token)
            parser_data = payload.get("sub")
            if parser_data == "parser":
                return True
            raise credentials_exception
        except JoseError:
            raise credentials_exception

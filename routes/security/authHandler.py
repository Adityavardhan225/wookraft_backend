# from jose import JWTError, jwt
# from decouple import config
# import time

# JWT_SECRET = config('JWT_SECRET')
# JWT_ALGORITHM = config('JWT_ALGORITHM')
# ACCESS_TOKEN_EXPIRE_MINUTES = config('ACCESS_TOKEN_EXPIRE_MINUTES', cast=int)

# class AuthHandler():
#     invalidated_tokens = set()
#     @staticmethod
#     def sign_jwt(user_id : str) -> str:
#         payload = {
#             "user_id": user_id,
#             "expires": time.time() + ACCESS_TOKEN_EXPIRE_MINUTES
#         }

#         token=jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
#         return token
 

#     @staticmethod
#     def decode_jwt(token: str) -> dict:
#        print(f"token decode_jwt: {token}")
#        try:
#            decode_token = jwt.decode(token, JWT_SECRET, algorithms=JWT_ALGORITHM)
#            print(f"decode token: {decode_token}")
#            if decode_token["exp"] < time.time() or token in AuthHandler.invalidated_tokens:
#                  return None
#            return decode_token
#        except JWTError as e:
#            print("unable to decode token")
#            return None

#     @staticmethod
#     def invalidate_token(token: str):
#         AuthHandler.invalidated_tokens.add(token)

















from jose import JWTError, jwt
import os
import time

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')  # You can set a default here
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))  # Default 30 mins

class AuthHandler():
    invalidated_tokens = set()

    @staticmethod
    def sign_jwt(user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "expires": time.time() + ACCESS_TOKEN_EXPIRE_MINUTES
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def decode_jwt(token: str) -> dict:
        print(f"token decode_jwt: {token}")
        try:
            decode_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            print(f"decode token: {decode_token}")
            if decode_token["exp"] < time.time() or token in AuthHandler.invalidated_tokens:
                return None
            return decode_token
        except JWTError as e:
            print("unable to decode token")
            return None

    @staticmethod
    def invalidate_token(token: str):
        AuthHandler.invalidated_tokens.add(token)

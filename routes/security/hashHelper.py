from bcrypt import checkpw, gensalt, hashpw

class HashHelper:
    @staticmethod
    def hash_password(plain_password: str) -> str:
        return hashpw(plain_password.encode('utf-8'), gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8')):
            return True
        else:
            return False
        
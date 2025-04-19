from schema.user import UserInCreate
from pymongo.database import Database
from repository.base import BaseRepository
from fastapi import HTTPException

class UserRepository(BaseRepository):
    def __init__(self, db: Database):
        super().__init__(db)

    def create_user(self, user_data: UserInCreate, user_id: str) -> dict:
        new_user = user_data.model_dump(exclude_none=True)
        new_user['owner_id'] = user_id 
        result = self.db.users.insert_one(new_user)
        return new_user

    def user_exist_by_email(self, email: str) -> bool:
        return self.db.users.find_one({"email": email}) is not None

    def get_user_by_email(self, email: str):
         user=self.db.users.find_one({"email": email})
         if user:
              user['id'] = str(user['id'])
         return user
    

    def get_user_by_id(self, user_id: str) -> dict:
        user = self.db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user["id"] = str(user["id"])
        return user
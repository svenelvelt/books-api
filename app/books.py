from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.db import Database
from app.models import ObjectIdStr

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{book_id}")
async def get_book(db: Database, book_id: ObjectIdStr) -> dict:
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

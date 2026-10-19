from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.db import Database
from app.models import Book, ObjectIdStr

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{book_id}")
async def get_book(db: Database, book_id: ObjectIdStr) -> Book:
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return Book.model_validate(book)

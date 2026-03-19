from fastapi import FastAPI, Response, status
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# ---------------- DATA ---------------- #

books = [
    {"id": 1, "title": "Python Basics", "author": "John", "genre": "Tech", "is_available": True},
    {"id": 2, "title": "AI Guide", "author": "Smith", "genre": "Tech", "is_available": True},
    {"id": 3, "title": "History of India", "author": "Raj", "genre": "History", "is_available": True},
    {"id": 4, "title": "Science 101", "author": "David", "genre": "Science", "is_available": True},
    {"id": 5, "title": "Fiction Story", "author": "Alice", "genre": "Fiction", "is_available": True},
    {"id": 6, "title": "Data Structures", "author": "Bob", "genre": "Tech", "is_available": True},
]

borrow_records = []
queue = []

book_counter = 7
record_counter = 1

# ---------------- MODELS ---------------- #

class BorrowRequest(BaseModel):
    member_name: str = Field(min_length=2)
    book_id: int = Field(gt=0)
    borrow_days: int = Field(gt=0, le=30)
    member_id: str = Field(min_length=4)
    member_type: str = "regular"


class NewBook(BaseModel):
    title: str = Field(min_length=2)
    author: str = Field(min_length=2)
    genre: str = Field(min_length=2)
    is_available: bool = True


# ---------------- HELPERS ---------------- #

def find_book(book_id):
    for book in books:
        if book["id"] == book_id:
            return book
    return None


def calculate_due_date(days, member_type):
    if member_type == "premium":
        days = min(days, 60)
    return f"Return by Day {10 + days}"


# ---------------- DAY 1 ---------------- #

@app.get("/")
def home():
    return {"message": "Welcome to Library System"}


@app.get("/books")
def get_books():
    return {"total": len(books), "books": books}


@app.get("/books/summary")
def summary():
    available = sum(1 for b in books if b["is_available"])
    genres = {}
    for b in books:
        genres[b["genre"]] = genres.get(b["genre"], 0) + 1
    return {
        "total": len(books),
        "available": available,
        "borrowed": len(books) - available,
        "genres": genres
    }


# ---------------- FIXED ROUTES (IMPORTANT ORDER) ---------------- #

@app.get("/books/filter")
def filter_books(
    genre: Optional[str] = None,
    author: Optional[str] = None,
    is_available: Optional[bool] = None
):
    result = books

    if genre is not None:
        result = [b for b in result if b["genre"] == genre]

    if author is not None:
        result = [b for b in result if b["author"] == author]

    if is_available is not None:
        result = [b for b in result if b["is_available"] == is_available]

    return {"count": len(result), "books": result}


@app.get("/books/search")
def search(keyword: str):
    result = [
        b for b in books
        if keyword.lower() in b["title"].lower() or keyword.lower() in b["genre"].lower()
    ]
    return {"count": len(result), "books": result}


@app.get("/books/sort")
def sort_books(sort_by: str = "title", order: str = "asc"):
    reverse = order == "desc"
    return sorted(books, key=lambda x: x[sort_by], reverse=reverse)


@app.get("/books/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    total = len(books)
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "data": books[start:start + limit]
    }


@app.get("/books/browse")
def browse(
    keyword: Optional[str] = None,
    sort_by: str = "title",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = books

    # filter
    if keyword:
        result = [
            b for b in result
            if keyword.lower() in b["title"].lower()
        ]

    # sort
    reverse = order == "desc"
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    # pagination
    start = (page - 1) * limit
    return result[start:start + limit]


# ❗ ALWAYS KEEP VARIABLE ROUTE LAST
@app.get("/books/{book_id}")
def get_book(book_id: int):
    book = find_book(book_id)
    if not book:
        return {"error": "Book not found"}
    return book


@app.get("/borrow-records")
def get_records():
    return {"total": len(borrow_records), "records": borrow_records}


# ---------------- DAY 2 + 3 ---------------- #

@app.post("/borrow")
def borrow(req: BorrowRequest):
    global record_counter

    book = find_book(req.book_id)
    if not book:
        return {"error": "Book not found"}

    if not book["is_available"]:
        return {"error": "Book not available"}

    book["is_available"] = False

    record = {
        "record_id": record_counter,
        "member_name": req.member_name,
        "book_id": req.book_id,
        "due_date": calculate_due_date(req.borrow_days, req.member_type)
    }

    borrow_records.append(record)
    record_counter += 1

    return record


# ---------------- DAY 4 CRUD ---------------- #

@app.post("/books")
def add_book(new: NewBook, response: Response):
    global book_counter

    for b in books:
        if b["title"].lower() == new.title.lower():
            return {"error": "Duplicate book"}

    book = {
        "id": book_counter,
        **new.dict()
    }

    books.append(book)
    book_counter += 1

    response.status_code = status.HTTP_201_CREATED
    return book


@app.put("/books/{book_id}")
def update_book(book_id: int, genre: Optional[str] = None, is_available: Optional[bool] = None):
    book = find_book(book_id)
    if not book:
        return {"error": "Not found"}

    if genre is not None:
        book["genre"] = genre

    if is_available is not None:
        book["is_available"] = is_available

    return book


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    book = find_book(book_id)
    if not book:
        return {"error": "Not found"}

    books.remove(book)
    return {"message": "Deleted", "title": book["title"]}


# ---------------- DAY 5 WORKFLOW ---------------- #

@app.post("/queue/add")
def add_queue(member_name: str, book_id: int):
    book = find_book(book_id)

    if not book:
        return {"error": "Book not found"}

    if book["is_available"]:
        return {"message": "Book available"}

    queue.append({"member_name": member_name, "book_id": book_id})
    return {"message": "Added to queue"}


@app.get("/queue")
def get_queue():
    return queue


@app.post("/return/{book_id}")
def return_book(book_id: int):
    book = find_book(book_id)

    if not book:
        return {"error": "Not found"}

    book["is_available"] = True

    for q in queue:
        if q["book_id"] == book_id:
            queue.remove(q)
            return {"message": f"Assigned to {q['member_name']}"}

    return {"message": "Returned and available"}
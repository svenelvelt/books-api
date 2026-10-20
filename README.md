# Books API

[![CI](https://github.com/svenelvelt/books-api/actions/workflows/ci.yml/badge.svg)](https://github.com/svenelvelt/books-api/actions/workflows/ci.yml)

A REST API for books and their authors, built with FastAPI and MongoDB: CRUD with validation, pagination and filtering, plus author and publisher statistics built on MongoDB aggregations.

Built with Python 3.13, FastAPI, MongoDB 8 (async PyMongo), Pydantic and uv.

## Running

```bash
docker compose up -d --build                # MongoDB + API
docker compose exec api python -m app.seed  # optional: load sample data
```

The API runs at http://localhost:8000, with interactive docs at http://localhost:8000/docs. Stop it with `docker compose down`, adding `-v` to also delete the data.

### Without Docker

With [uv](https://docs.astral.sh/uv/) and a MongoDB on `localhost:27017` (e.g. `docker compose up -d mongodb`):

```bash
uv sync
uv run uvicorn app.main:app --reload
```

| Environment variable | Default | Purpose |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017` | Connection string |
| `MONGODB_DATABASE` | `books` | Database name |
| `MONGODB_TIMEOUT_MS` | `5000` | How long to wait for MongoDB before failing |

## Database

No setup is needed: the API creates its indexes on startup. `python -m app.seed` loads two sample books and their three authors, and only runs against an empty database, so it never changes existing data.

Timestamps are stored and returned in UTC, so a sample time of `2017-01-12T00:00:00+03:00` is returned as `2017-01-11T21:00:00Z`.

## Endpoints

| Method | Path | Description | Success |
|---|---|---|---|
| `GET` | `/books` | List books (paginated, filterable) | 200 |
| `POST` | `/books` | Create a book | 201 |
| `GET` | `/books/{id}` | Get a book | 200 |
| `PATCH` | `/books/{id}` | Update some fields of a book | 200 |
| `DELETE` | `/books/{id}` | Delete a book | 204 |
| `GET` | `/authors` | List authors with their `book_count` (paginated) | 200 |
| `POST` | `/authors` | Create an author | 201 |
| `GET` | `/authors/{id}` | Get an author | 200 |
| `GET` | `/authors/{id}/books` | List an author's books (paginated) | 200 |
| `GET` | `/publishers/{publisher_name}/average_pages` | Average pages of a publisher's books | 200 |
| `GET` | `/health/live` | The process is up (does not check MongoDB) | 200 |
| `GET` | `/health/ready` | MongoDB is reachable | 200 / 503 |

- Pagination uses `page` (default 1) and `limit` (1 to 100, default 20), ordered by creation. Lists return `{"items": [...], "total", "page", "limit"}`.
- `GET /books` filters: `title` and `author` are case-insensitive substring matches. `publisher` must match exactly, as in `average_pages`. `tags` can be repeated, and a book must have all of them: `?tags=Python&tags=Learning`.
- Creates return `201` with a `Location` header pointing to the new resource.

### Examples

Ids are 24-character strings. A book lists its authors by id in `author_ids` (not as an `author` name string), so create the author first:

```bash
curl -X POST localhost:8000/authors -H 'Content-Type: application/json' \
  -d '{"name": "Luciano Ramalho"}'
```
```json
{"id": "6ad69c1bf11c623ca40b477e", "name": "Luciano Ramalho", "birth_date": null}
```

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Fluent Python", "publisher": "O'\''Reilly Media",
       "author_ids": ["6ad69c1bf11c623ca40b477e"], "pages": 1012, "tags": ["Python"]}'
```
```json
{
  "id": "6ad69c1bf11c623ca40b477f",
  "title": "Fluent Python",
  "publisher": "O'Reilly Media",
  "authors": [{"id": "6ad69c1bf11c623ca40b477e", "name": "Luciano Ramalho"}],
  "pages": 1012,
  "tags": ["Python"],
  "created_at": "2026-10-19T22:39:23.403000Z",
  "updated_at": "2026-10-19T22:39:23.403000Z"
}
```

The remaining examples assume the sample data is loaded.

Getting, updating and deleting a book:

```bash
curl localhost:8000/books/{id}            # 200 with the book, 404 if there is none
curl -X PATCH localhost:8000/books/{id} -H 'Content-Type: application/json' \
  -d '{"pages": 1014}'                     # 200 with the full book; only pages and updated_at change
curl -X DELETE localhost:8000/books/{id}  # 204, no body
```

Listing, paginating and filtering books. Each returns a page, `{"items": [...], "total", "page", "limit"}`:

```bash
curl 'localhost:8000/books?page=1&limit=1'             # first book of 2, total: 2
curl 'localhost:8000/books?author=Mark&title=Learning' # "Learning Python"
curl 'localhost:8000/books?tags=Python&tags=Learning'  # "Learning Python": it has both tags
curl "localhost:8000/books?publisher=O'Reilly%20Media"  # both sample books
```

An author's books come back in the same page shape, or 404 if the author does not exist:

```bash
curl localhost:8000/authors/{author_id}/books
```

Authors with their book count:

```bash
curl 'localhost:8000/authors?limit=2'
```
```json
{
  "items": [
    {"id": "6ad69988f74363310e2f1bf9", "name": "Mark Lutz", "birth_date": null, "book_count": 1},
    {"id": "6ad69988f74363310e2f1bfa", "name": "Harry Percival", "birth_date": null, "book_count": 1}
  ],
  "total": 3,
  "page": 1,
  "limit": 2
}
```

Average pages for a publisher. The name must match exactly and is URL-encoded:

```bash
curl "localhost:8000/publishers/O'Reilly%20Media/average_pages"
```
```json
{"publisher": "O'Reilly Media", "average_pages": 976.0}
```

### Errors

All errors share one shape: a machine-readable `code`, a `detail` message, and for validation failures an `errors` list naming each field.

```json
{
  "code": "validation_error",
  "detail": "Request validation failed",
  "errors": [
    {"loc": ["body", "title"], "msg": "String should have at least 1 character"},
    {"loc": ["body", "pages"], "msg": "Input should be greater than 0"}
  ]
}
```

| Status | `code` | When |
|---|---|---|
| 404 | `book_not_found`, `author_not_found`, `publisher_not_found` | The resource in the URL does not exist |
| 422 | `validation_error` | Invalid body, path or query parameter |
| 422 | `unknown_authors` | `author_ids` refers to authors that do not exist |
| 503 | `database_unavailable` | MongoDB cannot be reached |
| 500 | `internal_error` | Unexpected error, details are only logged |

### Validation

Text fields are trimmed and must be 1 to 500 characters; `pages` must be an integer from 1 to 100,000; `author_ids` needs at least one id and no duplicates; `birth_date` cannot be in the future. Unknown fields are rejected, including the server-managed `id`, `created_at` and `updated_at`. `PATCH` needs at least one field, and sent fields must not be `null`.

## Testing

The tests need a MongoDB on `localhost:27017`. They use a separate `books_test` database, which is dropped after the run.

```bash
uv sync
uv run pytest              # all tests
uv run pytest --cov        # with a coverage report; fails below 95%
uv run pytest tests/unit   # unit tests only, no MongoDB needed
uv run ruff check . && uv run ruff format --check .
```

Unit tests cover the request models and the filter builder. Integration tests call every endpoint against a real MongoDB, including error cases, aggregations, indexes, seeding and database outages.

Coverage is about 98%; the only untested lines are the seed command's command-line wrapper. CI runs the tests with coverage, fails if it drops below 95%, and adds the report to each run's summary page.

## CI and production

GitHub Actions runs the linters, the tests against a MongoDB service container, a Docker build and the Terraform checks (`fmt` and `validate`) on every push and pull request. Pushes to `main` are deployed to AWS once the infrastructure exists.

[`terraform/`](terraform/README.md) defines the production setup: ECS Fargate behind an Application Load Balancer, and MongoDB Atlas over PrivateLink, with the tasks signing in to the database through their IAM role. Its README explains the decisions and how to deploy.

## Design decisions

- Ids are ObjectIds. They only need to be unique, and ObjectIds are generated by the driver without coordination. An integer counter would add a write to a single counter document on every insert.
- Authors are embedded in books as references. Each book stores `authors: [{"id", "name"}]`, MongoDB's extended reference pattern. Clients send `author_ids`, and the server copies the names. Filtering by author, an author's books and `book_count` then all read only the `books` collection, using an index. The cost is one indexed lookup per write, and renaming an author would mean updating their books.
- `GET /authors` paginates the authors first, then counts each one's books with a `$lookup` and `$count`, so book documents are never loaded and authors without books show `0`. `average_pages` is a `$match` and `$avg`.
- The indexes are compound: `authors.id`, `publisher` or `tags`, each followed by `_id`. List queries filter on one of those fields and page in `_id` order, so the index returns a page already sorted, instead of MongoDB fetching every match and sorting it in memory. Tests check the query plans with `explain`. Publisher and tags are matched exactly so the indexes apply. The `title` and `author` substring filters cannot use a normal index; at scale they would move to a search index.
- Liveness never touches MongoDB, so an outage does not get healthy containers restarted. Readiness reports MongoDB for load-balancer routing.
- The structure is flat: one module per resource, with routes querying MongoDB directly and no repository or service layers.

Out of scope: updating and deleting authors, authentication, and cursor-based pagination.

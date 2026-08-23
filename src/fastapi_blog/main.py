from fastapi import FastAPI, HTTPException, status

from fastapi_blog.schema import PostCreate, PostResponse

app = FastAPI()

posts = [
    {
        "id": "1",
        "title": "Title 1",
        "content": "Content 1",
        "created_at": "23 Aug 2026",
    },
    {
        "id": "2",
        "title": "Title 2",
        "content": "Content 2",
        "created_at": "23 Aug 2026",
    },
    {
        "id": "3",
        "title": "Title 3",
        "content": "Content 3",
        "created_at": "23 Aug 2026",
    },
    {
        "id": "4",
        "title": "Title 4",
        "content": "Content 4",
        "created_at": "23 Aug 2026",
    },
    {
        "id": "5",
        "title": "Title 5",
        "content": "Content 5",
        "created_at": "23 Aug 2026",
    },
]


@app.get("/")
def main() -> dict:
    return {"status": "OK"}


@app.get("/api/posts", response_model=list[PostResponse])
def get_all_posts():
    return posts


@app.get("/api/posts/{id}")
def get_post(id: str):

    for post in posts:
        if post["id"] == id:
            return post

    raise HTTPException(status_code=404, detail="Post Not Found")


@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
def create_post(post: PostCreate):
    new_id = len(posts) + 1
    new_post = {
        "id": str(new_id),
        "title": post.title,
        "content": post.content,
        "created_at": "24 Aug 2026",
    }

    posts.append(new_post)

    return new_post

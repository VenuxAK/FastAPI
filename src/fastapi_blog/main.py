from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

# from fastapi.exception_handlers import (
#     http_exception_handler,
#     request_validation_exception_handler,
# )
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# from starlette.exceptions import HTTPException as StarletteHTTPException
import fastapi_blog.models
from fastapi_blog.database import Base, engine, get_db
from fastapi_blog.schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)

# Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# @app.exception_handlers(StarletteHTTPException)
# def general_http_exception_handler(request: Request)


@app.get("/")
def main() -> dict:
    return {"status": "OK"}


################ User #######################


# Create new user
@app.post(
    "/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Validate username
    result = await db.execute(
        Select(fastapi_blog.models.User).where(
            fastapi_blog.models.User.username == user.username
        )
    )
    existing_username = result.scalars().first()
    if existing_username:
        raise HTTPException(status_code=422, detail="Username already taken.")

    # Validate email
    result = await db.execute(
        Select(fastapi_blog.models.User).where(
            fastapi_blog.models.User.email == user.email
        )
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=422, detail="Email already taken.")

    new_user = fastapi_blog.models.User(username=user.username, email=user.email)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# Get user by id
@app.get(
    "/api/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK
)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(status_code=404, detail="User not found")


# Get user's posts
@app.get(
    "/api/users/{user_id}/posts",
    response_model=list[PostResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        Select(fastapi_blog.models.Post)
        .where(fastapi_blog.models.Post.user_id == user.id)
        .options(selectinload(fastapi_blog.models.Post.author))
    )

    posts = result.scalars().all()

    return posts


# Get user's post by post id
@app.get(
    "/api/users/{user_id}/posts/{post_id}", response_model=PostResponse, status_code=200
)
async def get_user_post(
    user_id: int, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(404, detail="Post not found")

    result = await db.execute(
        Select(fastapi_blog.models.Post)
        .where(
            fastapi_blog.models.Post.id == post_id
            and fastapi_blog.models.Post.user_id == user_id
        )
        .options(selectinload(fastapi_blog.models.Post.author))
    )

    post = result.scalars().first()

    return post


# Update user profile
@app.patch(
    "/api/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_user_profile(
    user_id: int, data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if data.email is not None and user.email != data.email:
        result = await db.execute(
            Select(fastapi_blog.models.User).where(
                fastapi_blog.models.User.email == data.email
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(status_code=400)

    if data.username is not None and user.username != data.username:
        result = await db.execute(
            Select(fastapi_blog.models.User).where(
                fastapi_blog.models.User.username == data.username
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(status_code=400)

    if data.email is not None:
        user.email = data.email
    if data.username is not None:
        user.username = data.username
    if data.image_file is not None:
        user.image_file = data.image_file

    await db.commit()
    await db.refresh(user)
    return user


# Delete user profile
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_profile(
    user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.posts:
        raise HTTPException(400, "User cannot be deleted")

    await db.delete(user)
    await db.commit()


################ Post #######################


# Get Posts
@app.get(
    "/api/posts", response_model=list[PostResponse], status_code=status.HTTP_200_OK
)
async def get_all_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(fastapi_blog.models.Post).options(
            selectinload(fastapi_blog.models.Post.author)
        )
    )
    posts = result.scalars().all()

    return posts


# Get Post by id
@app.get(
    "/api/posts/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK
)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        Select(fastapi_blog.models.Post)
        .where(fastapi_blog.models.Post.id == int(post_id))
        .options(selectinload(fastapi_blog.models.Post.author))
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(status_code=404, detail="Post Not Found")

    return post


# Create new post
@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        Select(fastapi_blog.models.User).where(
            fastapi_blog.models.User.id == post.user_id
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    new_post = fastapi_blog.models.Post(
        title=post.title, content=post.content, user_id=post.user_id
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    return new_post


# Update post
@app.put(
    "/api/posts/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_post(
    post_id: int, data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    if data.user_id != post.user_id:
        raise HTTPException(401, detail="Forbidden")

    post.title = data.title
    post.content = data.content

    await db.commit()
    await db.refresh(post)
    return post


# Update partial post data
@app.patch(
    "/api/posts/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_partial_data_post(
    post_id: int, data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    if data.user_id != post.user_id:
        raise HTTPException(401, detail="Forbidden")

    updated_data = data.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(post, key, value)

    await db.commit()
    await db.refresh(post)
    return post


# Delete post
@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    await db.delete(post)
    await db.commit()

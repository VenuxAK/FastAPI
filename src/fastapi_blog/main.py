from contextlib import asynccontextmanager

# from typing import Annotated
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fastapi_blog.database import Base, engine
from fastapi_blog.routers import posts, users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(posts.router, prefix="/api", tags=["posts"])


@app.get("/")
def main() -> dict:
    return {"status": "OK"}

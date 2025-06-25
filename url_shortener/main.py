from fastapi import FastAPI
from api_v1.users.views import router as users_router
from api_v1.urls.views import router as urls_router, public_router

app = FastAPI(
    title="URL Shortener API",
)

app.include_router(users_router, prefix="/api/v1")
app.include_router(urls_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "URL Shortener API", 
    }
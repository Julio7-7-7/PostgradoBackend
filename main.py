from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import all_routers
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from scheduler import iniciar, detener


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar()
    yield
    detener()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in all_routers:
    app.include_router(router)

MEDIA_ROOT = Path(__file__).parent / "media"
MEDIA_ROOT.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")

@app.get("/")
def root():
    return {"message": "API Posgrado funcionando ✅"}
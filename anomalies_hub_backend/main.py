import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.anomalies import router as anomalies_router
from api.pipeline import router as pipeline_router


load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="FraudOps Hub API", description="Backend para o painel de prevenção a fraudes.")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"], 
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(anomalies_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
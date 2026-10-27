from fastapi import FastAPI

app = FastAPI(title="OpsIntel AI Service")


@app.get("/health")
def health():
    return {"status": "UP", "service": "ai-service"}
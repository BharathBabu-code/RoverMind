from fastapi import FastAPI

app = FastAPI(
    title="RoverMind API",
    version="0.1.0",
    description="Backend foundation for the RoverMind AI-assisted planetary exploration prototype."
)

@app.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    """
    Diagnostic endpoint to verify the API server is operational.
    Does not depend on or expose sensitive external configurations.
    """
    return {
        "status": "ok",
        "service": "RoverMind API"
    }
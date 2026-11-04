from fastapi import APIRouter, HTTPException
from backend.app.schemas.models import FullAnalysisRequest, FullAnalysisResponse
from backend.app.services.analysis_orchestrator import run_full_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=FullAnalysisResponse)
async def analyze_image(request: FullAnalysisRequest) -> FullAnalysisResponse:
    """
    Executes visual segmentation, terrain-risk costmap generation,
    and A* path planning on the specified image.
    """
    try:
        return run_full_analysis(request)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Planetary analysis pipeline encountered an internal server error.")

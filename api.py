from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from workflow import create_review_workflow
from state import ReviewState
import asyncio
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReviewRequest(BaseModel):
    repository_url: str

class ReviewResponse(BaseModel):
    report: Dict[str, Any]

@app.post("/review", response_model=ReviewResponse)
async def review_endpoint(request: ReviewRequest):
    try:
        # Initialize state
        state = ReviewState(messages=[], repository_url=request.repository_url, analysis_results=None, current_step="start_review", error_message=None)
        # Create workflow
        workflow = create_review_workflow()
        # Run workflow asynchronously and get the final state
        final_state = await workflow.arun(state)
        # Return the analysis results from the final state
        return {"report": final_state.get("analysis_results", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from model_wrapper import CustomQwen2_5VL_VLLM_Model

app = FastAPI(title="UI-Ins Service")
model_wrapper = CustomQwen2_5VL_VLLM_Model()

class GroundingRequest(BaseModel):
    instruction: str
    base64_image: str

class GroundingResponse(BaseModel):
    point: list | None # [x_norm, y_norm]
    raw_response: str

@app.on_event("startup")
async def startup_event():
    model_wrapper.load_model()

@app.post("/ground", response_model=GroundingResponse)
async def ground_endpoint(req: GroundingRequest):
    try:
        result = model_wrapper.ground(req.instruction, req.base64_image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
import os
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class EarthquakeRequest(BaseModel):
    start_date: str
    end_date: str

@app.post("/api/proxy")
async def proxy_to_lambda(earthquake_request: EarthquakeRequest):
    """Proxy requests to your API Gateway Lambda"""
    try:
        api_key = os.environ.get('API_GATEWAY_KEY')
        api_url = os.environ.get('API_GATEWAY_URL')
        
        if not api_key:
            raise HTTPException(status_code=500, detail="API key not configured")
        if not api_url:
            raise HTTPException(status_code=500, detail="API Gateway URL not configured")
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
        
        request_body = {
            'start_date': earthquake_request.start_date,
            'end_date': earthquake_request.end_date
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, json=request_body, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"API Gateway error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Mount static assets
if os.path.exists("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

# Serve React app
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str = ""):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    return FileResponse("dist/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
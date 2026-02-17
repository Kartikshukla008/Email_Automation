from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import csv
import io
import uuid
import os

from .scraper import crawl_site
from .redis_service import send_to_queue, set_campaign_pending, get_campaign_pending, decrement_campaign_pending
from .database import init_db
from .worker import start_worker
from .maps import scrape_google_maps_task

app = FastAPI(title="Email Outreach System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CampaignRequest(BaseModel):
    url: str
    subject: Optional[str] = None
    message: Optional[str] = None

class SendRequest(BaseModel):
    campaign_id: str
    subject: str
    template: str
    emails: List[str]

class CampaignResponse(BaseModel):
    id: str
    status: str
    extracted_count: Optional[int] = 0

class BatchCampaignResponse(BaseModel):
    campaigns: List[Dict[str, str]] # [{'id': '...', 'url': '...'}]

class MapsRequest(BaseModel):
    query: str
    limit: int

# In-memory storage (in prod use Redis/DB)
campaign_status = {}
campaign_results = {}
maps_tasks = {}

@app.on_event("startup")
async def startup_event():
    await init_db()
    # Start worker in background task for demo simplicity
    # In production, run worker.py as separate service
    asyncio.create_task(start_worker())

async def run_campaign_logic(campaign_id: str, req: CampaignRequest):
    print(f"[{campaign_id}] Starting scrape for {req.url}")
    campaign_status[campaign_id] = "Scraping"
    
    try:
        data = await crawl_site(req.url, max_pages=15)
        emails = data["emails"]
        metadata = data["metadata"]
        
        print(f"[{campaign_id}] Found {len(emails)} valid emails from {metadata['title']}")
        
        campaign_results[campaign_id] = {
            "metadata": metadata,
            "emails": emails,
            "original_request": req.dict()
        }
        
        campaign_status[campaign_id] = "Scraped"
        
    except Exception as e:
        print(f"[{campaign_id}] Error: {e}")
        campaign_status[campaign_id] = "Failed"

@app.post("/api/campaign", response_model=CampaignResponse)
async def start_campaign(req: CampaignRequest, background_tasks: BackgroundTasks):
    campaign_id = str(uuid.uuid4())
    campaign_status[campaign_id] = "Pending"
    
    background_tasks.add_task(run_campaign_logic, campaign_id, req)
    
    return {"id": campaign_id, "status": "started", "extracted_count": 0}

@app.post("/api/upload-csv", response_model=BatchCampaignResponse)
async def upload_csv(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    contents = await file.read()
    decoded = contents.decode('utf-8')
    buffer = io.StringIO(decoded)
    csv_reader = csv.reader(buffer)
    
    urls = []
    # Try to find URLs in the first column or any column containing http
    for row in csv_reader:
        for cell in row:
            if cell.strip().lower().startswith("http"):
                urls.append(cell.strip())
                break
    
    if not urls:
        raise HTTPException(status_code=400, detail="No valid URLs found in CSV")
        
    initiated_campaigns = []
    
    for url in urls:
        campaign_id = str(uuid.uuid4())
        
        campaign_status[campaign_id] = "Pending"
        req = CampaignRequest(url=url)
        
        background_tasks.add_task(run_campaign_logic, campaign_id, req)
        
        initiated_campaigns.append({
            "id": campaign_id,
            "url": url,
            "status": "Pending"
        })
        
    return {"campaigns": initiated_campaigns}

@app.get("/api/status")
async def get_status():
    for cid, status in list(campaign_status.items()):
        if status == "Sending":
            remaining = await get_campaign_pending(cid)
            if remaining <= 0:
                campaign_status[cid] = "Completed"
    return campaign_status

@app.get("/api/campaign/{campaign_id}/results")
async def get_campaign_results(campaign_id: str):
    if campaign_id not in campaign_results:
        if campaign_id in campaign_status:
             return {"status": campaign_status[campaign_id], "emails": [], "metadata": {}}
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign_results[campaign_id]

@app.post("/api/send")
async def send_emails(req: SendRequest):
    campaign_id = req.campaign_id
    
    # Initialize pending count
    await set_campaign_pending(campaign_id, len(req.emails))
    campaign_status[campaign_id] = "Sending"
    
    count = 0
    for email in req.emails:
        payload = {
            "email": email,
            "subject": req.subject,
            "template": req.template,
            "campaign_id": campaign_id
        }
        sent = await send_to_queue(payload)
        if sent:
            count += 1
        else:
            print(f"Failed to queue email for campaign {campaign_id}")
            await decrement_campaign_pending(campaign_id)
        
    return {"status": "queued", "count": count}

# ============================================
# MAPS SCRAPER ENDPOINTS
# ============================================

async def run_maps_task(task_id: str, query: str, limit: int, output_file: str):
    if task_id in maps_tasks:
        maps_tasks[task_id]["status"] = "Running"
    try:
        await scrape_google_maps_task(query, limit, output_file)
        if task_id in maps_tasks:
            maps_tasks[task_id]["status"] = "Completed"
    except Exception as e:
        print(f"Maps Task Failed: {e}")
        if task_id in maps_tasks:
            maps_tasks[task_id]["status"] = "Failed"

@app.post("/api/maps/scrape")
async def start_maps_scrape(req: MapsRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    output_path = f"maps_{task_id}.csv"
    
    maps_tasks[task_id] = {
        "status": "Pending",
        "query": req.query
    }
    
    background_tasks.add_task(run_maps_task, task_id, req.query, req.limit, output_path)
    
    return {"task_id": task_id, "status": "started"}

@app.get("/api/maps/status/{task_id}")
async def get_maps_status(task_id: str):
    task = maps_tasks.get(task_id)
    if not task:
        return {"task_id": task_id, "status": "Not Found"}
    return {"task_id": task_id, "status": task["status"]}

@app.get("/api/maps/results/{task_id}")
async def get_maps_results(task_id: str):
    task = maps_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "Completed":
        return {"results": []}

    results = []
    output_path = f"maps_{task_id}.csv"

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(row)
        except Exception as e:
            print(f"Error reading CSV: {e}")

    return {"results": results}

@app.get("/api/maps/download/{task_id}")
async def download_maps_csv(task_id: str):
    task = maps_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    output_path = f"maps_{task_id}.csv"
    query_slug = task["query"].replace(" ", "_").lower()
    filename = f"{query_slug}_leads.csv"

    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(output_path, media_type='text/csv', filename=filename)

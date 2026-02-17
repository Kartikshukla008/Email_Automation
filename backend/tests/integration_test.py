
import asyncio
import aiohttp
from aiohttp import web
import socket
import csv
import io
import time
import requests

# 1. Setup Mock Server
async def handle_root(request):
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>Here is an email: test_user@mysite.com</p>
            <a href="mailto:another_user@mysite.com">Contact Us</a>
        </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_mock_server():
    app_server = web.Application()
    app_server.router.add_get('/', handle_root)
    runner = web.AppRunner(app_server)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 9090)
    await site.start()
    print("Mock server started at http://localhost:9090")
    return runner

# 2. Main Logic to Upload and Verify
async def run_integration_test():
    runner = await start_mock_server()
    
    API_BASE = "http://localhost:8000"
    
    # Create CSV
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["URL"])
    writer.writerow(["http://localhost:9090"])
    csv_content = csv_buffer.getvalue()
    
    print("\n[Uploaded CSV Content]")
    print(csv_content)
    
    # Upload CSV
    print("\n[Step 1] Uploading CSV...")
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/api/upload-csv", data={'file': io.BytesIO(csv_content.encode())}) as resp:
            if resp.status != 200:
                print(f"Error uploading CSV: {resp.status} - {await resp.text()}")
                return
            
            data = await resp.json()
            campaigns = data.get("campaigns", [])
            if not campaigns:
                print("No campaigns created!")
                return
                
            campaign_id = campaigns[0]["id"]
            print(f"Campaign ID: {campaign_id}")
            
        # Poll for completion
        print("\n[Step 2] Waiting for scraping to complete...")
        found_emails = []
        for _ in range(10): # Try for 10 seconds
            async with session.get(f"{API_BASE}/api/campaign/{campaign_id}/results") as resp:
                if resp.status == 200:
                    status_data = await resp.json()
                    # status_data could be results dict directly if scraped, let's see api.
                    # api says: if status checking returns "Scraped", it returns dict with 'emails', else returns {'status': ...}
                    
                    # BUT main.py:
                    # if campaign_id not in campaign_results:
                    #    if (in campaign_status) return {status: ..., emails: [], ...}
                    # else return campaign_results[campaign_id] which has 'emails' list.
                    
                    if "emails" in status_data and status_data["emails"]:
                        found_emails = status_data["emails"]
                        print(f"Scraping complete! Found emails: {found_emails}")
                        break
                    
                    # Also check status if it's there
                    status = status_data.get("status")
                    if status:
                         print(f"Current status: {status}")
                         
                await asyncio.sleep(1)
        
        if not found_emails:
            print("Failed to find emails in time.")
            return

        # Send Emails
        print("\n[Step 3] Sending emails...")
        payload = {
            "campaign_id": campaign_id,
            "subject": "Integration Test Subject",
            "template": "Hello, this is a test email.",
            "emails": found_emails
        }
        
        async with session.post(f"{API_BASE}/api/send", json=payload) as resp:
            if resp.status == 200:
                send_resp = await resp.json()
                print(f"Send initiated: {send_resp}")
            else:
                print(f"Error sending emails: {resp.status} - {await resp.text()}")

    # Clean up
    await runner.cleanup()
    print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(run_integration_test())

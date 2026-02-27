import re
import asyncio
import aiohttp # type: ignore
import ssl
from bs4 import BeautifulSoup # type: ignore
from urllib.parse import urljoin, urlparse, unquote
from email_validator import validate_email, EmailNotValidError

SAFE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Upgrade-Insecure-Requests': '1'
}

# Improved regex to catch more cases but avoid common false positives
email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+(?:\s*@\s*|\s+at\s+)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def decode_cf_email(cf_r):
    """Decode Cloudflare obfuscated email string"""
    email = ""
    r = int(cf_r[:2], 16)
    for i in range(2, len(cf_r), 2):
        c = int(cf_r[i:i+2], 16) ^ r
        email += chr(c)
    return email

async def extract_emails_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    emails = set()
    
    # 1. Regex search in visible text
    text_content = soup.get_text(separator=' ')
    raw_matches = email_pattern.findall(text_content)
    
    for match in raw_matches:
        # Normalize obfuscated emails like "user at example.com"
        decoded_match = unquote(match)
        clean_email = decoded_match.replace(' at ', '@').replace(' ', '')
        emails.add(clean_email)

    # 2. Check 'mailto:' links specifically
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().startswith('mailto:'):
            # Extract email from mailto:user@example.com?subject=...
            parts = href.split(':')
            if len(parts) > 1:
                potential_email = parts[1].split('?')[0].strip()
                potential_email = unquote(potential_email).strip()
                emails.add(potential_email)
    
    # 3. Check for Cloudflare protected emails
    # Pattern 1: <a href="/cdn-cgi/l/email-protection#...">
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/cdn-cgi/l/email-protection#' in href:
            cf_hash = href.split('#')[-1]
            try:
                decoded = decode_cf_email(cf_hash)
                emails.add(decoded)
            except Exception:
                pass
                
    # Pattern 2: <span class="__cf_email__" data-cfemail="...">
    for span in soup.find_all(attrs={"data-cfemail": True}):
        try:
            cf_hash = span['data-cfemail']
            decoded = decode_cf_email(cf_hash)
            emails.add(decoded)
        except Exception:
            pass

    return emails   

async def validate_single_email(email):
    # 1. Syntax check
    try:
        valid = validate_email(email, check_deliverability=False) # DNS check can be slow/blocking
        email_normalized = valid.email
    except EmailNotValidError:
        return None
        
    # 2. Domain check (simple blacklist)
    try:
        domain = email_normalized.split('@')[1]
        if domain in ['example.com', 'test.com', 'sentry.io', 'greensock.com', 'w3.org', 'reactjs.org', 'cloudflare.com', 'google.com']:
            return None
        
        # exclude image/font files that regex mistakes for emails (e.g. image@2x.png)
        if email_normalized.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.woff', '.woff2', '.ttf', '.css', '.js')):
            return None
            
        return email_normalized
    except IndexError:
        return None

async def fetch_and_scan_js(session, url, script_urls):
    """Fetch JS files and scan for emails concurrently"""
    emails = set()
    domain = urlparse(url).netloc
    
    # Deduplicate and filter safely
    valid_urls = set()
    for script_url in script_urls:
        full_url = urljoin(url, script_url)
        parsed_script = urlparse(full_url)
        # Scan same domain + potentially CDNs if needed, but sticking to same domain for speed safety
        # Allow subdomains
        script_netloc = parsed_script.netloc
        if script_netloc and script_netloc != domain and not script_netloc.endswith('.' + domain):
            continue
        valid_urls.add(full_url)
    
    if not valid_urls:
        return emails

    # Define fetcher
    async def fetch_js(js_url):
        try:
            async with session.get(js_url, timeout=5) as response:
                if response.status == 200:
                    text = await response.text()
                    # Use regex directly on JS code
                    raw_matches = email_pattern.findall(text)
                    js_emails = set()
                    for match in raw_matches:
                        decoded = unquote(match)
                        clean_email = decoded.replace(' at ', '@').replace(' ', '')
                        js_emails.add(clean_email)
                    return js_emails
        except Exception:
            pass
        return set()

    # Run all JS fetches in parallel
    results = await asyncio.gather(*[fetch_js(u) for u in valid_urls])
    
    for res in results:
        emails.update(res)
        
    return emails

async def _process_page_worker(session, url, domain, extract_metadata=False):
    """
    Process a single URL: Fetch, Extract Emails, Find Links
    Returns: (emails_set, priority_links, other_links, metadata_dict or None)
    """
    found_emails = set()
    priority_links = []
    other_links = []
    metadata = None

    print(f"Crawling: {url}")
    
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                print(f"Failed to fetch {url}: Status {response.status}")
                return set(), [], [], None
            
            text = await response.text()
            final_url = str(response.url) # Update URL in case of redirects
            soup = BeautifulSoup(text, 'html.parser')

            # Extract metadata if needed
            if extract_metadata:
                metadata = {}
                title_tag = soup.find('title')
                metadata["title"] = title_tag.string.strip() if title_tag else ""
                
                meta_desc = soup.find('meta', attrs={"name": "description"})
                if not meta_desc:
                    meta_desc = soup.find('meta', attrs={"property": "og:description"})
                metadata["description"] = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ""

            # Extract Emails from HTML
            page_emails = await extract_emails_from_html(text)
            
            # SPA Fallback: Check for scripts
            script_tags = soup.find_all('script', src=True)
            script_urls = [s['src'] for s in script_tags]
            
            if script_urls:
                js_emails = await fetch_and_scan_js(session, final_url, script_urls)
                page_emails.update(js_emails)

            # Validate emails in parallel
            if page_emails:
                val_results = await asyncio.gather(*[validate_single_email(e) for e in page_emails])
                for ve in val_results:
                    if ve:
                        found_emails.add(ve)
            
            # Find internal links
            local_seen = set()
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(final_url, href).split('#')[0]
                parsed_link = urlparse(full_url)
                
                # Only follow internal links (allow subdomains)
                link_netloc = parsed_link.netloc
                if (link_netloc == domain or link_netloc.endswith('.' + domain)) and full_url not in local_seen:
                    local_seen.add(full_url)
                    link_text = link.get_text().lower()
                    path = parsed_link.path.lower()
                    
                    # Prioritize Contact or About pages
                    if 'contact' in path or 'contact' in link_text or 'about' in path:
                        priority_links.append(full_url)
                    else:
                        other_links.append(full_url)

    except Exception as e:
        print(f"Error crawling {url}: {e}")
    
    return found_emails, priority_links, other_links, metadata

async def crawl_site(start_url: str, max_pages: int = 15):
    domain = urlparse(start_url).netloc
    if domain.startswith("www."):
        domain = domain[4:]
    visited = set()
    queue = [start_url]
    found_emails = set()
    
    final_metadata = {
        "title": "",
        "description": ""
    }
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Concurrency limit
    BATCH_SIZE = 5

    async with aiohttp.ClientSession(headers=SAFE_HEADERS, connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        
        while queue and len(visited) < max_pages:
            # Prepare a batch of URLs
            batch = []
            
            # Fill batch up to limit or until max_pages is potentially reached
            # Note: We need to be careful not to overshoot max_pages too much, 
            # but for performance slightly overshooting is better than sequential.
            while queue and len(batch) < BATCH_SIZE and (len(visited) + len(batch)) < (max_pages + BATCH_SIZE):
                next_url = queue.pop(0)
                if next_url not in visited:
                    visited.add(next_url)
                    batch.append(next_url)
            
            if not batch:
                break
                
            # Run batch
            tasks = []
            for url in batch:
                extract_meta = (url == start_url)
                tasks.append(_process_page_worker(session, url, domain, extract_meta))
            
            results = await asyncio.gather(*tasks)
            
            # Process results
            for result in results:
                emails, p_links, o_links, metadata = result
                
                # Update emails
                found_emails.update(emails)
                
                # Update metadata if found (from homepage usually)
                if metadata:
                    final_metadata = metadata
                
                # Update queue (prioritize contact links)
                # We add priority links to the FRONT of the queue to be picked up in next batch
                for l in reversed(o_links):
                    if l not in visited and l not in queue:
                         queue.append(l)
                
                for l in reversed(p_links):
                    if l not in visited and l not in queue:
                         queue.insert(0, l)
            
            # Small delay between batches to be polite
            await asyncio.sleep(0.1)

    return {
        "metadata": final_metadata,
        "emails": list(found_emails)
    }

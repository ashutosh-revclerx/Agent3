"""
agents/scraping_agent.py
────────────────────────
SCRAPING & EXTRACTION AGENT (Sprint 1 Foundation)
─────────────────────────────────────────────────
Responsibility:
  - Interfaces with Nexus API for company website and LinkedIn scraping
  - Uses Gemini to extract structured CompanyDNA and ParticipantProfiles
  - Validates output using Pydantic schemas with confidence flags
  - Generates fun facts and icebreakers
  - Manages data staleness (30-day TTL for company, 7-day for participant data)
  - Provides fallback flows when scraping fails or returns partial data
"""

import logging
import asyncio
import json
import os
import httpx
import websockets
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Literal
from dotenv import load_dotenv
from pydantic import ValidationError

from gemini_client import gemini_json, gemini_text
from schemas import CompanyDNA, ParticipantProfile

# Load env from same folder
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger("copilot.scraping_agent")

class NexusClient:
    """
    Async client for the Nexus Scraping API.
    Handles submitting scrape jobs and retrieving results via WebSocket or Polling.
    """
    BASE_URL = "http://124.123.18.150:9090/nexus-api"
    API_KEY = os.getenv("NEXUS_API_KEY", "nxs_ZsMlNFaSe9b-994Fh-ttIV3rNyuk72PN")

    def __init__(self):
        self.headers = {
            "X-API-Key": self.API_KEY,
            "Content-Type": "application/json"
        }

    async def submit_scrape(self, url: str, output_format: str = "markdown", js_render: bool = False) -> str:
        async with httpx.AsyncClient() as client:
            payload = {
                "url": url,
                "output_format": output_format,
                "js_render": js_render
            }
            try:
                response = await client.post(f"{self.BASE_URL}/public/scrape", headers=self.headers, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                job_id = data.get("job_id")
                if not job_id:
                    raise ValueError(f"Nexus API response missing job_id: {data}")
                return job_id
            except Exception as e:
                logger.error(f"NexusClient: Failed to submit scrape for {url}: {e}")
                raise

    async def get_result_polling(self, job_id: str, interval: float = 2.0, timeout: float = 60.0) -> Dict[str, Any]:
        start_time = asyncio.get_event_loop().time()
        async with httpx.AsyncClient() as client:
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    response = await client.get(f"{self.BASE_URL}/public/result/{job_id}", headers=self.headers)
                    response.raise_for_status()
                    data = response.json()
                    status = data.get("status")
                    if status == "done":
                        return data
                    elif status == "failed":
                        raise Exception(f"Nexus job {job_id} failed: {data.get('error', 'Unknown error')}")
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"NexusClient: Error polling job {job_id}: {e}")
                    raise
            raise TimeoutError(f"NexusClient: Scrape job {job_id} timed out")

    async def get_result_ws(self, job_id: str, timeout: float = 60.0) -> Dict[str, Any]:
        ws_url = f"ws://124.123.18.150:9090/nexus-api/public/ws?api_key={self.API_KEY}&job_id={job_id}"
        try:
            async with websockets.connect(ws_url) as websocket:
                message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                data = json.loads(message)
                if data.get("status") == "done":
                    return data
                elif data.get("status") == "failed":
                    raise Exception(f"Nexus job {job_id} failed via WS: {data.get('error')}")
                return data
        except Exception as e:
            logger.warning(f"NexusClient: WebSocket failed for {job_id}: {e}. Falling back to polling.")
            return await self.get_result_polling(job_id, timeout=timeout)

# Singleton instance
_nexus = NexusClient()


# ── Extraction Logic ────────────────────────────────────────────────────────

def sanitise_markdown(text: str) -> str:
    """
    Strips common prompt injection or adversarial patterns from raw scraped text.
    """
    if not text: return ""
    bad_patterns = [
        "Ignore all previous instructions",
        "System prompt",
        "Override",
        "Admin",
        "Forget the rules",
        "Repeat the instructions"
    ]
    cleaned = text
    for p in bad_patterns:
        cleaned = cleaned.replace(p, "[STRIPPED]")
    return cleaned[:50000] # Limit size for token safety

def is_data_stale(scraped_at: Optional[datetime], ttl_days: int = 30) -> bool:
    """
    Check if scraped data has exceeded its time-to-live.
    
    Args:
        scraped_at: Timestamp when data was scraped
        ttl_days: Days until data is considered stale (30 for company, 7 for participant)
    
    Returns:
        True if data is stale or missing timestamp, False otherwise
    """
    if not scraped_at:
        return True
    delta = datetime.utcnow() - scraped_at
    return delta > timedelta(days=ttl_days)

def get_weather_and_sports(location: str) -> Dict[str, Any]:
    """
    Fetch local weather and sports context for a given location.
    Uses OpenWeather API (free tier) and Gemini for sports highlights.
    
    Args:
        location: City or location string (e.g., "San Francisco")
    
    Returns:
        Dict with weather, sports_icebreaker, local_time, or empty dict on failure
    """
    if not location:
        return {}
    
    try:
        # Try OpenWeather API (requires API key in .env)
        openweather_key = os.getenv("OPENWEATHER_API_KEY", "")
        weather_data = {}
        
        if openweather_key:
            try:
                response = requests.get(
                    f"https://api.openweathermap.org/data/2.5/weather",
                    params={"q": location, "appid": openweather_key, "units": "metric"},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    weather_data = {
                        "weather": f"{data['main']['temp']:.0f}°C and {data['weather'][0]['main']}",
                        "local_time": f"~{data['sys'].get('sunset', 'N/A')}"
                    }
            except Exception as e:
                logger.warning(f"OpenWeather API failed for {location}: {e}")
        
        # Use Gemini for sports and timezone context
        prompt = f"""
        Find current local context for {location}:
        1. Local Sports: Is there a major local sports team playing today or recently? If so, what's a fun highlight?
        2. Timezone: What is the current local time zone?
        
        Return JSON only:
        {{"sports_icebreaker": "e.g. The Lakers won a thriller last night", "timezone": "e.g. PST"}}
        """
        
        try:
            sports_result = gemini_json(prompt)
            if sports_result:
                weather_data.update(sports_result)
            return weather_data
        except Exception as e:
            logger.warning(f"Scraping Agent: Failed to get sports context for {location}: {e}")
            return weather_data
    except Exception as e:
        logger.error(f"Scraping Agent: Failed to get weather/sports for {location}: {e}")
        return {}

def extract_company_dna(markdown_content: str, url: str) -> Optional[CompanyDNA]:
    """
    Extract structured company data from scraped markdown content.
    Uses Gemini with strict schema validation and confidence flagging.
    
    Args:
        markdown_content: Raw markdown from website scrape
        url: Source URL for traceability
    
    Returns:
        CompanyDNA object with confidence flag, or None on extraction failure
    """
    if not markdown_content or len(markdown_content.strip()) < 50:
        logger.warning(f"Extraction: Insufficient content from {url} for Company DNA")
        return None
    
    markdown_content = sanitise_markdown(markdown_content)
    
    prompt = f"""
    Extract structured data from the company website content below.
    Return ONLY valid JSON matching this schema:
    {{
        "company_name": "Company Name",
        "vision": "The company's core mission and vision",
        "goals": ["goal1", "goal2", ...],
        "products": ["product1", "product2", ...],
        "tone": "professional/innovative/customer-focused/etc",
        "recent_news": ["news1", "news2", ...]
    }}
    
    If a field cannot be confidently extracted, use an empty string or empty list.
    
    Website content:
    {markdown_content}
    
    URL: {url}
    """
    
    try:
        result = gemini_json(prompt)
        if not result:
            logger.warning(f"Extraction: Gemini returned empty result for {url}")
            return None
        
        # Ensure required fields
        if "company_name" not in result or not result["company_name"]:
            logger.warning(f"Extraction: Missing company_name in result from {url}")
            return None
        
        result["source_url"] = url
        result["scraped_at"] = datetime.utcnow()
        
        # Determine confidence level
        required_fields = ["company_name", "vision", "goals", "products", "tone"]
        extracted_count = sum(1 for field in required_fields if result.get(field))
        
        if extracted_count >= 4:
            result["confidence"] = "complete"
        elif extracted_count >= 2:
            result["confidence"] = "partial"
        else:
            result["confidence"] = "fallback"
        
        # Validate against schema
        dna = CompanyDNA(**result)
        logger.info(f"Extraction: Company DNA extracted with confidence={dna.confidence} from {url}")
        return dna
    except ValidationError as e:
        logger.error(f"Extraction: Schema validation failed for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Extraction Agent: Failed to extract DNA from {url}: {e}")
        return None

def extract_participant_profile(markdown_content: str, url: str) -> Optional[ParticipantProfile]:
    """
    Extract professional profile data from LinkedIn or other profile page.
    Uses Gemini with strict schema validation and confidence flagging.
    
    Args:
        markdown_content: Raw markdown from profile scrape
        url: LinkedIn or profile URL
    
    Returns:
        ParticipantProfile object with confidence flag, or None on extraction failure
    """
    if not markdown_content or len(markdown_content.strip()) < 30:
        logger.warning(f"Extraction: Insufficient content from {url} for Participant Profile")
        return None
    
    markdown_content = sanitise_markdown(markdown_content)
    
    # Check if this is a login wall (LinkedIn returns login page if not authenticated)
    login_indicators = ["Sign in", "Sign up", "Join LinkedIn", "Log in to LinkedIn"]
    if any(indicator in markdown_content for indicator in login_indicators):
        logger.warning(f"Extraction: Login wall detected at {url} — routing to self-entry fallback")
        return None
    
    prompt = f"""
    Extract professional profile data from the LinkedIn or profile page content below.
    Return ONLY valid JSON matching this schema:
    {{
        "name": "Full Name",
        "role": "Job Title",
        "company": "Company Name",
        "headline": "Professional headline",
        "summary": "Short bio or summary",
        "skills": ["skill1", "skill2", ...],
        "location": "City, Country",
        "industry": "Industry or field"
    }}
    
    If a field cannot be extracted, use an empty string or empty list.
    Extract only confirmed information visible on the profile.
    
    Profile content:
    {markdown_content}
    
    URL: {url}
    """
    
    try:
        result = gemini_json(prompt)
        if not result:
            logger.warning(f"Extraction: Gemini returned empty result for {url}")
            return None
        
        # Ensure required fields
        if "name" not in result or not result["name"]:
            logger.warning(f"Extraction: Missing name in result from {url}")
            return None
        
        result["linkedin_url"] = url
        result["source"] = "linkedin"
        result["scraped_at"] = datetime.utcnow()
        
        # Determine confidence level
        required_fields = ["name", "role", "company", "headline", "location"]
        extracted_count = sum(1 for field in required_fields if result.get(field))
        
        if extracted_count >= 4:
            result["confidence"] = "complete"
        elif extracted_count >= 2:
            result["confidence"] = "partial"
        else:
            result["confidence"] = "fallback"
        
        # Validate against schema
        profile = ParticipantProfile(**result)
        logger.info(f"Extraction: Participant Profile extracted with confidence={profile.confidence} from {url}")
        return profile
    except ValidationError as e:
        logger.error(f"Extraction: Schema validation failed for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Extraction Agent: Failed to extract profile from {url}: {e}")
        return None

def generate_fun_fact(profile: ParticipantProfile) -> Optional[str]:
    prompt = f"Generate ONE fun fact for {profile.name} based on their profile: {profile.model_dump_json()}"
    try:
        fact = gemini_text(prompt)
        return fact.strip() if fact else None
    except Exception as e:
        logger.error(f"Extraction Agent: Failed to generate fun fact for {profile.name}: {e}")
    return None


# ── Agent Actions ──────────────────────────────────────────────────────────

async def run_company_scrape(session_code: str, url: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Scrape company website and extract structured Company DNA.
    
    Args:
        session_code: Session identifier for logging
        url: Company website URL
        force_refresh: Ignore TTL and re-scrape (used for manual refresh)
    
    Returns:
        CompanyDNA dict with confidence flag, or None on complete failure
    """
    try:
        logger.info(f"Scraping Agent: Starting company scrape for {session_code} from {url}")
        
        job_id = await _nexus.submit_scrape(url, output_format="markdown", js_render=False)
        logger.info(f"Scraping Agent: Submitted job {job_id} for {url}")
        
        result = await _nexus.get_result_ws(job_id, timeout=60.0)
        
        if result.get("status") == "done":
            content = result.get("content", "")
            dna = extract_company_dna(content, url)
            
            if dna:
                dna_dict = dna.model_dump()
                logger.info(f"Scraping Agent: Company DNA extracted for {session_code} with confidence={dna.confidence}")
                return dna_dict
            else:
                logger.warning(f"Scraping Agent: Extraction returned None for {session_code}")
                return None
        else:
            logger.error(f"Scraping Agent: Scrape failed with status {result.get('status')} for {url}")
            return None
    except Exception as e:
        logger.error(f"Scraping Agent: Company scrape for {session_code} failed: {e}")
        return None


async def run_linkedin_scrape(participant_id: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape LinkedIn profile and extract structured Participant Profile.
    
    Args:
        participant_id: Participant identifier for logging
        url: LinkedIn profile URL
    
    Returns:
        ParticipantProfile dict with fun fact and local context, or None on failure
        Returns None if login wall detected — triggers self-entry fallback
    """
    try:
        logger.info(f"Scraping Agent: Starting LinkedIn profile scrape for {participant_id} from {url}")
        
        # Use js_render=True for React SPA content loading
        job_id = await _nexus.submit_scrape(url, output_format="markdown", js_render=True)
        logger.info(f"Scraping Agent: Submitted LinkedIn job {job_id}")
        
        result = await _nexus.get_result_ws(job_id, timeout=60.0)
        
        if result.get("status") == "done":
            content = result.get("content", "")
            profile = extract_participant_profile(content, url)
            
            if profile:
                profile_data = profile.model_dump()
                
                # Generate fun fact from confirmed data
                profile_data["fun_fact"] = generate_fun_fact(profile)
                
                # Get local context (weather, sports, timezone)
                if profile.location:
                    local_context = get_weather_and_sports(profile.location)
                    profile_data["local_context"] = local_context
                
                logger.info(f"Scraping Agent: LinkedIn profile extracted for {participant_id} with confidence={profile.confidence}")
                return profile_data
            else:
                # Extraction returned None (likely login wall or insufficient content)
                logger.warning(f"Scraping Agent: Profile extraction failed for {participant_id} — routing to self-entry fallback")
                return None
        else:
            logger.error(f"Scraping Agent: LinkedIn scrape failed with status {result.get('status')} for {url}")
            return None
    except Exception as e:
        logger.error(f"Scraping Agent: LinkedIn scrape for {participant_id} failed: {e}")
        return None

from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class CompanyDNA(BaseModel):
    """
    Structured representation of a company's vision, goals, products, and culture.
    Extracted from the company website.
    """
    company_name: str
    vision: str = Field(description="The company's core mission and vision for the future.")
    goals: List[str] = Field(default_factory=list, description="Key strategic goals or objectives mentioned on the website.")
    products: List[str] = Field(default_factory=list, description="Core products or services offered by the company.")
    recent_news: List[str] = Field(default_factory=list, description="Recent announcements or highlights from the company.")
    confidence: Literal["complete", "partial", "fallback"] = "partial"
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    source_url: Optional[str] = None
    raw_markdown: Optional[str] = None

class ParticipantProfile(BaseModel):
    """
    Structured representation of a participant's professional profile.
    Extracted from LinkedIn or self-entered.
    """
    name: str
    role: str
    company: Optional[str] = None
    headline: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    industry: Optional[str] = None
    confidence: Literal["complete", "partial", "fallback"] = "partial"
    source: Literal["linkedin", "manual"] = "manual"
    scraped_at: Optional[datetime] = None
    linkedin_url: Optional[str] = None
    fun_fact: Optional[str] = None
    local_context: Optional[Dict] = None

class ScrapeResult(BaseModel):
    """
    Wrapper for any scrape operation.
    """
    job_id: str
    status: str
    url: str
    content: Optional[str] = None
    error: Optional[str] = None

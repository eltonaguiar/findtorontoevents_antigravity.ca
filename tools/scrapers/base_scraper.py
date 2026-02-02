#!/usr/bin/env python3
"""
Base scraper class with common functionality for all Toronto event scrapers.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup

# Known Toronto venue locations with coordinates
TORONTO_VENUES = {
    "nathan phillips square": {
        "address": "100 Queen St W, Toronto, ON M5H 2N2",
        "lat": 43.6525,
        "lng": -79.3832
    },
    "sankofa square": {
        "address": "1 Dundas St E, Toronto, ON M5B 2R8",
        "lat": 43.6561,
        "lng": -79.3802
    },
    "toronto city hall": {
        "address": "100 Queen St W, Toronto, ON M5H 2N1",
        "lat": 43.6534,
        "lng": -79.3841
    },
    "harbourfront centre": {
        "address": "235 Queens Quay W, Toronto, ON M5J 2G8",
        "lat": 43.6388,
        "lng": -79.3822
    },
    "ontario place": {
        "address": "955 Lake Shore Blvd W, Toronto, ON M6K 3B9",
        "lat": 43.6283,
        "lng": -79.4139
    },
    "exhibition place": {
        "address": "100 Princes' Blvd, Toronto, ON M6K 3C3",
        "lat": 43.6355,
        "lng": -79.4176
    },
    "fort york": {
        "address": "250 Fort York Blvd, Toronto, ON M5V 3K9",
        "lat": 43.6389,
        "lng": -79.4030
    },
    "the distillery district": {
        "address": "55 Mill St, Toronto, ON M5A 3C4",
        "lat": 43.6503,
        "lng": -79.3596
    },
    "yonge-dundas square": {
        "address": "1 Dundas St E, Toronto, ON M5B 2R8",
        "lat": 43.6561,
        "lng": -79.3802
    },
    "queens park": {
        "address": "Queens Park, Toronto, ON M5S 2C6",
        "lat": 43.6624,
        "lng": -79.3913
    },
    "high park": {
        "address": "1873 Bloor St W, Toronto, ON M6R 2Z3",
        "lat": 43.6465,
        "lng": -79.4637
    },
    "mel lastman square": {
        "address": "5100 Yonge St, North York, ON M2N 5V7",
        "lat": 43.7676,
        "lng": -79.4137
    },
    "scarborough civic centre": {
        "address": "150 Borough Dr, Scarborough, ON M1P 4N7",
        "lat": 43.7731,
        "lng": -79.2578
    },
    "etobicoke civic centre": {
        "address": "399 The West Mall, Etobicoke, ON M9C 2Y2",
        "lat": 43.6438,
        "lng": -79.5597
    },
    "east york civic centre": {
        "address": "850 Coxwell Ave, East York, ON M4C 5R1",
        "lat": 43.6906,
        "lng": -79.3272
    },
    "bmo field": {
        "address": "170 Princes' Blvd, Toronto, ON M6K 3C3",
        "lat": 43.6332,
        "lng": -79.4186
    },
    "rogers centre": {
        "address": "1 Blue Jays Way, Toronto, ON M5V 1J1",
        "lat": 43.6414,
        "lng": -79.3894
    },
    "scotiabank arena": {
        "address": "40 Bay St, Toronto, ON M5J 2X2",
        "lat": 43.6435,
        "lng": -79.3791
    },
    "roy thomson hall": {
        "address": "60 Simcoe St, Toronto, ON M5J 2H5",
        "lat": 43.6466,
        "lng": -79.3864
    },
    "massey hall": {
        "address": "178 Victoria St, Toronto, ON M5B 1T7",
        "lat": 43.6545,
        "lng": -79.3787
    },
    "aga khan museum": {
        "address": "77 Wynford Dr, North York, ON M3C 1K1",
        "lat": 43.7257,
        "lng": -79.3323
    },
    "rom": {
        "address": "100 Queens Park, Toronto, ON M5S 2C6",
        "lat": 43.6677,
        "lng": -79.3948
    },
    "ago": {
        "address": "317 Dundas St W, Toronto, ON M5T 1G4",
        "lat": 43.6536,
        "lng": -79.3925
    },
    "cn tower": {
        "address": "290 Bremner Blvd, Toronto, ON M5V 3L9",
        "lat": 43.6426,
        "lng": -79.3871
    },
    "casa loma": {
        "address": "1 Austin Terrace, Toronto, ON M5R 1X8",
        "lat": 43.6780,
        "lng": -79.4094
    },
    "st. lawrence market": {
        "address": "93 Front St E, Toronto, ON M5E 1C3",
        "lat": 43.6487,
        "lng": -79.3715
    },
    "kensington market": {
        "address": "Kensington Ave, Toronto, ON M5T 2K2",
        "lat": 43.6547,
        "lng": -79.4005
    }
}

# Exclusion patterns for non-events
EXCLUSION_PATTERNS = [
    r"square maintenance",
    r"maintenance day",
    r"closed for",
    r"facility closure",
    r"private event",
    r"rental only",
    r"staff only",
    r"internal meeting"
]


@dataclass
class ScrapedEvent:
    """Standardized event data structure"""
    id: str
    title: str
    date: str  # ISO format
    end_date: Optional[str] = None  # For multi-day events
    location: str = "Toronto, ON"
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    source: str = "Unknown"
    host: str = ""
    url: str = ""
    price: str = "Free"
    price_amount: float = 0.0
    is_free: bool = True
    description: str = ""
    categories: List[str] = None
    tags: List[str] = None
    status: str = "UPCOMING"
    is_multi_day: bool = False
    last_updated: str = ""
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = ["General"]
        if self.tags is None:
            self.tags = ["General"]
        if not self.last_updated:
            self.last_updated = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        # Remove None values and internal fields
        return {k: v for k, v in d.items() if v is not None}


class BaseScraper:
    """Base class for all Toronto event scrapers"""
    
    SOURCE_NAME = "Unknown"
    BASE_URL = ""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error fetching {url}: {e}")
            return None
    
    def generate_event_id(self, title: str, date: str, source: str) -> str:
        """Generate a unique event ID from title + date + source"""
        raw = f"{title.lower().strip()}-{date}-{source}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    def should_exclude(self, title: str) -> bool:
        """Check if event should be excluded based on title"""
        title_lower = title.lower()
        for pattern in EXCLUSION_PATTERNS:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return True
        return False
    
    def parse_date(self, date_str: str, year: int = None) -> Optional[str]:
        """Parse various date formats to ISO format"""
        if year is None:
            year = datetime.now().year
        
        # Clean the string
        date_str = date_str.strip()
        
        # Common date formats
        formats = [
            "%B %d, %Y",      # January 15, 2026
            "%B %d %Y",       # January 15 2026
            "%b %d, %Y",      # Jan 15, 2026
            "%b %d %Y",       # Jan 15 2026
            "%Y-%m-%d",       # 2026-01-15
            "%m/%d/%Y",       # 01/15/2026
            "%d/%m/%Y",       # 15/01/2026
            "%B %d",          # January 15 (no year)
            "%b %d",          # Jan 15 (no year)
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If no year in format, use provided year
                if dt.year == 1900:
                    dt = dt.replace(year=year)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        
        return None
    
    def parse_date_range(self, date_str: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse date ranges like 'January 15 to 20' or 'Feb 1 - Feb 5'"""
        # Patterns for date ranges
        patterns = [
            # "January 15 to 20" or "January 15 - 20"
            r"(\w+ \d+)\s*(?:to|-)\s*(\d+)",
            # "January 15 to February 20" or "Jan 15 - Feb 20"
            r"(\w+ \d+)\s*(?:to|-)\s*(\w+ \d+)",
            # "Jan 15 - Jan 20, 2026"
            r"(\w+ \d+)\s*-\s*(\w+ \d+),?\s*(\d{4})?",
        ]
        
        year = datetime.now().year
        
        for pattern in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                groups = match.groups()
                start_str = groups[0]
                end_str = groups[1] if len(groups) > 1 else None
                
                # Try to extract year
                if len(groups) > 2 and groups[2]:
                    year = int(groups[2])
                
                start_date = self.parse_date(start_str, year)
                
                if end_str:
                    # If end is just a day number, construct full date
                    if end_str.isdigit():
                        month = start_str.split()[0]
                        end_str = f"{month} {end_str}"
                    end_date = self.parse_date(end_str, year)
                else:
                    end_date = None
                
                return start_date, end_date
        
        # If no range found, try single date
        single_date = self.parse_date(date_str)
        return single_date, None
    
    def enhance_location(self, location_text: str, title: str = "") -> Dict:
        """Enhance location with coordinates and full address"""
        result = {
            "location": location_text,
            "address": None,
            "lat": None,
            "lng": None
        }
        
        # Combine title and location for venue detection
        combined = f"{title} {location_text}".lower()
        
        # Check known venues
        for venue_name, venue_data in TORONTO_VENUES.items():
            if venue_name in combined:
                result["location"] = venue_name.title()
                result["address"] = venue_data["address"]
                result["lat"] = venue_data["lat"]
                result["lng"] = venue_data["lng"]
                return result
        
        # If location is too generic, try to extract more specific info
        if location_text.lower() in ["toronto", "toronto, on", "toronto, ontario"]:
            # Check title for venue hints
            for venue_name, venue_data in TORONTO_VENUES.items():
                if venue_name in title.lower():
                    result["location"] = venue_name.title()
                    result["address"] = venue_data["address"]
                    result["lat"] = venue_data["lat"]
                    result["lng"] = venue_data["lng"]
                    return result
        
        # Try to detect if it's an address
        address_patterns = [
            r"\d+\s+[\w\s]+(?:st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|way|cres|crescent)",
        ]
        for pattern in address_patterns:
            match = re.search(pattern, location_text, re.IGNORECASE)
            if match:
                result["address"] = location_text
                break
        
        return result
    
    def categorize_event(self, title: str, description: str = "") -> Tuple[List[str], List[str]]:
        """Categorize event based on title and description"""
        combined = f"{title} {description}".lower()
        
        category_keywords = {
            "Music": ["concert", "music", "live band", "dj", "festival music", "orchestra", "symphony", "jazz", "hip hop", "r&b", "electronic"],
            "Arts": ["art", "gallery", "exhibit", "exhibition", "museum", "painting", "sculpture", "installation", "film", "cinema", "movie"],
            "Sports": ["sports", "game", "match", "hockey", "basketball", "soccer", "football", "baseball", "tennis", "run", "marathon", "race", "athletic"],
            "Food & Drink": ["food", "culinary", "taste", "restaurant", "chef", "dining", "wine", "beer", "brunch", "market food"],
            "Nightlife": ["nightlife", "club", "party", "dance", "bar", "lounge", "midnight", "after dark"],
            "Family": ["family", "kids", "children", "youth", "all ages", "educational"],
            "Community": ["community", "neighbourhood", "cultural", "heritage", "parade", "celebration", "festival"],
            "Business": ["business", "networking", "professional", "conference", "seminar", "workshop", "trade"],
            "Dating": ["dating", "singles", "mingle", "speed dating", "matchmaking", "social mixer"],
        }
        
        categories = []
        tags = []
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in combined:
                    if category not in categories:
                        categories.append(category)
                    if keyword not in tags:
                        tags.append(keyword.title())
        
        if not categories:
            categories = ["General"]
        if not tags:
            tags = ["General"]
        
        return categories, tags
    
    def scrape(self) -> List[ScrapedEvent]:
        """Override this method in subclasses to implement scraping logic"""
        raise NotImplementedError("Subclasses must implement scrape()")
    
    def scrape_to_json(self) -> List[Dict]:
        """Scrape events and return as list of dictionaries"""
        events = self.scrape()
        return [event.to_dict() for event in events]

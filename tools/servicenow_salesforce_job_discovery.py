#!/usr/bin/env python3
# ServiceNow & Salesforce Job Discovery Tool
# Uses SubQ API for document comparison and decision making

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Add project root to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SubQ API configuration
SUBQ_API_URL = "https://api.subq.dev/v1"
SUBQ_FREE_KEY = "sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV"
SUBQ_PAID_KEY = "sk-proj-7IuzAriNQVjz7lnikGi2Hi45c4j084O7"

# Job sources configuration
def get_servicenow_sources():
    return [
        # Direct company career pages
        {"name": "ServiceNow", "url": "https://careers.servicenow.com/jobs/", "type": "direct"},
        {"name": "BDO Canada", "url": "https://www.jobs.ca/bdo/jobs/", "type": "direct"},
        {"name": "Huron Consulting", "url": "https://www.flexjobs.com/gjw/huron_consulting_group/", "type": "direct"},
        {"name": "Platform 6", "url": "https://www.platform-6.com/job/", "type": "direct"},
        {"name": "ComTec", "url": "https://haystackapp.io/jobs/", "type": "direct"},
        
        # Job aggregators
        {"name": "Remotery", "url": "https://www.remotery.co/remote-servicenow-jobs/north-america-remote", "type": "aggregator"},
        {"name": "FlexJobs", "url": "https://www.flexjobs.com", "type": "aggregator"},
        {"name": "Dice", "url": "https://www.dice.com", "type": "aggregator"},
        {"name": "Indeed Canada", "url": "https://ca.indeed.com", "type": "aggregator"},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs", "type": "aggregator"},
    ]

def get_salesforce_sources():
    return [
        # Direct company career pages
        {"name": "Salesforce", "url": "https://salesforce.wd5.myworkdayjobs.com/en-US/Salesforce_Careers/", "type": "direct"},
        {"name": "Kicksaw", "url": "https://www.kicksaw.com", "type": "direct"},
        {"name": "Decisive Point", "url": "https://dailyremote.com/remote-job/senior-salesforce-administrator-5461410", "type": "direct"},
        {"name": "Marsh McLennan", "url": "https://www.marshmclennan.com", "type": "direct"},
        {"name": "Cherokee Federal", "url": "https://jobgether.com/offer/6a8f690741fb9301cd8e1dc3-agentforce-salesforce-developer", "type": "direct"},
        
        # Job aggregators
        {"name": "BuiltIn", "url": "https://builtin.com/job/salesforce-administrator/2786969", "type": "aggregator"},
        {"name": "NeuraFlash", "url": "https://www.neuraflash.com", "type": "aggregator"},
        {"name": "Indeed Canada", "url": "https://ca.indeed.com", "type": "aggregator"},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs", "type": "aggregator"},
        {"name": "FlexJobs", "url": "https://www.flexjobs.com", "type": "aggregator"},
    ]

# Search patterns and filters
def get_search_patterns():
    return {
        "servicenow": {
            "keywords": ["ServiceNow Developer", "ServiceNow Architect", "ServiceNow Consultant", "ServiceNow Administrator"],
            "certifications": ["CSA", "CAD", "CIS-CSM", "CMA", "CTA", "CIS"],
            "technologies": ["ITSM", "CSM", "GRC", "HRSD", "IRM", "ITOM", "SecOps"],
            "locations": ["Toronto", "Remote Canada", "Canada", "GTA", "Mississauga", "Brampton", "Vaughan", "Markham", "Richmond Hill"]
        },
        "salesforce": {
            "keywords": ["Salesforce Developer", "Salesforce Administrator", "Salesforce Architect", "Salesforce Consultant"],
            "certifications": ["Admin", "PD I", "PD II", "Advanced Admin", "Platform Developer I", "Platform Developer II"],
            "technologies": ["Apex", "LWC", "SOQL", "Visualforce", "Agentforce", "Lightning Web Components"],
            "locations": ["Toronto", "Remote Canada", "Canada", "GTA", "Mississauga", "Brampton", "Vaughan", "Markham", "Richmond Hill"]
        }
    }

class JobDiscoveryEngine:
    def __init__(self, use_paid_subq=False):
        self.use_paid_subq = use_paid_subq
        self.subq_key = SUBQ_PAID_KEY if use_paid_subq else SUBQ_FREE_KEY
        self.results = []
        
    def scan_source(self, source: Dict, job_type: str) -> List[Dict]:
        """Scan a single source for jobs"""
        logger.info(f"Scanning {source['name']} ({source['type']}) for {job_type} jobs")
        
        # This is a placeholder - in production this would use actual web scraping
        # For now, we'll simulate the process with sample data
        sample_jobs = self._generate_sample_jobs(source, job_type)
        
        # Apply quality filtering
        filtered_jobs = self._filter_jobs(sample_jobs, job_type)
        
        logger.info(f"Found {len(filtered_jobs)} qualified {job_type} jobs from {source['name']}")
        return filtered_jobs
    
    def _generate_sample_jobs(self, source: Dict, job_type: str) -> List[Dict]:
        """Generate sample jobs for demonstration purposes"""
        patterns = get_search_patterns()
        
        # Simulate different numbers of jobs based on source type
        base_count = 5 if source['type'] == 'direct' else 20
        
        jobs = []
        for i in range(base_count):
            job = {
                "id": f"{source['name'].lower().replace(' ', '_')}_{job_type}_{i}",
                "title": self._get_random_title(job_type, patterns[job_type]['keywords']),
                "company": source['name'],
                "url": f"{source['url']}job{i}",
                "location": self._get_random_location(patterns[job_type]['locations']),
                "certifications": self._get_random_certifications(patterns[job_type]['certifications']),
                "technologies": self._get_random_technologies(patterns[job_type]['technologies']),
                "posted_date": (datetime.now()).strftime("%Y-%m-%d"),
                "source": source['name'],
                "source_type": source['type'],
                "score": self._calculate_quality_score(job_type, source)
            }
            jobs.append(job)
        
        return jobs
    
    def _get_random_title(self, job_type: str, keywords: List[str]) -> str:
        import random
        keyword = random.choice(keywords)
        locations = ["Toronto", "Remote", "Canada", "GTA"]
        location = random.choice(locations)
        return f"{keyword} - {location}" if random.random() > 0.3 else keyword
    
    def _get_random_location(self, locations: List[str]) -> str:
        import random
        return random.choice(locations)
    
    def _get_random_certifications(self, certifications: List[str]) -> List[str]:
        import random
        count = random.randint(0, 2)
        return random.sample(certifications, min(count, len(certifications)))
    
    def _get_random_technologies(self, technologies: List[str]) -> List[str]:
        import random
        count = random.randint(1, 3)
        return random.sample(technologies, min(count, len(technologies)))
    
    def _calculate_quality_score(self, job_type: str, source: Dict) -> float:
        """Calculate quality score based on source reliability and job type"""
        scores = {
            "direct": 0.9,
            "aggregator": 0.7
        }
        
        base_score = scores.get(source['type'], 0.5)
        
        # Bonus for Toronto/Remote Canada locations
        if "Toronto" in source['name'] or "Remote Canada" in source['name']:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _filter_jobs(self, jobs: List[Dict], job_type: str) -> List[Dict]:
        """Apply quality filtering to jobs"""
        patterns = get_search_patterns()
        
        filtered = []
        for job in jobs:
            # Filter by location
            location_match = any(loc.lower() in job['location'].lower() 
                               for loc in patterns[job_type]['locations'])
            
            # Filter by certifications
            cert_match = len(job['certifications']) > 0
            
            # Filter by recency (last 7 days)
            from datetime import datetime, timedelta
            posted_date = datetime.strptime(job['posted_date'], "%Y-%m-%d")
            recent = (datetime.now() - posted_date).days <= 7
            
            # Score threshold
            score_ok = job['score'] >= 0.7
            
            if location_match and cert_match and recent and score_ok:
                filtered.append(job)
        
        return filtered
    
    def run_discovery(self) -> Dict[str, List[Dict]]:
        """Run the complete job discovery process"""
        logger.info("Starting ServiceNow & Salesforce job discovery...")
        
        results = {
            "servicenow": [],
            "salesforce": []
        }
        
        # Scan ServiceNow sources
        servicenow_sources = get_servicenow_sources()
        for source in servicenow_sources:
            jobs = self.scan_source(source, "servicenow")
            results["servicenow"].extend(jobs)
        
        # Scan Salesforce sources
        salesforce_sources = get_salesforce_sources()
        for source in salesforce_sources:
            jobs = self.scan_source(source, "salesforce")
            results["salesforce"].extend(jobs)
        
        # Remove duplicates
        results["servicenow"] = self._remove_duplicates(results["servicenow"])
        results["salesforce"] = self._remove_duplicates(results["salesforce"])
        
        # Sort by score
        results["servicenow"].sort(key=lambda x: x["score"], reverse=True)
        results["salesforce"].sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Discovery completed: {len(results['servicenow'])} ServiceNow jobs, {len(results['salesforce'])} Salesforce jobs")
        
        return results
    
    def _remove_duplicates(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs by URL"""
        seen_urls = set()
        unique_jobs = []
        
        for job in jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        return unique_jobs
    
    def save_results(self, results: Dict[str, List[Dict]], filename: str = None):
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"servicenow_salesforce_jobs_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(__file__), "..", "public", filename)
        
        # Create public directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {filepath}")
        return filepath

# Main execution
def main():
    parser = argparse.ArgumentParser(description='ServiceNow & Salesforce Job Discovery Tool')
    parser.add_argument('--paid', action='store_true', help='Use paid SUBQ API key')
    parser.add_argument('--output', '-o', help='Output filename')
    args = parser.parse_args()
    
    # Initialize engine
    engine = JobDiscoveryEngine(use_paid_subq=args.paid)
    
    # Run discovery
    results = engine.run_discovery()
    
    # Save results
    filepath = engine.save_results(results, args.output)
    
    # Print summary
    print(f"\nJob Discovery Summary:")
    print(f"ServiceNow jobs found: {len(results['servicenow'])}")
    print(f"Salesforce jobs found: {len(results['salesforce'])}")
    print(f"Results saved to: {filepath}")
    
    # Show top 5 ServiceNow jobs
    if results['servicenow']:
        print(f"\nTop 5 ServiceNow Jobs:")
        for i, job in enumerate(results['servicenow'][:5]):
            print(f"{i+1}. {job['title']} @ {job['company']} ({job['location']}) - Score: {job['score']:.2f}")
    
    # Show top 5 Salesforce jobs
    if results['salesforce']:
        print(f"\nTop 5 Salesforce Jobs:")
        for i, job in enumerate(results['salesforce'][:5]):
            print(f"{i+1}. {job['title']} @ {job['company']} ({job['location']}) - Score: {job['score']:.2f}")

if __name__ == "__main__":
    import argparse
    main()

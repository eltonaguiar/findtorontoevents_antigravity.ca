# Job Discovery Configuration

# ServiceNow Configuration
SERVICENOW_CONFIG = {
    "sources": [
        # Direct company career pages
        {"name": "ServiceNow", "url": "https://careers.servicenow.com/jobs/", "priority": 10},
        {"name": "BDO Canada", "url": "https://www.jobs.ca/bdo/jobs/", "priority": 9},
        {"name": "Huron Consulting", "url": "https://www.flexjobs.com/gjw/huron_consulting_group/", "priority": 8},
        {"name": "Platform 6", "url": "https://www.platform-6.com/job/", "priority": 8},
        {"name": "ComTec", "url": "https://haystackapp.io/jobs/", "priority": 7},
        
        # Job aggregators
        {"name": "Remotery", "url": "https://www.remotery.co/remote-servicenow-jobs/north-america-remote", "priority": 6},
        {"name": "FlexJobs", "url": "https://www.flexjobs.com", "priority": 6},
        {"name": "Dice", "url": "https://www.dice.com", "priority": 5},
        {"name": "Indeed Canada", "url": "https://ca.indeed.com", "priority": 5},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs", "priority": 4},
    ],
    
    "search_patterns": {
        "keywords": ["ServiceNow Developer", "ServiceNow Architect", "ServiceNow Consultant", "ServiceNow Administrator", "ServiceNow Solution Architect"],
        "certifications": ["CSA", "CAD", "CIS-CSM", "CMA", "CTA", "CIS", "Certified System Administrator", "Certified Application Developer"],
        "technologies": ["ITSM", "CSM", "GRC", "HRSD", "IRM", "ITOM", "SecOps", "Cloud", "SRE", "DevOps"],
        "locations": ["Toronto", "Remote Canada", "Canada", "GTA", "Mississauga", "Brampton", "Vaughan", "Markham", "Richmond Hill", "Ontario"]
    },
    
    "quality_filters": {
        "min_score": 0.7,
        "max_age_days": 7,
        "required_certifications": True,
        "location_required": True
    }
}

# Salesforce Configuration
SALESFORCE_CONFIG = {
    "sources": [
        # Direct company career pages
        {"name": "Salesforce", "url": "https://salesforce.wd5.myworkdayjobs.com/en-US/Salesforce_Careers/", "priority": 10},
        {"name": "Kicksaw", "url": "https://www.kicksaw.com", "priority": 9},
        {"name": "Decisive Point", "url": "https://dailyremote.com/remote-job/senior-salesforce-administrator-5461410", "priority": 8},
        {"name": "Marsh McLennan", "url": "https://www.marshmclennan.com", "priority": 8},
        {"name": "Cherokee Federal", "url": "https://jobgether.com/offer/6a8f690741fb9301cd8e1dc3-agentforce-salesforce-developer", "priority": 7},
        
        # Job aggregators
        {"name": "BuiltIn", "url": "https://builtin.com/job/salesforce-administrator/2786969", "priority": 6},
        {"name": "NeuraFlash", "url": "https://www.neuraflash.com", "priority": 6},
        {"name": "Indeed Canada", "url": "https://ca.indeed.com", "priority": 5},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs", "priority": 4},
        {"name": "FlexJobs", "url": "https://www.flexjobs.com", "priority": 4},
    ],
    
    "search_patterns": {
        "keywords": ["Salesforce Developer", "Salesforce Administrator", "Salesforce Architect", "Salesforce Consultant", "Salesforce Platform Developer", "Salesforce Lightning Developer"],
        "certifications": ["Admin", "PD I", "PD II", "Advanced Admin", "Platform Developer I", "Platform Developer II", "Salesforce Certified Administrator", "Salesforce Certified Platform Developer I"],
        "technologies": ["Apex", "LWC", "SOQL", "Visualforce", "Agentforce", "Lightning Web Components", "Salesforce CPQ", "Salesforce Marketing Cloud"],
        "locations": ["Toronto", "Remote Canada", "Canada", "GTA", "Mississauga", "Brampton", "Vaughan", "Markham", "Richmond Hill", "Ontario"]
    },
    
    "quality_filters": {
        "min_score": 0.7,
        "max_age_days": 7,
        "required_certifications": True,
        "location_required": True
    }
}

# General Configuration
GENERAL_CONFIG = {
    "scan_frequency": {
        "hourly": True,
        "daily": True,
        "weekly": True
    },
    "notification_settings": {
        "email": True,
        "slack": False,
        "discord": True
    },
    "output_formats": ["json", "markdown", "csv"],
    "subq_api_key": "sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV",
    "subq_api_url": "https://api.subq.dev/v1"
}

# Location mapping for Toronto/GTA
TORONTO_GTA_LOCATIONS = [
    "Toronto",
    "Remote Canada",
    "Canada",
    "GTA",
    "Greater Toronto Area",
    "Mississauga",
    "Brampton",
    "Vaughan",
    "Markham",
    "Richmond Hill",
    "Newmarket",
    "Aurora",
    "Pickering",
    "Ajax",
    "Whitby",
    "Oshawa",
    "Clarington",
    "Durham Region",
    "York Region",
    "Peel Region",
    "Halton Region",
    "Ontario"
]

# Certification mapping
CERTIFICATION_MAPPING = {
    "servicenow": {
        "CSA": "Certified System Administrator",
        "CAD": "Certified Application Developer",
        "CIS-CSM": "Certified Implementation Specialist - Customer Service Management",
        "CMA": "Certified Master Architect",
        "CTA": "Certified Technical Architect"
    },
    "salesforce": {
        "Admin": "Salesforce Certified Administrator",
        "PD I": "Salesforce Certified Platform Developer I",
        "PD II": "Salesforce Certified Platform Developer II",
        "Advanced Admin": "Salesforce Certified Advanced Administrator"
    }
}

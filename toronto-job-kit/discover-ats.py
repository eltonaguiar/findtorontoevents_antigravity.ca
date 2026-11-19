#!/usr/bin/env python3
"""discover-ats.py — read-only ATS discovery for Toronto platform jobs.
   Does NOT submit applications. Only prints candidate URLs + requisition IDs.
"""
import json, sys, urllib.request, urllib.error

PORTALS = [
    {"name":"Alldus", "url":"https://alldus.com/jobs/", "type":"custom"},
    {"name":"Alimentiv", "url":"https://jobs.lever.co/alimentiv-2", "type":"lever"},
    {"name":"Versapay", "url":"https://jobs.lever.co/versapay", "type":"lever"},
    {"name":"Ensiti", "url":"https://jobs.smartrecruiters.com/Ensiti", "type":"smartrecruiters"},
    {"name":"Traction Rec", "url":"https://tractionrec.bamboohr.com/careers", "type":"bamboohr"},
    {"name":"Hydro One / Acronym", "url":"https://hydroone.talentnet.community/jobs", "type":"talentnet"},
    {"name":"Cognizant", "url":"https://careers.cognizant.com/ca-en/jobs", "type":"workday"},
    {"name":"TD Bank", "url":"https://td.wd3.myworkdayjobs.com/TD_Bank_Careers", "type":"workday"},
    {"name":"CEA", "url":"https://jobs.ashbyhq.com/centreforeffectivealtruism", "type":"ashby"},
]

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print(json.dumps({"portals": PORTALS}, indent=2))
    print("\n# Run this script with network access to discover new requisition IDs.")
    print("# Then manually verify each candidate against the rules in AGENT-RUNBOOK.md.")

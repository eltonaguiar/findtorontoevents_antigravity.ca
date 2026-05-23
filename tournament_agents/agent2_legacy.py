import logging
import json
import os
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT2_LEGACY - %(message)s')

class LegacyDashboardAgent:
    def __init__(self):
        self.endpoints = [
            'https://findtorontoevents.ca/findmutualfunds/portfolio1/',
            'https://findtorontoevents.ca/findmutualfunds/portfolio1/stats.html',
            'https://findtorontoevents.ca/findmutualfunds/portfolio1/report.html',
            'https://findtorontoevents.ca/findmutualfunds2/portfolio2/',
            'https://findtorontoevents.ca/findmutualfunds2/portfolio2/stats/index.html',
            'https://findtorontoevents.ca/findforex2/',
            'https://findtorontoevents.ca/findforex2/portfolio/',
            'https://findtorontoevents.ca/findforex2/portfolio/stats/index.html',
            'https://findtorontoevents.ca/findstocks/portfolio2/penny-stocks.html'
        ]
        self.tracking_dir = os.path.join(os.path.dirname(__file__), 'data', 'legacy')
        os.makedirs(self.tracking_dir, exist_ok=True)
        self.report = []

    def audit_endpoints(self):
        logging.info("Starting audit of legacy endpoints...")
        for url in self.endpoints:
            try:
                # We do a basic GET request to check if endpoints are alive
                response = requests.get(url, timeout=5)
                status = 'ALIVE' if response.status_code == 200 else f'DEAD_STATUS_{response.status_code}'
            except requests.RequestException as e:
                status = f'ERROR_{type(e).__name__}'
            
            logging.info(f"{url} -> {status}")
            self.report.append({
                'url': url,
                'status': status
            })

    def save_report(self):
        file_path = os.path.join(self.tracking_dir, 'legacy_audit.json')
        with open(file_path, 'w') as f:
            json.dump(self.report, f, indent=4)
        logging.info(f"Audit report saved to {file_path}")

    def run(self):
        self.audit_endpoints()
        self.save_report()

if __name__ == "__main__":
    agent = LegacyDashboardAgent()
    agent.run()

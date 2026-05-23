"""
DNA Evolution Updates - FTP Deployment Script
=============================================

Deploys DNA evolution documentation to findtorontoevents.ca/updates

Usage:
    python deploy/dna_updates_ftp_deploy.py
"""

import ftplib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Configuration
FTP_HOST = "ftp.findtorontoevents.ca"
FTP_USER = "ejaguiar"  # Update with actual credentials
FTP_PASS = ""  # Load from environment
FTP_DIR = "/public_html/updates"

LOCAL_FILES = [
    ("updates/updates_dna_evolution_systems.md", "dna_evolution_march_2026.md"),
    ("updates/dna_blueprint.html", "dna_blueprint.html"),
    ("docs/DNA_SYSTEMS_COMPREHENSIVE_REVIEW.md", "dna_systems_review.md"),
    ("docs/DNA_BLUEPRINT.md", "dna_blueprint.md"),
]

def load_ftp_credentials():
    """Load FTP credentials from environment or config file."""
    # Try environment first
    user = os.getenv("FTP_USER", "ejaguiar")
    password = os.getenv("FTP_PASSWORD", "")
    
    # Try config file
    config_path = Path.home() / ".ftp_config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            user = config.get("user", user)
            password = config.get("password", password)
    
    return user, password

def deploy_files():
    """Deploy DNA evolution documentation via FTP."""
    print("=" * 70)
    print("DNA EVOLUTION UPDATES - FTP DEPLOYMENT")
    print("=" * 70)
    
    user, password = load_ftp_credentials()
    
    if not password:
        print("Warning: No FTP password found. Set FTP_PASSWORD environment variable.")
        print("Creating local deployment package instead...")
        create_local_package()
        return
    
    try:
        print(f"\nConnecting to {FTP_HOST}...")
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(user, password)
        
        # Navigate to updates directory
        try:
            ftp.cwd(FTP_DIR)
        except:
            print(f"Creating directory: {FTP_DIR}")
            ftp.mkd(FTP_DIR)
            ftp.cwd(FTP_DIR)
        
        print(f"Connected! Current directory: {ftp.pwd()}")
        print()
        
        # Upload files
        for local_path, remote_name in LOCAL_FILES:
            local_file = Path(local_path)
            if not local_file.exists():
                print(f"⚠️  Skipping (not found): {local_path}")
                continue
            
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {remote_name}', f)
            
            size = local_file.stat().st_size
            print(f"✅ Uploaded: {remote_name} ({size:,} bytes)")
        
        # Create index file
        create_index_html(ftp)
        
        ftp.quit()
        print("\n" + "=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print(f"\nFiles available at:")
        print(f"  https://findtorontoevents.ca/updates/dna_blueprint.html")
        print(f"  https://findtorontoevents.ca/updates/dna_evolution_march_2026.md")
        
    except Exception as e:
        print(f"\n❌ FTP Error: {e}")
        print("Creating local package instead...")
        create_local_package()

def create_index_html(ftp=None):
    """Create index HTML file for updates directory."""
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>Trading System Updates | findtorontoevents</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #1a365d; }
        .update { background: #f7fafc; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #00d4aa; }
        .date { color: #718096; font-size: 0.9em; }
        a { color: #3182ce; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .tag { background: #00d4aa; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>🧬 Trading System Updates</h1>
    <p>Latest updates from the DNA Evolution Engine and algorithmic trading systems.</p>
    
    <div class="update">
        <span class="tag">NEW</span>
        <h2>DNA Evolution Systems v2.0</h2>
        <p class="date">March 9, 2026</p>
        <p>Major update deploying three powerful DNA evolution engines: Genetic Programming, MAP-Elites Quality-Diversity, and Ensemble Coevolution.</p>
        <ul>
            <li><a href="dna_blueprint.html">📊 DNA Blueprint (HTML)</a> - Complete technical specification</li>
            <li><a href="dna_evolution_march_2026.md">📝 Update Notes (MD)</a> - Detailed release notes</li>
            <li><a href="dna_systems_review.md">📈 Systems Review</a> - Comprehensive system analysis</li>
        </ul>
        <p><strong>Highlights:</strong></p>
        <ul>
            <li>500+ DNA-evolved strategies</li>
            <li>60.1% win rate (Battleground)</li>
            <li>+217% total return</li>
            <li>Prop firm challenge ready</li>
        </ul>
    </div>
    
    <div class="update">
        <h2>DNA Systems Documentation</h2>
        <p>Complete documentation for all DNA evolution systems:</p>
        <ul>
            <li><a href="dna_blueprint.md">DNA Blueprint (Markdown)</a></li>
        </ul>
    </div>
    
    <hr>
    <p style="color: #718096; font-size: 0.9em;">
        Last updated: March 9, 2026 | 
        <a href="https://findtorontoevents.ca">← Back to main site</a>
    </p>
</body>
</html>
"""
    
    if ftp:
        ftp.storbinary('STOR index.html', index_html.encode())
        print("✅ Uploaded: index.html")
    else:
        # Save locally
        output_path = Path("updates/deploy/index.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(index_html)
        print(f"✅ Created local: {output_path}")

def create_local_package():
    """Create a local deployment package."""
    print("\nCreating local deployment package...")
    
    deploy_dir = Path("updates/deploy")
    deploy_dir.mkdir(parents=True, exist_ok=True)
    
    for local_path, remote_name in LOCAL_FILES:
        src = Path(local_path)
        if src.exists():
            import shutil
            shutil.copy(src, deploy_dir / remote_name)
            print(f"✅ Copied: {remote_name}")
    
    create_index_html()
    
    print(f"\n📦 Package ready at: {deploy_dir.absolute()}")
    print("Upload these files to your FTP server manually.")

if __name__ == "__main__":
    deploy_files()

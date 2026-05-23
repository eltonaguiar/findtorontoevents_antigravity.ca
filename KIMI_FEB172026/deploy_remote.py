"""
KIMI_FEB172026 - Remote Deployment Script
Deploys the trading system to remote sites via FTP/SFTP
"""

import os
import sys
import ftplib
import paramiko
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_DEPLOY")

# Remote site configurations
SITES = {
    "findtorontoevents": {
        # 2026-04-17: was "/KIMI_FEB172026" — would land in 50webs FTP root and
        # corrupt other sites. Must include the site-prefix for 50webs deploys.
        "host": os.getenv("FTP_HOST", "ftps2.50webs.com"),
        "user": os.getenv("FTP_USER", ""),
        "pass": os.getenv("FTP_PASS", ""),
        "remote_path": "/findtorontoevents.ca/KIMI_FEB172026",
        "type": "ftp"
    },
    "tdotevent": {
        # 2026-04-17: was "/KIMI_FEB172026" — same 50webs multi-tenant trap.
        "host": os.getenv("FTP_HOST2", "ftps2.50webs.com"),
        "user": os.getenv("FTP_USER2", ""),
        "pass": os.getenv("FTP_PASS2", ""),
        "remote_path": "/tdotevent.ca/KIMI_FEB172026",
        "type": "ftp"
    },
    "torontoevent": {
        "host": os.getenv("FTP_HOST3", "torontoevent.net"),
        "user": os.getenv("FTP_USER3", ""),
        "pass": os.getenv("FTP_PASS3", ""),
        "remote_path": "/KIMI_FEB172026",
        "type": "ftp"
    }
}


def deploy_ftp(site_name, config):
    """Deploy via FTP"""
    try:
        logger.info(f"Deploying to {site_name} via FTP...")
        
        ftp = ftplib.FTP(config["host"])
        ftp.login(config["user"], config["pass"])
        
        # Create remote directory
        try:
            ftp.mkd(config["remote_path"].lstrip("/"))
        except:
            pass  # Directory may already exist
        
        ftp.cwd(config["remote_path"].lstrip("/"))
        
        # Upload files
        local_dir = Path("KIMI_FEB172026")
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                remote_file = str(relative_path).replace("\\", "/")
                
                # Create subdirectories
                parent = str(relative_path.parent).replace("\\", "/")
                if parent != ".":
                    try:
                        ftp.mkd(parent)
                    except:
                        pass
                
                # Upload file
                with open(file_path, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_file}', f)
        
        ftp.quit()
        logger.info(f"✓ Deployed to {site_name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to deploy to {site_name}: {e}")
        return False


def deploy_sftp(site_name, config):
    """Deploy via SFTP"""
    try:
        logger.info(f"Deploying to {site_name} via SFTP...")
        
        transport = paramiko.Transport((config["host"], 22))
        transport.connect(username=config["user"], password=config["pass"])
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Create remote directory
        try:
            sftp.mkdir(config["remote_path"])
        except:
            pass
        
        # Upload files
        local_dir = Path("KIMI_FEB172026")
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                remote_file = f"{config['remote_path']}/{relative_path}".replace("\\", "/")
                
                # Create subdirectories
                remote_parent = str(Path(remote_file).parent).replace("\\", "/")
                try:
                    sftp.mkdir(remote_parent)
                except:
                    pass
                
                sftp.put(str(file_path), remote_file)
        
        sftp.close()
        transport.close()
        logger.info(f"✓ Deployed to {site_name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to deploy to {site_name}: {e}")
        return False


def deploy_all():
    """Deploy to all configured sites"""
    logger.info("=" * 80)
    logger.info("KIMI_FEB172026 - Remote Deployment")
    logger.info("=" * 80)
    
    results = {}
    
    for site_name, config in SITES.items():
        if not config["user"] or not config["pass"]:
            logger.warning(f"Skipping {site_name} - no credentials")
            continue
        
        if config["type"] == "ftp":
            results[site_name] = deploy_ftp(site_name, config)
        elif config["type"] == "sftp":
            results[site_name] = deploy_sftp(site_name, config)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Deployment Summary")
    logger.info("=" * 80)
    for site, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"  {site}: {status}")
    
    return all(results.values())


def create_status_page():
    """Create a status page for remote sites"""
    status_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>KIMI_FEB172026 - Trading System Status</title>
    <meta http-equiv="refresh" content="60">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #c8c8d8; padding: 40px; }}
        h1 {{ color: #00ff88; }}
        .status {{ padding: 20px; background: #12121a; border-radius: 8px; margin: 20px 0; }}
        .online {{ color: #00ff88; }}
        .offline {{ color: #ff4757; }}
        .warning {{ color: #ffd700; }}
        pre {{ background: #1a1a25; padding: 15px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>⚡ KIMI_FEB172026 Trading System</h1>
    <div class="status">
        <h2>System Status</h2>
        <p>Last updated: {datetime.now().isoformat()}</p>
        <p class="online">● Online</p>
        <p>Version: 11.0.0-INTEGRATED</p>
    </div>
    <div class="status">
        <h2>Quick Links</h2>
        <ul>
            <li><a href="/KIMI_FEB172026/data/latest_signals.json">Latest Signals</a></li>
            <li><a href="/KIMI_FEB172026/data/system_status.json">System Status</a></li>
            <li><a href="/KIMI_FEB172026/data/validation_results.json">Validation Results</a></li>
        </ul>
    </div>
    <div class="status">
        <h2>Documentation</h2>
        <ul>
            <li><a href="FINAL_SUMMARY.md">System Summary</a></li>
            <li><a href="VALIDATION_README.md">Validation Guide</a></li>
            <li><a href="README.md">Full Documentation</a></li>
        </ul>
    </div>
</body>
</html>"""
    
    with open("KIMI_FEB172026/index.html", "w") as f:
        f.write(status_html)
    
    logger.info("Created status page: KIMI_FEB172026/index.html")


if __name__ == "__main__":
    create_status_page()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--create-status-only":
        sys.exit(0)
    
    success = deploy_all()
    sys.exit(0 if success else 1)

"""
Migration Script: Replace yfinance calls with EnhancedDataFetcher

Scans codebase for yfinance usage and provides migration recommendations.
Can also auto-migrate simple cases.
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YFinanceMigrator:
    """
    Helps migrate from yfinance to EnhancedDataFetcher.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.yfinance_pattern = re.compile(r'import\s+yfinance|from\s+yfinance|yf\.Ticker|yf\.download')
        self.findings: List[Dict] = []
    
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for yfinance usage."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except:
            return findings
        
        # Check for yfinance imports
        for i, line in enumerate(lines, 1):
            if self.yfinance_pattern.search(line):
                findings.append({
                    'file': str(file_path),
                    'line': i,
                    'code': line.strip(),
                    'type': 'import' if 'import' in line else 'usage'
                })
        
        return findings
    
    def scan_project(self) -> Dict:
        """Scan entire project for yfinance usage."""
        logger.info("Scanning project for yfinance usage...")
        
        all_findings = []
        files_scanned = 0
        
        # Scan Python files
        for py_file in self.project_root.rglob('*.py'):
            # Skip certain directories
            if any(skip in str(py_file) for skip in ['__pycache__', '.venv', 'venv', 'node_modules']):
                continue
            
            findings = self.scan_file(py_file)
            if findings:
                all_findings.extend(findings)
            files_scanned += 1
        
        self.findings = all_findings
        
        # Group by file
        by_file = {}
        for finding in all_findings:
            file_path = finding['file']
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(finding)
        
        logger.info(f"Scanned {files_scanned} files, found yfinance in {len(by_file)} files")
        
        return {
            'total_findings': len(all_findings),
            'files_affected': len(by_file),
            'by_file': by_file
        }
    
    def generate_migration_guide(self) -> str:
        """Generate migration guide for findings."""
        if not self.findings:
            return "No yfinance usage found. Project is already migrated!"
        
        guide = ["# YFinance to EnhancedDataFetcher Migration Guide\n"]
        guide.append("## Files Requiring Migration\n")
        
        by_file = {}
        for finding in self.findings:
            file_path = finding['file']
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(finding)
        
        for file_path, findings in sorted(by_file.items()):
            guide.append(f"\n### {file_path}")
            guide.append("```python")
            for f in findings[:10]:  # Show first 10
                guide.append(f"# Line {f['line']}: {f['code']}")
            if len(findings) > 10:
                guide.append(f"# ... and {len(findings) - 10} more occurrences")
            guide.append("```")
            
            # Provide migration template
            guide.append("\n**Migration Template:**")
            guide.append("```python")
            guide.append("# OLD (yfinance)")
            guide.append("import yfinance as yf")
            guide.append("data = yf.download('BTC-USD', period='1d', interval='1h')")
            guide.append("")
            guide.append("# NEW (EnhancedDataFetcher)")
            guide.append("from data_fetcher_enhanced import EnhancedDataFetcher")
            guide.append("fetcher = EnhancedDataFetcher()")
            guide.append("data = await fetcher.fetch_crypto_data('BTCUSDT', timeframe='1h', limit=24)")
            guide.append("```")
        
        guide.append("\n## Quick Migration Steps\n")
        guide.append("1. Replace `import yfinance as yf` with `from data_fetcher_enhanced import EnhancedDataFetcher`")
        guide.append("2. Replace `yf.download()` with `fetcher.fetch_crypto_data()` or `fetcher.fetch_stock_data()`")
        guide.append("3. Add `await` since EnhancedDataFetcher uses async")
        guide.append("4. Handle the DataFrame format (should be similar)")
        
        return '\n'.join(guide)
    
    def auto_migrate_simple(self, file_path: Path) -> bool:
        """
        Attempt to auto-migrate simple yfinance usage.
        Returns True if migration was successful.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple patterns that can be auto-migrated
            original = content
            
            # Replace imports
            content = re.sub(
                r'import yfinance as yf\n',
                'from data_fetcher_enhanced import EnhancedDataFetcher\n',
                content
            )
            
            content = re.sub(
                r'from yfinance import.*?\n',
                'from data_fetcher_enhanced import EnhancedDataFetcher\n',
                content
            )
            
            # If changes were made, add fetcher initialization
            if content != original:
                # Add fetcher initialization after imports
                content = re.sub(
                    r'(from data_fetcher_enhanced import EnhancedDataFetcher\n)',
                    r'\1\nfetcher = EnhancedDataFetcher()\n',
                    content
                )
                
                # Save backup
                backup_path = file_path.with_suffix('.py.bak')
                with open(backup_path, 'w') as f:
                    f.write(original)
                
                # Save migrated version
                with open(file_path, 'w') as f:
                    f.write(content)
                
                logger.info(f"Auto-migrated: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Auto-migration failed for {file_path}: {e}")
            return False
    
    def create_migration_report(self, output_path: str = "YFINANCE_MIGRATION_REPORT.md"):
        """Create detailed migration report."""
        report = self.generate_migration_guide()
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Migration report saved to {output_path}")
        return output_path


def main():
    """Run migration scanner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate from yfinance to EnhancedDataFetcher')
    parser.add_argument('--scan', action='store_true', help='Scan project for yfinance usage')
    parser.add_argument('--auto-migrate', action='store_true', help='Auto-migrate simple cases')
    parser.add_argument('--report', action='store_true', help='Generate migration report')
    
    args = parser.parse_args()
    
    migrator = YFinanceMigrator()
    
    if args.scan or args.report or not any([args.scan, args.auto_migrate, args.report]):
        # Default to scan
        results = migrator.scan_project()
        print(f"\nFound {results['total_findings']} yfinance usages in {results['files_affected']} files")
        
        if results['by_file']:
            print("\nFiles affected:")
            for file_path, findings in sorted(results['by_file'].items(), 
                                             key=lambda x: len(x[1]), 
                                             reverse=True)[:10]:
                print(f"  {file_path}: {len(findings)} occurrences")
    
    if args.report:
        report_path = migrator.create_migration_report()
        print(f"\nReport saved: {report_path}")
    
    if args.auto_migrate:
        print("\nAuto-migrating simple cases...")
        results = migrator.scan_project()
        migrated = 0
        
        for file_path in results['by_file'].keys():
            if migrator.auto_migrate_simple(Path(file_path)):
                migrated += 1
        
        print(f"Auto-migrated {migrated} files")


if __name__ == '__main__':
    main()

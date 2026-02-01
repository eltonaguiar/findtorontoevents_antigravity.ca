#!/usr/bin/env python3
"""
Simple HTTP server for testing events loading
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
from pathlib import Path

PORT = 9000

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

def main():
    # Change to workspace root directory
    workspace_root = Path(__file__).parent.parent
    os.chdir(workspace_root)
    
    print(f"Starting server at http://localhost:{PORT}")
    print(f"Serving files from: {workspace_root}")
    
    server = HTTPServer(('127.0.0.1', PORT), CORSRequestHandler)
    try:
        print("Server is running. Press Ctrl+C to stop.")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    main()
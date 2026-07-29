#!/usr/bin/env python3
"""One-shot HTTP server — serves WindowsHelper.exe on port 8888"""
import http.server
import socketserver
import os

PORT = 8888
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist"))

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[+] {self.client_address[0]} - {args[0][:80]}")

print(f"[*] Serving WindowsHelper.exe on :{PORT}")
print(f"[*] Files: {', '.join(os.listdir('.'))}")
print()

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    httpd.serve_forever()

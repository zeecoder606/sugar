import mimetypes
import threading
import BaseHTTPServer
import os

from jarabe.model import bundleregistry

class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        splitted = self.path.split("/")
        bundle_id = splitted[1]
        path = splitted[2:]

        registry = bundleregistry.get_registry()
        bundle = registry.get_bundle(bundle_id)

        file_path = os.path.join(bundle.get_path(), *path)
        with open(file_path) as f:
            self.send_response(200)
            self.send_header('Content-type', mimetypes.guess_type(file_path))
            self.end_headers()
            self.wfile.write(f.read())
 
class ServerThread(threading.Thread):
    def run(self):
        httpd = BaseHTTPServer.HTTPServer(('', 8000), HTTPRequestHandler)
        httpd.serve_forever()

def start_server():
    thread = ServerThread()
    thread.start()

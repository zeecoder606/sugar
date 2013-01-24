import mimetypes
import threading
import BaseHTTPServer
import os

from jarabe.model import bundleregistry
from jarabe import config

class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        splitted = self.path.split("/")
        if splitted[1] == "toolkit":
            base_path = config.html_toolkit_path
        else:
            registry = bundleregistry.get_registry()
            bundle = registry.get_bundle(splitted[1])
            base_path = bundle.get_path()

        file_path = os.path.join(base_path, *splitted[2:])
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

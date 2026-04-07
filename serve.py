import os, http.server, socketserver
os.chdir('/Users/jessicauviovo/Documents/vis-code-evolution/public')
PORT = 3456
with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    httpd.serve_forever()

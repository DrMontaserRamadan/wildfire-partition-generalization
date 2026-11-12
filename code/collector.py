import http.server, socketserver, json, os, re, sys
os.makedirs("corpus/ft", exist_ok=True)
PORT=8778
class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Access-Control-Allow-Methods","POST,OPTIONS")
        self.send_header("Access-Control-Allow-Private-Network","true")
        self.send_header("Access-Control-Max-Age","86400")
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()
    def do_POST(self):
        n=int(self.headers.get("Content-Length",0))
        try:
            payload=json.loads(self.rfile.read(n).decode("utf-8","ignore"))
            items=payload if isinstance(payload,list) else [payload]
            saved=[]
            for it in items:
                key=re.sub(r"[^A-Za-z0-9_.-]","_",str(it.get("key","")))[:64]
                txt=it.get("text") or ""
                if key and len(txt)>4000:
                    open(f"corpus/ft/{key}.txt","w",encoding="utf-8").write(txt)
                    saved.append(key)
            self.send_response(200); self._cors()
            self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"saved":len(saved),"keys":saved}).encode())
            print(f"saved {len(saved)}: {saved}",flush=True)
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(str(e).encode()); print("ERR",e,flush=True)
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
with socketserver.TCPServer(("127.0.0.1",PORT),H) as s:
    print(f"collector listening on {PORT}",flush=True); s.serve_forever()

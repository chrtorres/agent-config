"""Serve the review and generated fixture over an ephemeral loopback port."""
from argparse import ArgumentParser
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes
import re
from urllib.parse import urlsplit


def handler(assets, video=None, source=None):
    app = Path(__file__).resolve().parent
    files = {"/": app/"index.html"}
    files.update({"/"+name:app/name for name in ("app.mjs","motion.mjs","render.mjs","style.css")})
    files["/video.mp4"]=video if video is not None else assets/"video.mp4"
    if source is not None:
        files["/source.mp4"]=source
    files.update({"/timeline/"+p.name:p for p in (assets/"timeline").iterdir() if p.is_file()})

    class Review(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.respond(False)

        def do_GET(self):
            self.respond(True)

        def respond(self, body):
            target=files.get(urlsplit(self.path).path)
            if target is None or not target.is_file():
                self.send_error(404)
                return
            size=target.stat().st_size
            interval=self.headers.get("Range")
            first,last=0,size-1
            if interval:
                match=re.fullmatch(r"bytes=(\d+)-(\d*)",interval)
                if match:
                    first=int(match[1])
                    last=min(last,int(match[2])) if match[2] else last
                if not match or first>last:
                    self.send_response(416)
                    self.send_header("Content-Range",f"bytes */{size}")
                    self.end_headers()
                    return
            self.send_response(206 if interval else 200)
            self.send_header("Content-Type", "text/javascript" if target.suffix==".mjs" else mimetypes.guess_type(target)[0])
            self.send_header("Accept-Ranges","bytes")
            self.send_header("Permissions-Policy","gamepad=(self)")
            self.send_header("Content-Length",str(last-first+1))
            if interval:
                self.send_header("Content-Range",f"bytes {first}-{last}/{size}")
            self.end_headers()
            if body:
                with target.open("rb") as f,suppress(BrokenPipeError,ConnectionResetError):
                    f.seek(first)
                    remaining=last-first+1
                    while remaining and (block:=f.read(min(remaining,65536))):
                        self.wfile.write(block)
                        remaining-=len(block)
    return Review


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("assets",type=Path)
    parser.add_argument("--video",type=Path,help="MP4 matching the supplied timeline")
    parser.add_argument("--source",type=Path,help="Untouched input MP4 to serve at /source.mp4")
    parser.add_argument("--port",type=int,default=0)
    args=parser.parse_args()
    for media in (args.video,args.source):
        if media is not None and not media.is_file():
            parser.error(f"File not found: {media}")
    with ThreadingHTTPServer(("127.0.0.1",args.port),handler(args.assets,args.video,args.source)) as server:
        print(f"http://127.0.0.1:{server.server_port}/",flush=True)
        server.serve_forever()

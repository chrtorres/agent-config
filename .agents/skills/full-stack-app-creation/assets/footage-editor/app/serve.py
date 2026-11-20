"""Serve the review and private footage assets over an ephemeral loopback port."""
from argparse import ArgumentParser
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import re
from urllib.parse import urlsplit


def handler(assets, video=None, source=None, uhd=None, regions=None, skin=None, cleanup_tracks=None, motion_study=None, motion_splats=None):
    app = Path(__file__).resolve().parent
    files = {"/": app/"index.html", "/4k/": app/"uhd.html"}
    modules = ("app.mjs","motion.mjs","render.mjs","regions.mjs","inspect.mjs","cleanup.mjs",
               "transport.mjs","secondary.mjs","splats.mjs","stage-zoom.mjs","picking.mjs","point-regions.mjs")
    files.update({"/"+name:app/name for name in (*modules,"style.css")})
    files["/video.mp4"]=video if video is not None else assets/"video.mp4"
    if source is not None:
        files["/source.mp4"]=source
    uhd = uhd if uhd is not None else assets/"4k.mp4"
    if uhd.is_file():
        files["/4k.mp4"]=uhd
    timeline = assets/"timeline"
    files["/timeline/timeline.json"] = timeline/"timeline.json"
    if files["/timeline/timeline.json"].is_file():
        manifest = json.loads(files["/timeline/timeline.json"].read_text())
        for name, *_ in manifest["pages"]:
            if Path(name).name == name:
                files["/timeline/"+name] = timeline/name

    if regions is not None:
        files["/regions.json"]=regions
    if cleanup_tracks is not None:
        files["/cleanup-tracks.json"]=cleanup_tracks
    if motion_study is not None:
        files["/motion-study.json"]=motion_study
    if motion_splats is not None:
        files["/motion-splats.json"]=motion_splats
    if skin is not None:
        files.update({"/skin/"+p.name:p for p in skin.glob("skin-*.png") if p.is_file()})

    class Review(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

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
            self.send_header("Cache-Control","no-store")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("X-Content-Type-Options","nosniff")
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
    parser.add_argument("--uhd",type=Path,help="Portrait 4K MP4 on the same timeline")
    parser.add_argument("--regions",type=Path,help="Python-generated augmentation regions")
    parser.add_argument("--skin",type=Path,help="Directory of Python-generated skin mask pages")
    parser.add_argument("--cleanup-tracks",type=Path,help="Joint-relative cleanup track sidecar")
    parser.add_argument("--motion-study",type=Path,help="Recorded secondary motion measurements")
    parser.add_argument("--motion-splats",type=Path,help="Recorded temporal Gaussian tracks")
    parser.add_argument("--port",type=int,default=0)
    args=parser.parse_args()
    for media in (args.video,args.source,args.uhd,args.regions,args.cleanup_tracks,args.motion_study,args.motion_splats):
        if media is not None and not media.is_file():
            parser.error(f"File not found: {media}")
    with ThreadingHTTPServer(("127.0.0.1",args.port),handler(args.assets,args.video,args.source,args.uhd,args.regions,args.skin,args.cleanup_tracks,args.motion_study,args.motion_splats)) as server:
        print(f"http://127.0.0.1:{server.server_port}/",flush=True)
        server.serve_forever()

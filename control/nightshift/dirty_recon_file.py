#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
ps=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("knowledge/recon/")]
if not ps: raise SystemExit(260)
if any(x=="knowledge/recon/opportunity_graph.json" for x in ps): raise SystemExit(261)
if any(x=="knowledge/recon/watchlist.json" for x in ps): raise SystemExit(262)
if any(x.startswith("knowledge/recon/seeds/") for x in ps): raise SystemExit(263)
raise SystemExit(264)

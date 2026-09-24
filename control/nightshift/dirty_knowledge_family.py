#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
ps=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("knowledge/")]
if not ps: raise SystemExit(241)
groups=[("candidates/",242),("coverage/",243),("cross_venue/",244),("dark_market_intelligence/",245),("documents/",246),("gemini/",247),("kalshi/",248),("polymarket/",249),("public_research/",250),("recon/",251),("regulatory/",252),("research/",253),("research_os/",254),("runs/",255)]
for pref,code in groups:
 if any(x.startswith("knowledge/"+pref) for x in ps): raise SystemExit(code)
# remaining groups compressed
if any(x.startswith("knowledge/sources/") for x in ps): raise SystemExit(239)
if any(x.startswith("knowledge/strategy_benchmarks/") for x in ps): raise SystemExit(238)
if any(x.startswith("knowledge/watch/") for x in ps): raise SystemExit(237)
if any(x.startswith("knowledge/weak_signals/") for x in ps): raise SystemExit(236)
if any(x.startswith("knowledge/nadex/") for x in ps): raise SystemExit(235)
raise SystemExit(234)

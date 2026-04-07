"""SpikeCanvas Agent Infrastructure Validation. Run: python tests/test_agent_infrastructure.py"""
import os, re, sys, json

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT = os.path.join(REPO, ".agent")
SKILLS = os.path.join(AGENT, "skills")
WORKFLOWS = os.path.join(AGENT, "workflows")
SKILL_NAMES = ["analysis-visualizer","batch-auditor","dashboard-operator","data-investigator",
    "experiment-educator","performance-profiler","pipeline-developer","pipeline-operator","repo-map-updater"]
WF_NAMES = ["submit-sorting-job.md","monitor-jobs.md"]
MAPS = [os.path.join(SKILLS,"repo-map-updater","COMPONENT_MAP.md"),os.path.join(SKILLS,"repo-map-updater","CONFIG_MAP.md")]
BANNED = ["spikelab","SpikeLab","SPIKELAB","spike_lab","spike-lab"]
SRC_REFS = ["kilosort2_simplified.py","kilosort2_params.py","run.sh","mqtt_listener.py",
    "splitter_fanout.py","k8s_kilosort2.py","job_center.py","values.py","app.py","sorting_job_info.json"]

passed=failed=0; errors=[]
def ok(l): global passed; passed+=1; print(f"  PASS  {l}")
def fail(l,d=""): global failed; failed+=1; m=f"  FAIL  {l}"+(f" -- {d}" if d else ""); errors.append(m); print(m)
def parse_fm(t):
    if not t.startswith("---"): return None
    p=t.split("---",2)
    if len(p)<3: return None
    fm={}
    for line in p[1].strip().splitlines():
        if ":" in line: k,v=line.split(":",1); fm[k.strip()]=v.strip()
    return fm

# [1] Directories
print("\n[1] Directories")
for d,n in [(AGENT,".agent"),(SKILLS,"skills"),(WORKFLOWS,"workflows")]:
    ok(n) if os.path.isdir(d) else fail(n+" missing")

# [2] Skills exist
print("\n[2] Skills")
for s in SKILL_NAMES:
    p=os.path.join(SKILLS,s,"SKILL.md")
    ok(s) if os.path.isfile(p) else fail(s+" missing")

# [3] Frontmatter
print("\n[3] Frontmatter")
for s in SKILL_NAMES:
    p=os.path.join(SKILLS,s,"SKILL.md")
    if not os.path.isfile(p): continue
    with open(p,"r",encoding="utf-8") as f: fm=parse_fm(f.read())
    if not fm: fail(s,"bad frontmatter"); continue
    ok(f"{s} name") if fm.get("name")==s else fail(s,f"name={fm.get('name')}")
    ok(f"{s} desc") if fm.get("description") else fail(s,"no description")

# [4] Workflows
print("\n[4] Workflows")
for w in WF_NAMES:
    p=os.path.join(WORKFLOWS,w)
    if not os.path.isfile(p): fail(w+" missing"); continue
    ok(w)
    with open(p,"r",encoding="utf-8") as f: fm=parse_fm(f.read())
    ok(f"{w} desc") if fm and fm.get("description") else fail(w,"no description")

# [5] Maps
print("\n[5] Maps")
for mp in MAPS:
    n=os.path.basename(mp); sz=os.path.getsize(mp) if os.path.isfile(mp) else 0
    ok(f"{n} ({sz//1024}KB)") if sz>1000 else fail(n,f"{sz}B")

# [6] Security
print("\n[6] Security")
violations=[]
for root,_,files in os.walk(AGENT):
    for fn in files:
        fp=os.path.join(root,fn)
        try:
            with open(fp,"r",encoding="utf-8") as f: c=f.read()
            for t in BANNED:
                if t in c: violations.append((os.path.relpath(fp,REPO),t))
        except: pass
ok("No banned terms") if not violations else [fail(f"'{t}' in {p}") for p,t in violations]

# [7] Component map refs
print("\n[7] Component Map Refs")
cm=os.path.join(SKILLS,"repo-map-updater","COMPONENT_MAP.md")
if os.path.isfile(cm):
    with open(cm,"r",encoding="utf-8") as f: cc=f.read()
    for s in SRC_REFS: ok(s) if s in cc else fail(s+" not in COMPONENT_MAP")

# [8] Tag alignment
print("\n[8] Tag Alignment")
cfg=os.path.join(SKILLS,"repo-map-updater","CONFIG_MAP.md")
if os.path.isfile(cfg):
    with open(cfg,"r",encoding="utf-8") as f: cc=f.read()
    tags=re.findall(r"braingeneers/ephys_pipeline:(v[\d.]+)",cc)
    u=set(tags)
    ok(f"All aligned: {u.pop()} ({len(tags)} refs)") if len(u)==1 else fail("Mismatch",str(u))

# [9] Config vs source
print("\n[9] Config vs Source")
jp=os.path.join(REPO,"Services","Spike_Sorting_Listener","src","sorting_job_info.json")
if os.path.isfile(jp) and os.path.isfile(cfg):
    with open(jp) as f: ji=json.load(f)
    img=ji.get("image","")
    ok(f"Image '{img}' in CONFIG_MAP") if img in cc else fail("Image drift",img)

# [10] Cross-refs
print("\n[10] Cross-refs")
existing={s for s in SKILL_NAMES if os.path.isfile(os.path.join(SKILLS,s,"SKILL.md"))}
ref_re=re.compile(r"([\w-]+)\s+skill")
for s in existing:
    with open(os.path.join(SKILLS,s,"SKILL.md"),"r",encoding="utf-8") as f: c=f.read()
    for r2 in ref_re.findall(c):
        if r2 in existing: ok(f"{s}->{r2}")
        elif r2 in SKILL_NAMES: fail(f"{s}->{r2}","missing target")

# [11] Content quality
print("\n[11] Quality")
for s in SKILL_NAMES:
    p=os.path.join(SKILLS,s,"SKILL.md")
    if not os.path.isfile(p): continue
    with open(p,"r",encoding="utf-8") as f: lines=f.readlines()
    ok(f"{s} {len(lines)}L") if len(lines)>=50 else fail(s,f"only {len(lines)} lines")
    secs=sum(1 for l in lines if l.startswith("## "))
    ok(f"{s} {secs}S") if secs>=3 else fail(s,f"only {secs} sections")

# Summary
print(f"\n{'='*60}\nResults: {passed}/{passed+failed} passed, {failed} failed")
if errors: print("\nFailures:"); [print(f"  {e}") for e in errors]
print("="*60)
sys.exit(0 if failed==0 else 1)

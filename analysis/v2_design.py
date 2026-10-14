"""The spreads the v2 wording count was chosen from (see REPRODUCE-v2.md).

  python3 analysis/v2_design.py

Reads Jev's three-pass v1 rows (the v1 grid, the 16 added wordings, both footbridge arms) and prints,
per scenario: wordings, the spread of the score across wordings at a fixed count (orders averaged),
the order spread within a wording, the share of cells at N >= 2 that act, and the spread across
wordings of each wording's share of acting cells, which sets the interval width per wording count.
"""
import glob
import json
import pathlib
import statistics as st
from collections import defaultdict

T = str(pathlib.Path(__file__).resolve().parent.parent / "results")
files = glob.glob(T+"/raw/jev-pass-[abc].jsonl")+glob.glob(T+"/raw/jev-extra-pass-[abc].jsonl")+glob.glob(T+"/footbridge-*/jev-*-pass-[abc].jsonl")
per = defaultdict(list)
for f in files:
    for l in open(f):
        r=json.loads(l); per[(r["scenario"],r["wording"],r["order"],r["n"])].append(r["answers"]["pull"])
# replay SD
rep=[st.pstdev(v) for v in per.values() if len(v)==3]
print("cells",len(per),"replay mean abs dev from cell mean", round(st.mean(sum(abs(x-st.mean(v)) for x in v)/3 for v in per.values() if len(v)==3),4), "replay sd", round(st.mean(rep),4))
sc={k:st.mean(v) for k,v in per.items()}
scen=sorted({k[0] for k in sc})
print("scenario | wordings | between-wording SD of score (orders averaged, mean over N>=1) | order SD within wording | share of wording-orders acting, N>=2 | SD across wordings of per-wording act share")
for s in scen:
    ws=sorted({k[1] for k in sc if k[0]==s}); ns=sorted({k[3] for k in sc if k[0]==s})
    bw=[];ow=[]
    for n in ns:
        if n<1: continue
        vals=[]
        for w in ws:
            o=[sc[(s,w,oo,n)] for oo in ("o1","o2") if (s,w,oo,n) in sc]
            if len(o)==2: vals.append(st.mean(o)); ow.append(abs(o[0]-o[1])/2)
        if len(vals)>1: bw.append(st.pstdev(vals))
    share=[];
    for w in ws:
        a=[sc[k]>0.5 for k in sc if k[0]==s and k[1]==w and k[3]>=2]
        if a: share.append(sum(a)/len(a))
    acts=[sc[k]>0.5 for k in sc if k[0]==s and k[3]>=2]
    print(s,len(ws),round(st.mean(bw),3) if bw else None,round(st.mean(ow),3) if ow else None, round(sum(acts)/len(acts),3) if acts else None, round(st.pstdev(share),3) if len(share)>1 else None, len(ns))

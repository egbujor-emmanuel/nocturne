"""END-TO-END FEASIBILITY SPIKE - local only, publishes nothing.
Proves every moving part of NOCTURNE works together:
  live price -> real depth -> news -> Qwen judgement -> noise score -> 4 output lines
"""
import json,urllib.request,urllib.parse,datetime as dt,re,statistics as st,time

ET=dt.timezone(dt.timedelta(hours=-4))
import os
def _key():
    k=os.environ.get("QWEN_API_KEY")
    if not k:
        for ln in open(os.path.join(os.path.dirname(__file__),"..",".env"),encoding="utf8"):
            if ln.startswith("QWEN_API_KEY="): k=ln.split("=",1)[1].strip()
    if not k: raise SystemExit("QWEN_API_KEY not set")
    return k
KEY=_key()
UA={"User-Agent":"Mozilla/5.0"}

def jget(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))

# ---------- 1. live price + real executable depth ----------
def depth_report(sym,move_pct=0.5):
    ob=jget(f"https://api.bitget.com/api/v2/spot/market/orderbook?symbol={sym}&type=step0&limit=150")["data"]
    asks=[(float(p),float(q)) for p,q in ob["asks"]]
    if not asks: return None
    best=asks[0][0]; lim=best*(1+move_pct/100)
    shares=sum(q for p,q in asks if p<=lim)
    return dict(best=best,shares=shares,usd=shares*best,
                spread=(float(ob["bids"][0][0]) if ob.get("bids") else best))

# ---------- 2. news ----------
def news(ticker,name,n=5):
    q=urllib.parse.quote(f"{name} stock")
    x=urllib.request.urlopen(urllib.request.Request(
        f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en",headers=UA),timeout=25).read().decode("utf8","ignore")
    items=re.findall(r"<item>(.*?)</item>",x,re.S)
    out=[]
    for it in items[:n]:
        t=re.search(r"<title>(.*?)</title>",it,re.S)
        d=re.search(r"<pubDate>(.*?)</pubDate>",it,re.S)
        if t: out.append((re.sub(r"&#?\w+;","",t.group(1)).strip(),(d.group(1) if d else "")))
    return out

# ---------- 3. Qwen judgement ----------
def qwen(prompt):
    body=json.dumps({"model":"qwen3.8-max",
        "messages":[{"role":"system","content":"You are a terse equity analyst. Reply ONLY with compact JSON."},
                    {"role":"user","content":prompt}],"max_tokens":300}).encode()
    r=urllib.request.Request("https://hackathon.bitgetops.com/v1/chat/completions",data=body,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    t0=time.time()
    d=json.load(urllib.request.urlopen(r,timeout=90))
    return d["choices"][0]["message"]["content"], d["usage"]["total_tokens"], time.time()-t0

# ---------- 4. historical void move (last completed weekend) ----------
def last_void(sym):
    bars=json.load(open(f"data/1h/{sym}.json"))
    b={dt.datetime.fromtimestamp(int(r[0])/1000,ET):(float(r[4]),float(r[6])) for r in bars}
    fri=max(t.date() for t in b if t.weekday()==4)
    sun=fri+dt.timedelta(days=2)
    def near(day,h):
        for k in range(4):
            t=dt.datetime.combine(day,dt.time(h,0),ET)-dt.timedelta(hours=k)
            if t in b: return b[t][0]
    pf,pv=near(fri,15),near(sun,19)
    vol=sum(q for t,(c,q) in b.items()
            if dt.datetime.combine(fri,dt.time(20,0),ET)<=t<dt.datetime.combine(sun,dt.time(19,0),ET))
    return fri,pf,pv,(pv/pf-1)*100,vol

NAMES={"RNVDAUSDT":"Nvidia","RTSLAUSDT":"Tesla","RAAPLUSDT":"Apple"}
print("="*74)
print("NOCTURNE END-TO-END SPIKE   ",dt.datetime.now(ET).strftime("%a %Y-%m-%d %H:%M ET"))
print("="*74)
for sym,name in NAMES.items():
    print(f"\n### {name} ({sym})")
    d=depth_report(sym)
    fri,pf,pv,movepct,vol=last_void(sym)
    hl=news(sym,name,4)
    print(f"  live best ask      : ${d['best']:.2f}")
    print(f"  depth to +0.5%     : {d['shares']:,.1f} shares  (${d['usd']:,.0f})")
    print(f"  last void window   : Fri {fri} close ${pf:.2f} -> Sun 19:00 ${pv:.2f}  ({movepct:+.2f}%)")
    print(f"  void window volume : ${vol:,.0f}")
    print(f"  headlines pulled   : {len(hl)}")
    for t,_ in hl[:2]: print(f"     - {t[:78]}")
    prompt=(f"{name} moved {movepct:+.2f}% while the US market was closed, on only "
            f"${vol:,.0f} of total trading volume. Recent headlines:\n"
            + "\n".join(f"- {t}" for t,_ in hl)
            + "\n\nReturn JSON: {\"justified\":true|false,\"noise_score\":0-100,\"reason\":\"<12 words\"} "
              "where noise_score is how likely this move is meaningless noise rather than real information.")
    try:
        txt,tok,el=qwen(prompt)
        m=re.search(r"\{.*\}",txt,re.S)
        j=json.loads(m.group(0)) if m else {}
        print(f"  QWEN -> noise_score={j.get('noise_score')}  justified={j.get('justified')}  ({tok} tok, {el:.1f}s)")
        print(f"          reason: {j.get('reason')}")
    except Exception as e:
        print("  QWEN FAILED:",e)
print("\n"+"="*74)

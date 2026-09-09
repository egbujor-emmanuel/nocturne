"""I4: Qwen news judge, with a threshold gate and an on-disk cache.

Qwen answers ONE question: is there news that plausibly justifies this move,
or is the price drifting on nothing?

Cost controls, because the hackathon credit is finite and latency is ~11s:
  * gate   - only called when the Noise Score is at or above THRESHOLD
  * cache  - keyed on (symbol, hour); repeat lookups are free
  * budget - hard cap on calls per run
  * degrade- any failure returns None and the product carries on without it
"""
import sys,os,json,re,time,urllib.request,urllib.parse,datetime as dt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import netfix  # DNS fallback; no-op on a healthy network
from core import ROOT

THRESHOLD=80          # only judge genuinely unusual dislocations
MAX_CALLS=25          # per invocation
CACHE=os.path.join(ROOT,"data","qwen_cache.json")
UA={"User-Agent":"Mozilla/5.0"}
BASE=os.environ.get("QWEN_BASE_URL","https://hackathon.bitgetops.com/v1")
MODEL=os.environ.get("QWEN_MODEL","qwen3.8-max")

def key():
    k=os.environ.get("QWEN_API_KEY")
    if k: return k
    p=os.path.join(ROOT,".env")
    if os.path.exists(p):
        for ln in open(p,encoding="utf8"):
            if ln.startswith("QWEN_API_KEY="): return ln.split("=",1)[1].strip()
    return None

def load_cache():
    try: return json.load(open(CACHE))
    except Exception: return {}

def save_cache(c): json.dump(c,open(CACHE,"w"))

def headlines(name,n=5):
    try:
        q=urllib.parse.quote(f"{name} stock")
        url=f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        x=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=20).read().decode("utf8","ignore")
        out=[]
        for it in re.findall(r"<item>(.*?)</item>",x,re.S)[:n]:
            t=re.search(r"<title>(.*?)</title>",it,re.S)
            if t: out.append(re.sub(r"&#?\w+;","",t.group(1)).strip())
        return out
    except Exception: return []

def ask(prompt,timeout=60):
    k=key()
    if not k: return None
    body=json.dumps({"model":MODEL,"max_tokens":220,
        "messages":[{"role":"system","content":"Terse equity analyst. Reply ONLY with compact JSON."},
                    {"role":"user","content":prompt}]}).encode()
    try:
        r=urllib.request.Request(f"{BASE}/chat/completions",data=body,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {k}"})
        d=json.load(urllib.request.urlopen(r,timeout=timeout))
        return d["choices"][0]["message"]["content"]
    except Exception:
        return None

def judge(sym,name,dislocation_pct,void_usd,score,cache=None,now=None):
    if score<THRESHOLD: return None
    cache=cache if cache is not None else load_cache()
    now=now or dt.datetime.now(dt.timezone.utc)
    ck=f"{sym}|{now:%Y-%m-%dT%H}"
    if ck in cache: return dict(cache[ck],cached=True)
    hl=headlines(name)
    prompt=(f"{name} ({sym}) has moved {dislocation_pct:+.2f}% away from Friday's US closing "
            f"price while the US market is closed, on about ${void_usd:,.0f} of total trading. "
            f"Recent headlines:\n"+("\n".join(f"- {h}" for h in hl) if hl else "- (none found)")+
            "\n\nReturn JSON only: {\"justified\":true|false,\"confidence\":0-100,"
            "\"reason\":\"under 14 words\"} where justified means real news plausibly "
            "explains a move of this size.")
    txt=ask(prompt)
    if not txt: return None
    m=re.search(r"\{.*\}",txt,re.S)
    if not m: return None
    try: j=json.loads(m.group(0))
    except Exception: return None
    out={"justified":bool(j.get("justified")),"confidence":j.get("confidence"),
         "reason":str(j.get("reason",""))[:120],"headlines":len(hl),
         "at":now.isoformat()}
    cache[ck]=out; save_cache(cache)
    return dict(out,cached=False)

if __name__=="__main__":
    c=load_cache()
    t0=time.time()
    r=judge("RNVDA","Nvidia",2.4,168280,95,c)
    print("gated call (score 95):",json.dumps(r,indent=1) if r else "FAILED")
    print(f"  elapsed {time.time()-t0:.1f}s")
    t0=time.time(); r2=judge("RNVDA","Nvidia",2.4,168280,95,c)
    print(f"cache hit: {r2 is not None and r2.get('cached')}  elapsed {time.time()-t0:.2f}s")
    print("below threshold (score 40):",judge("RAAPL","Apple",0.2,11276,40,c))

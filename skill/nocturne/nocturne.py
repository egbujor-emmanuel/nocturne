"""Tiny client for the NOCTURNE public API. No key, no deps beyond stdlib.

  python nocturne.py            -> session state + the 10 riskiest right now
  python nocturne.py RNVDA      -> one symbol
"""
import sys,json,urllib.request
BASE="https://egbujor-emmanuel.github.io/nocturne/api/v1"

def get(p):
    with urllib.request.urlopen(BASE+p,timeout=20) as r: return json.load(r)

def main():
    if len(sys.argv)>1:
        s=get(f"/symbols/{sys.argv[1].upper().lstrip('r').replace('R','R',1)}.json") \
          if sys.argv[1].upper().startswith("R") else get(f"/symbols/R{sys.argv[1].upper()}.json")
        print(json.dumps(s,indent=1)); return
    st=get("/state.json")
    f=st["finding"]
    print(f"session {st['session']}  dark={st['is_dark']}  reopen {st['next_reopen_et']}")
    print(f"finding: {f['noise_share_large_cap_pct']}% of void drift reverses "
          f"(beta {f['beta']}, t {f['t']}, n={f['observations']})")
    if not st["is_dark"]:
        print("US market is OPEN - noise scores suppressed, drift is real price discovery")
    print(f"\n{'sym':8s} {'last':>10s} {'fair':>10s} {'drift':>8s} {'score':>5s} {'buy $0.5%':>11s}")
    for r in st["symbols"][:10]:
        print(f"{r['symbol']:8s} {r['last']:10.2f} "
              f"{(r['fair_value'] or 0):10.2f} "
              f"{(r['dislocation_pct'] or 0):+7.2f}% {str(r['noise_score']):>5s} "
              f"{(r['buy_usd_0_5'] or 0):11,.0f}")

if __name__=="__main__": main()

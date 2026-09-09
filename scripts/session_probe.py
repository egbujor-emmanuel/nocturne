import json,datetime as dt,statistics as st,glob,os
ET=dt.timezone(dt.timedelta(hours=-4))
for p in sorted(glob.glob("data/1h/*.json"))[:2]:
    rows=json.load(open(p)); sym=os.path.basename(p)[:-5]
    b={}
    for r in rows:
        t=dt.datetime.fromtimestamp(int(r[0])/1000,ET)
        b[t]=(float(r[4]),float(r[5]),float(r[7] if len(r)>7 else r[6]))
    ts=sorted(b)
    print(f"=== {sym}: {len(ts)} bars, {ts[0]:%Y-%m-%d} -> {ts[-1]:%Y-%m-%d} ===")
    # liquidity by hour-of-week class
    wknd=[v[2] for t,v in b.items() if t.weekday()>=5]
    fri_eve=[v[2] for t,v in b.items() if t.weekday()==4 and t.hour>=20]
    rth=[v[2] for t,v in b.items() if t.weekday()<5 and 10<=t.hour<16]
    print(f"  median hourly $vol  regular-hours: ${st.median(rth):>12,.0f}")
    print(f"  median hourly $vol  weekend      : ${st.median(wknd):>12,.0f}")
    print(f"  ratio (RTH / weekend)            : {st.median(rth)/max(st.median(wknd),1e-9):,.0f}x")
    zero=sum(1 for v in wknd if v==0)
    print(f"  weekend hours with ZERO trades   : {zero}/{len(wknd)} = {zero/len(wknd)*100:.1f}%")
    # confirm session boundary: is there a Friday 16:00-20:00 ET gap in activity?
    for h in range(15,24):
        v=[x[2] for t,x in b.items() if t.weekday()==4 and t.hour==h]
        if v: print(f"    Fri {h:02d}:00 ET median $vol = {st.median(v):>12,.0f}")
    print()

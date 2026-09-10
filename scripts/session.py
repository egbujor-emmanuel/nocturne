"""C4: session-state classifier.

The whole product rests on knowing which regime we are in. Measured from the
tape (see docs/METHODOLOGY.md), the US-equity week on Bitget has six states:

  RTH        Mon-Fri 09:30-16:00 ET  routed to real market liquidity
  AH         Mon-Fri 16:00-20:00 ET  after-hours, still routed
  NIGHT      Mon-Thu 20:00-04:00 ET  US shut overnight
  PRE        Mon-Fri 04:00-09:30 ET  US pre-market
  VOID_A     Fri 20:00 -> Sun 19:00  NO external equity price exists anywhere
  PARTIAL_B  Sun 19:00 -> Mon 04:00  index futures live, single names still dark

ET is UTC-4 for the whole project window (US DST ends Nov 1 2026).
"""
import datetime as dt

ET=dt.timezone(dt.timedelta(hours=-4))

RTH,AH,NIGHT,PRE,VOID_A,PARTIAL_B="RTH","AH","NIGHT","PRE","VOID_A","PARTIAL_B"
DARK={VOID_A,PARTIAL_B,NIGHT}          # US market closed
WEEKEND_DARK={VOID_A,PARTIAL_B}        # the windows the model was fitted on
NO_ORACLE={VOID_A}                     # no external price anywhere

def now_et(): return dt.datetime.now(ET)

def classify(t=None):
    """t: tz-aware datetime (any tz) or None for now."""
    t=(t or now_et()).astimezone(ET)
    wd=t.weekday()                      # Mon=0 .. Sun=6
    mins=t.hour*60+t.minute
    OPEN,CLOSE,AH_END,PRE_START=9*60+30,16*60,20*60,4*60

    if wd==5: return VOID_A                              # all Saturday
    if wd==6: return VOID_A if mins<19*60 else PARTIAL_B  # Sun until 19:00
    if wd==4 and mins>=AH_END: return VOID_A              # Fri from 20:00
    if wd==0 and mins<PRE_START: return PARTIAL_B         # Mon until 04:00
    if mins<PRE_START: return NIGHT
    if mins<OPEN: return PRE
    if mins<CLOSE: return RTH
    if mins<AH_END: return AH
    return NIGHT

def void_window(t=None):
    """(start,end) of the void window containing or next following t."""
    t=(t or now_et()).astimezone(ET)
    fri=t.date()-dt.timedelta(days=(t.weekday()-4)%7)
    start=dt.datetime.combine(fri,dt.time(20,0),ET)
    if t<start and t.weekday()<4: pass
    end=dt.datetime.combine(fri+dt.timedelta(days=2),dt.time(19,0),ET)
    return start,end

def next_reopen(t=None):
    """Next Monday 09:30 ET re-anchor — when unfilled weekend orders are cancelled."""
    t=(t or now_et()).astimezone(ET)
    d=t.date()
    while True:
        cand=dt.datetime.combine(d,dt.time(9,30),ET)
        if cand>t and cand.weekday()<5: return cand
        d+=dt.timedelta(days=1)

if __name__=="__main__":
    print(f"now ET   : {now_et():%a %Y-%m-%d %H:%M}")
    print(f"session  : {classify()}")
    print(f"reopen   : {next_reopen():%a %Y-%m-%d %H:%M ET}")
    print("\nself-test across a full week:")
    base=dt.datetime(2026,9,11,0,0,tzinfo=ET)   # Friday
    exp={}
    for h in range(0,24*4,1):
        t=base+dt.timedelta(hours=h)
        exp.setdefault(classify(t),[]).append(t)
    for k in [RTH,AH,NIGHT,PRE,VOID_A,PARTIAL_B]:
        v=exp.get(k,[])
        if v: print(f"  {k:10s} {len(v):3d}h   first={v[0]:%a %H:%M}  last={v[-1]:%a %H:%M}")
    # boundary assertions
    assert classify(dt.datetime(2026,9,11,19,59,tzinfo=ET))==AH
    assert classify(dt.datetime(2026,9,11,20,0,tzinfo=ET))==VOID_A
    assert classify(dt.datetime(2026,9,12,12,0,tzinfo=ET))==VOID_A
    assert classify(dt.datetime(2026,9,13,18,59,tzinfo=ET))==VOID_A
    assert classify(dt.datetime(2026,9,13,19,0,tzinfo=ET))==PARTIAL_B
    assert classify(dt.datetime(2026,9,14,3,59,tzinfo=ET))==PARTIAL_B
    assert classify(dt.datetime(2026,9,14,4,0,tzinfo=ET))==PRE
    assert classify(dt.datetime(2026,9,14,9,30,tzinfo=ET))==RTH
    assert classify(dt.datetime(2026,9,14,16,0,tzinfo=ET))==AH
    assert classify(dt.datetime(2026,9,14,20,0,tzinfo=ET))==NIGHT
    print("\n  ALL BOUNDARY ASSERTIONS PASSED")

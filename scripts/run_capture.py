"""C3 (v2): local redundant capture runner.

Replaces run_capture.cmd. Batch under Task Scheduler was being terminated
(0xC000013A) on exactly the runs that did real work - `timeout` and console
redirection misbehave when no console is attached. Pure Python with explicit
subprocess timeouts is deterministic.
"""
import os,sys,subprocess,datetime as dt,random,time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG=os.path.join(ROOT,"logs","runner.log")
os.makedirs(os.path.join(ROOT,"logs"),exist_ok=True)

def log(m):
    line=f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} {m}"
    with open(LOG,"a",encoding="utf8") as f: f.write(line+"\n")
    print(line)

def run(args,timeout=90,check=False):
    env=dict(os.environ,GIT_TERMINAL_PROMPT="0",GCM_INTERACTIVE="never",
             NOCTURNE_SOURCE="local")
    try:
        p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
        return p.returncode,(p.stdout or "").strip(),(p.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1,"","TIMEOUT after %ss" % timeout

def main():
    rc,out,err=run([sys.executable,os.path.join("scripts","capture.py")],timeout=180)
    log(f"capture rc={rc} {out[:120]}{(' ERR '+err[:160]) if err else ''}")
    if rc!=0: return 1
    if "skip" in out: return 0

    for path in ("data/live","data/books","data/status.local.json","data/health.json",
                 "data/site.json"):
        if os.path.exists(os.path.join(ROOT,path)):
            run(["git","add","-A",path],timeout=60)
    rc,out,_=run(["git","diff","--cached","--quiet"],timeout=30)
    if rc==0:
        log("nothing staged"); return 0
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    run(["git","commit","-q","-m",f"capture local {stamp}"],timeout=60)
    for i in range(4):
        rc,_,_=run(["git","pull","--rebase","--autostash","-q","origin","master"],timeout=120)
        if rc==0:
            rc2,_,e2=run(["git","push","-q"],timeout=120)
            if rc2==0: log("pushed"); return 0
            log(f"push failed attempt {i+1}: {e2[:120]}")
        else:
            log(f"pull failed attempt {i+1}")
        time.sleep(random.uniform(2,6))
    log("PUSH FAILED after 4 attempts (commit is safe locally)")
    return 0

if __name__=="__main__": sys.exit(main())

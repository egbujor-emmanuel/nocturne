"""C3 (v2): local redundant capture runner.

Replaces run_capture.cmd. Batch under Task Scheduler was being terminated
(0xC000013A) on exactly the runs that did real work - `timeout` and console
redirection misbehave when no console is attached. Pure Python with explicit
subprocess timeouts is deterministic.
"""
import os,sys,subprocess,datetime as dt,random,time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC="local"
for i,a in enumerate(sys.argv):
    if a=="--source" and i+1<len(sys.argv): SRC=sys.argv[i+1]
LOG=os.path.join(ROOT,"logs","runner.%s.log"%SRC)
os.makedirs(os.path.join(ROOT,"logs"),exist_ok=True)

def log(m):
    line=f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} {m}"
    with open(LOG,"a",encoding="utf8") as f: f.write(line+"\n")
    print(line)

# Windows: stop git/python subprocesses flashing a console window every cycle
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

def run(args,timeout=90,check=False):
    env=dict(os.environ,GIT_TERMINAL_PROMPT="0",GCM_INTERACTIVE="never",
             NOCTURNE_SOURCE=SRC)
    try:
        p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,
                         timeout=timeout,creationflags=CREATE_NO_WINDOW)
        return p.returncode,(p.stdout or "").strip(),(p.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return -1,"","TIMEOUT after %ss" % timeout

GIT_LOCK=os.path.join(ROOT,"logs",".gitlock")
STALE=600  # seconds; a crashed holder must not block capture forever

def acquire_git_lock(wait=90):
    """Only one process may touch the git index at a time. Three writers doing
    `pull --rebase` concurrently left the repo mid-rebase with a detached HEAD
    and 90 conflicted files - this prevents that."""
    deadline=time.time()+wait
    while time.time()<deadline:
        try:
            if os.path.exists(GIT_LOCK) and time.time()-os.path.getmtime(GIT_LOCK)>STALE:
                os.remove(GIT_LOCK)
            fd=os.open(GIT_LOCK,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
            os.write(fd,str(os.getpid()).encode()); os.close(fd)
            return True
        except FileExistsError:
            time.sleep(2)
        except Exception:
            return True
    return False

def release_git_lock():
    try: os.remove(GIT_LOCK)
    except Exception: pass

def main():
    log("START pid=%s src=%s" % (os.getpid(),SRC))
    rc,out,err=run([sys.executable,os.path.join("scripts","capture.py")],timeout=180)
    log(f"capture rc={rc} {out[:120]}{(' ERR '+err[:160]) if err else ''}")
    if rc!=0: return 1
    if "skip" in out: return 0
    rc2,o2,e2=run([sys.executable,os.path.join("scripts","build_state.py")],timeout=120)
    log("state rc=%s %s" % (rc2,(o2 or e2)[:90]))
    rc3,o3,e3=run([sys.executable,os.path.join("scripts","orchestrate.py")],timeout=300)
    log("orch rc=%s %s" % (rc3,(o3 or e3).strip().splitlines()[-1][:110] if (o3 or e3).strip() else ""))

    if not acquire_git_lock():
        log("git lock busy - captured to disk, will push next cycle"); return 0
    try:
        return _git_publish()
    finally:
        release_git_lock()

def _git_publish():
    for path in ("data/live","data/books","data/status.local.json","data/health.json",
                 "data/site.json","api","predictions","posts"):
        if os.path.exists(os.path.join(ROOT,path)):
            run(["git","add","-A",path],timeout=60)
    rc,out,_=run(["git","diff","--cached","--quiet"],timeout=30)
    if rc==0:
        log("nothing staged"); return 0
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    run(["git","commit","-q","-m","capture %s %s"%(SRC,stamp)],timeout=60)
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

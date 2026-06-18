"""fix_names_caps.py [apply] — title-case ALL-CAPS dance names (preserve acronyms, fix typos),
regenerate clean slugs. Dry-run unless 'apply'."""
import os, re, subprocess, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
APPLY=len(sys.argv)>1 and sys.argv[1]=="apply"
ACR={"TLC","ATL","ALF","BK","MC","DJ","TV","II","III"}
SMALL={"the","a","an","of","to","and","in","on","with","for"}
FIX={"TYPERWRITER":"Typewriter","REEBOOK":"Reebok","CHARLSTON":"Charleston","MONESTARY":"Monastery"}
def psql(sql):
    env=dict(os.environ); env["PGPASSWORD"]="dancebabydance"
    p=subprocess.run(["psql","-h","192.168.0.197","-U","dance_user","-d","dancing","-v","ON_ERROR_STOP=1","-At","-F","\t"],
        input=sql,capture_output=True,text=True,encoding="utf-8",env=env)
    if p.returncode: sys.stderr.write(p.stderr); raise SystemExit(1)
    return [l.split("\t") for l in p.stdout.splitlines() if l]
def slugify(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    return re.sub(r"-{2,}","-",re.sub(r"[^a-z0-9]+","-",s)).strip("-")
def caseword(w,first):
    u=w.upper()
    if u in ACR: return u
    if u in FIX: return FIX[u]
    lw=w.lower()
    return lw if (not first and lw in SMALL) else lw[:1].upper()+lw[1:]
def smartcase(name):
    out=[]; first=True
    for p in re.split(r"(\W+)",name):
        if re.match(r"\w",p): out.append(caseword(p,first)); first=False
        else: out.append(p)
    return "".join(out)

rows=psql('''SELECT "Id","Name","Slug" FROM "Dances" WHERE "Name"=upper("Name") AND "Name" ~ '[A-Z]' ORDER BY "Id";''')
existing={r[0] for r in psql('SELECT "Slug" FROM "Dances";')}
T=["BEGIN;"]; n=0
for did,name,slug in rows:
    new=smartcase(name)
    if new==name: continue
    ns=slugify(new); base=ns; i=2
    while ns in existing and ns!=slug: ns=f"{base}-{i}"; i+=1
    existing.add(ns)
    esc=new.replace("'","''")
    T.append(f'UPDATE "Dances" SET "Name"=\'{esc}\',"Slug"=\'{ns}\' WHERE "Id"={did};')
    print(f"  #{did}: {name}  ->  {new}   [{ns}]"); n+=1
T.append("COMMIT;" if APPLY else "ROLLBACK;")
print(f"\n{n} names to fix | Mode: {'APPLY' if APPLY else 'DRY RUN'}")
psql("\n".join(T))

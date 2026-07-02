"""
Phase 8 citation verification. Each reference is matched against Crossref, the returned metadata
(title, authors, journal, year, volume, pages, DOI) is used to rebuild an AMA 11th-edition citation,
and a Zotero-importable BibTeX file is emitted. Crossref artifacts (ALL-CAPS, <scp> tags) are cleaned.
"""
import urllib.request, urllib.parse, json, re, os, html
OUT=r"C:\Users\Owner\ortho-mimic-study\manuscript"
UA={"User-Agent":"ortho-mimic-study/1.0 (mailto:local@local)"}

# (key, query, expected first-author surname, expected year) — queries are bibliographic strings
REFS=[
 (1,"Osteomyelitis Lew Waldvogel Lancet 2004","Lew","2004"),
 (2,"Prosthetic joint infection Tande Patel Clinical Microbiology Reviews 2014","Tande","2014"),
 (3,"Culture-negative prosthetic joint infection Berbari Clinical Infectious Diseases 2007","Berbari","2007"),
 (4,"2018 definition periprosthetic hip knee infection evidence-based validated criteria Parvizi Journal of Arthroplasty 2018","Parvizi","2018"),
 (5,"MIMIC-IV freely accessible electronic health record dataset Johnson Scientific Data 2023","Johnson","2023"),
 (6,"Diagnosis management prosthetic joint infection clinical practice guidelines Infectious Diseases Society America Osmon 2013","Osmon","2013"),
 (7,"Sonication removed hip knee prostheses diagnosis infection Trampuz New England Journal Medicine 2007","Trampuz","2007"),
]

def clean(s):
    if not s: return s
    s=re.sub(r"</?[^>]+>","",s)          # strip tags incl <scp>
    s=html.unescape(s)
    if s.isupper(): s=s.title()
    return s.strip()

def crossref(query):
    url="https://api.crossref.org/works?"+urllib.parse.urlencode({"query.bibliographic":query,"rows":3})
    d=json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=30))
    return d["message"]["items"]

def ama(it):
    auth=it.get("author",[])
    names=[]
    for a in auth:
        fam=clean(a.get("family","")); given=a.get("given","")
        ini="".join(p[0] for p in re.split(r"[ \-]",given) if p) if given else ""
        names.append(f"{fam} {ini}".strip())
    if len(names)>6: astr=", ".join(names[:3])+", et al"
    else: astr=", ".join(names)
    title=clean(it.get("title",[""])[0] if it.get("title") else "")
    jour=clean((it.get("short-container-title") or it.get("container-title") or [""])[0])
    yr=(it.get("issued",{}).get("date-parts",[[None]])[0][0])
    vol=it.get("volume",""); iss=it.get("issue",""); pg=it.get("page","")
    doi=it.get("DOI","")
    cite=f"{astr}. {title}. {jour}. {yr}"
    if vol: cite+=f";{vol}"
    if iss: cite+=f"({iss})"
    if pg: cite+=f":{pg}"
    cite+=f". doi:{doi}"
    return cite, doi, title, yr, jour

def bibtex(key,it):
    auth=it.get("author",[]); a=" and ".join(f"{x.get('family','')}, {x.get('given','')}" for x in auth)
    t=clean(it.get("title",[""])[0] if it.get("title") else "")
    j=clean((it.get("container-title") or [""])[0])
    y=it.get("issued",{}).get("date-parts",[[None]])[0][0]
    return (f"@article{{ref{key},\n  author = {{{a}}},\n  title = {{{t}}},\n  journal = {{{j}}},\n"
            f"  year = {{{y}}},\n  volume = {{{it.get('volume','')}}},\n  number = {{{it.get('issue','')}}},\n"
            f"  pages = {{{it.get('page','')}}},\n  doi = {{{it.get('DOI','')}}}\n}}\n")

lines=[]; bibs=[]; report=[]
for key,q,exp_auth,exp_yr in REFS:
    items=crossref(q)
    pick=None
    for it in items:
        fam=(it.get("author",[{}])[0].get("family","") if it.get("author") else "")
        yr=str(it.get("issued",{}).get("date-parts",[[None]])[0][0])
        if exp_auth.lower() in fam.lower() and yr==exp_yr:
            pick=it; break
    if pick is None: pick=items[0]
    cite,doi,title,yr,jour=ama(pick)
    lines.append(f"{key}. {cite}")
    bibs.append(bibtex(key,pick))
    ok = (exp_auth.lower() in (pick.get("author",[{}])[0].get("family","").lower() if pick.get("author") else "")) and (str(yr)==exp_yr)
    report.append((key,exp_auth,exp_yr,yr,doi,"OK" if ok else "CHECK",title[:60]))

open(os.path.join(OUT,"references_ama.md"),"w",encoding="utf-8").write("\n".join(lines))
open(os.path.join(OUT,"references.bib"),"w",encoding="utf-8").write("\n".join(bibs))
print("VERIFICATION REPORT")
for r in report:
    print(f"  [{r[5]}] ref{r[0]} {r[1]} {r[2]} -> crossref yr {r[3]} | doi {r[4]}")
print("\nAMA references + Zotero .bib written to manuscript/")
print("\n".join(lines))

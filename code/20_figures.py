"""
Phase 6 figures. Reads digests, produces journal-grade PDF+PNG at 600 DPI.
  Figure 1 — organism spectrum overall + PJI vs osteomyelitis
  Figure 2 — culture-negative benchmark: by source category + by infection type (with 95% CIs)
  Figure 3 — antimicrobial resistance panel (%R with 95% CIs) + MRSA
  Figure 4 — diagnostic yield by source category + ML anticipatability probe (ROC-free bar)
"""
import os, json, sys, numpy as np
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from figure_kit import set_style, save, panel, faint_grid, BLUE, GREY, SALMON, OKABE, LABEL, MUTED

PROJ=r"C:\Users\Owner\ortho-mimic-study"; OUT=os.path.join(PROJ,"output")
FIG=os.path.join(OUT,"figures"); os.makedirs(FIG,exist_ok=True)
R=json.load(open(os.path.join(OUT,"results_digest.json")))
S=json.load(open(os.path.join(OUT,"stats_digest.json")))
M=json.load(open(os.path.join(OUT,"ml_digest.json")))
set_style()

CAT_LABEL={"deep_tissue_bone":"Deep tissue / bone","synovial_joint":"Synovial / joint fluid",
           "implant_sonication":"Implant sonication /\nforeign body","abscess_deep_fluid":"Abscess / deep fluid",
           "superficial_swab":"Superficial swab","blood":"Blood","other":"Other"}
IT_LABEL={"PJI":"Prosthetic joint\ninfection","Osteomyelitis":"Native\nosteomyelitis","Device (other)":"Other device\ninfection"}

# ---------------- Figure 1: organism spectrum ----------------
def fig1():
    over=R["aim1_organism"]["by_genus_group"]
    # keep top 9 by pct, collapse rest
    items=sorted(over.items(), key=lambda kv: kv[1]["pct"], reverse=True)
    top=items[:9]
    names=[k for k,_ in top]; pcts=[v["pct"] for _,v in top]
    pji=R["aim1_organism"]["by_infection_type"]["PJI"]["by_genus_group"]
    ost=R["aim1_organism"]["by_infection_type"]["Osteomyelitis"]["by_genus_group"]
    fig,axes=plt.subplots(1,2,figsize=(11,5.2))
    ax=axes[0]
    ypos=np.arange(len(names))[::-1]
    ax.barh(ypos,pcts,color=BLUE,zorder=3,height=0.7)
    ax.set_yticks(ypos); ax.set_yticklabels(names)
    ax.set_xlabel("Isolates (% of deep-specimen isolates)")
    for yv,pv in zip(ypos,pcts): ax.text(pv+0.4,yv,f"{pv:.1f}",va="center",fontsize=8,color=LABEL)
    faint_grid(ax,"x"); ax.set_xlim(0,max(pcts)*1.15); panel(ax,"a")
    # grouped PJI vs osteo for top 6
    ax=axes[1]
    top6=[n for n in names][:6]
    pv=[pji.get(n,{}).get("pct",0) for n in top6]; ov=[ost.get(n,{}).get("pct",0) for n in top6]
    x=np.arange(len(top6)); w=0.38
    ax.bar(x-w/2,pv,w,label="Prosthetic joint infection",color=BLUE,zorder=3)
    ax.bar(x+w/2,ov,w,label="Native osteomyelitis",color=SALMON,zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([n.replace(" ","\n",1) for n in top6],fontsize=7.5)
    ax.set_ylabel("Isolates (%)"); ax.legend(frameon=False,loc="upper right")
    faint_grid(ax,"y"); panel(ax,"b")
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure1_organism_spectrum"))

# ---------------- Figure 2: culture-negative benchmark ----------------
def fig2():
    a2=R["aim2_culture_negative"]
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    # by source category
    ax=axes[0]
    cats=["deep_tissue_bone","synovial_joint","implant_sonication"]
    fr=[a2["by_source_category"][c]["frac"]*100 for c in cats]
    lo=[a2["by_source_category"][c]["ci"][0]*100 for c in cats]
    hi=[a2["by_source_category"][c]["ci"][1]*100 for c in cats]
    x=np.arange(len(cats))
    err=[[f-l for f,l in zip(fr,lo)],[h-f for f,h in zip(fr,hi)]]
    ax.bar(x,fr,color=BLUE,zorder=3,width=0.6,yerr=err,capsize=4,error_kw=dict(lw=1,ecolor=LABEL))
    ax.set_xticks(x); ax.set_xticklabels([CAT_LABEL[c] for c in cats],fontsize=8.5)
    ax.set_ylabel("Culture-negative specimens (%)")
    for xv,fv,hv in zip(x,fr,hi): ax.text(xv,hv+2.0,f"{fv:.1f}%",ha="center",fontsize=8.5,color=LABEL)
    faint_grid(ax,"y"); ax.set_ylim(0,70); panel(ax,"a")
    # by infection type (specimen-level)
    ax=axes[1]
    its=["PJI","Osteomyelitis","Device (other)"]
    fr=[a2["by_infection_type"][i]["frac"]*100 for i in its]
    lo=[a2["by_infection_type"][i]["ci"][0]*100 for i in its]
    hi=[a2["by_infection_type"][i]["ci"][1]*100 for i in its]
    x=np.arange(len(its)); err=[[f-l for f,l in zip(fr,lo)],[h-f for f,h in zip(fr,hi)]]
    ax.bar(x,fr,color=[BLUE,SALMON,GREY],zorder=3,width=0.6,yerr=err,capsize=4,error_kw=dict(lw=1,ecolor=LABEL))
    ax.set_xticks(x); ax.set_xticklabels([IT_LABEL[i] for i in its],fontsize=8.5)
    ax.set_ylabel("Culture-negative specimens (%)")
    for xv,fv,hv in zip(x,fr,hi): ax.text(xv,hv+2.0,f"{fv:.1f}%",ha="center",fontsize=8.5,color=LABEL)
    faint_grid(ax,"y"); ax.set_ylim(0,70); panel(ax,"b")
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure2_culture_negative"))

# ---------------- Figure 3: resistance panel ----------------
def fig3():
    ar=R["aim3_resistance"]["agent_percentR"]
    order=["VANCOMYCIN","RIFAMPIN","GENTAMICIN","TRIMETHOPRIM/SULFA","TETRACYCLINE","CEFTRIAXONE",
           "CIPROFLOXACIN","LEVOFLOXACIN","CLINDAMYCIN","CEFAZOLIN","OXACILLIN","ERYTHROMYCIN"]
    order=[a for a in order if a in ar]
    fr=[ar[a]["pctR"] for a in order]; lo=[ar[a]["ci"][0] for a in order]; hi=[ar[a]["ci"][1] for a in order]
    fig,ax=plt.subplots(figsize=(8.2,5.2))
    y=np.arange(len(order))[::-1]
    err=[[f-l for f,l in zip(fr,lo)],[h-f for f,h in zip(fr,hi)]]
    ax.barh(y,fr,color=SALMON,zorder=3,height=0.66,xerr=err,capsize=3,error_kw=dict(lw=0.9,ecolor=LABEL))
    ax.set_yticks(y); ax.set_yticklabels([a.title().replace("Trimethoprim/Sulfa","TMP-SMX") for a in order])
    ax.set_xlabel("Isolates resistant (%)")
    for yv,fv,a in zip(y,fr,order): ax.text(fv+1,yv,f"{fv:.0f}%",va="center",fontsize=8,color=LABEL)
    mr=R["aim3_resistance"]["mrsa_among_saureus"]
    ax.text(0.98,0.02,f"MRSA among S. aureus: {mr['frac']*100:.0f}% (95% CI {mr['ci'][0]*100:.0f}–{mr['ci'][1]*100:.0f}; n={mr['tested']})",
            transform=ax.transAxes,ha="right",va="bottom",fontsize=8,color=MUTED)
    faint_grid(ax,"x"); ax.set_xlim(0,max(fr)*1.18)
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure3_resistance"))

# ---------------- Figure 4: yield by source + ML probe ----------------
def fig4():
    yld=R["aim4_intensity"]["yield_by_source_category"]
    cats=["deep_tissue_bone","synovial_joint","implant_sonication","abscess_deep_fluid","superficial_swab","blood"]
    cats=[c for c in cats if c in yld]
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    ax=axes[0]
    fr=[yld[c]["frac"]*100 for c in cats]; lo=[yld[c]["ci"][0]*100 for c in cats]; hi=[yld[c]["ci"][1]*100 for c in cats]
    y=np.arange(len(cats))[::-1]; err=[[f-l for f,l in zip(fr,lo)],[h-f for f,h in zip(fr,hi)]]
    ax.barh(y,fr,color=BLUE,zorder=3,height=0.66,xerr=err,capsize=3,error_kw=dict(lw=0.9,ecolor=LABEL))
    ax.set_yticks(y); ax.set_yticklabels([CAT_LABEL[c].replace("\n"," ") for c in cats],fontsize=8.5)
    ax.set_xlabel("Culture-positive (%)"); faint_grid(ax,"x"); ax.set_xlim(0,100); panel(ax,"a")
    for yv,fv in zip(y,fr): ax.text(fv+1.5,yv,f"{fv:.0f}%",va="center",fontsize=8,color=LABEL)
    # ML probe: AUROC bars with CI
    ax=axes[1]
    labels=["Clinical context","+ Inflammatory labs"]
    au=[M["M1_context"]["auroc"],M["M2_with_labs"]["auroc"]]
    ci=[M["M1_context"]["auroc_ci"],M["M2_with_labs"]["auroc_ci"]]
    x=np.arange(2); err=[[a-c[0] for a,c in zip(au,ci)],[c[1]-a for a,c in zip(au,ci)]]
    ax.bar(x,au,color=[GREY,BLUE],width=0.55,zorder=3,yerr=err,capsize=5,error_kw=dict(lw=1,ecolor=LABEL))
    ax.axhline(0.5,ls="--",lw=0.9,color=MUTED,zorder=2)
    ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=9); ax.set_ylabel("Out-of-fold AUROC")
    ax.set_ylim(0.45,0.75)
    for xv,av,c in zip(x,au,ci): ax.text(xv,c[1]+0.008,f"{av:.3f}",ha="center",fontsize=9,color=LABEL)
    ax.text(0.5,0.02,f"Δ={M['paired_auroc_gain']['delta']:+.3f} (95% CI {M['paired_auroc_gain']['ci'][0]:+.3f} to {M['paired_auroc_gain']['ci'][1]:+.3f})",
            transform=ax.transAxes,ha="center",va="bottom",fontsize=8,color=MUTED)
    panel(ax,"b")
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure4_yield_and_probe"))

fig1(); fig2(); fig3(); fig4()
print("Figures written to output/figures/:")
for f in sorted(os.listdir(FIG)):
    if f.endswith(".pdf"): print("  ",f)

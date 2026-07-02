"""
Phase 6 figures, NEJM style (ggsci NEJM palette, Helvetica, 600 DPI PDF+PNG, uppercase panels).
  Figure 1 - organism spectrum (overall; PJI vs osteomyelitis)
  Figure 2 - no-growth benchmark: by source, by infection type, by sampling intensity
  Figure 3 - antimicrobial resistance (S. aureus panel; gram-negative panel)
  Figure 4 - diagnostic yield by source; anticipatability probe
"""
import os, json, sys, numpy as np
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from nejm_kit import (set_style, panel, faint_grid, save,
    NEJM_BLUE, NEJM_RED, NEJM_ORANGE, NEJM_GREEN, NEJM_LTBLUE, GREY, LABEL, MUTED)

PROJ=r"C:\Users\Owner\ortho-mimic-study"; OUT=os.path.join(PROJ,"output")
FIG=os.path.join(OUT,"figures"); os.makedirs(FIG,exist_ok=True)
R=json.load(open(os.path.join(OUT,"results_digest.json")))
S=json.load(open(os.path.join(OUT,"stats_digest.json")))
M=json.load(open(os.path.join(OUT,"ml_digest.json")))
set_style()

CAT={"deep_tissue_bone":"Deep tissue or bone","synovial_joint":"Synovial or joint fluid",
     "implant_sonication":"Implant sonication","abscess_deep_fluid":"Abscess or deep fluid",
     "superficial_swab":"Superficial swab","blood":"Blood"}
IT={"PJI":"Prosthetic joint\ninfection","Osteomyelitis":"Native\nosteomyelitis","Device (other)":"Other device\ninfection"}

def err_from(fr,lo,hi): return [[f-l for f,l in zip(fr,lo)],[h-f for f,h in zip(fr,hi)]]

# ---------------- Figure 1 ----------------
def fig1():
    over=R["aim1_organism"]["by_genus_group"]
    items=[(k,v) for k,v in sorted(over.items(),key=lambda kv:kv[1]["pct"],reverse=True) if v["pct"]>=0.5][:9]
    names=[k for k,_ in items]; pcts=[v["pct"] for _,v in items]
    pji=R["aim1_organism"]["by_infection_type"]["PJI"]["by_genus_group"]
    ost=R["aim1_organism"]["by_infection_type"]["Osteomyelitis"]["by_genus_group"]
    fig,axes=plt.subplots(1,2,figsize=(11,4.9))
    ax=axes[0]; y=np.arange(len(names))[::-1]
    ax.barh(y,pcts,color=NEJM_BLUE,zorder=3,height=0.68)
    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_xlabel("Percentage of isolates")
    for yv,pv in zip(y,pcts): ax.text(pv+0.5,yv,f"{pv:.1f}",va="center",fontsize=8,color=LABEL)
    faint_grid(ax,"x"); ax.set_xlim(0,max(pcts)*1.16); panel(ax,"A")
    ax=axes[1]; top6=names[:6]
    SHORT={"Staphylococcus aureus":"S. aureus","Coagulase-negative staphylococci":"CoNS",
           "Other gram-negative":"Other\nGNB","Streptococcus":"Strepto-\ncoccus",
           "Enterococcus":"Entero-\ncoccus","Other gram-positive":"Other\nGPC",
           "Pseudomonas aeruginosa":"P. aeru-\nginosa","Anaerobe":"Anaerobe","Escherichia coli":"E. coli"}
    pv=[pji.get(n,{}).get("pct",0) for n in top6]; ov=[ost.get(n,{}).get("pct",0) for n in top6]
    x=np.arange(len(top6)); w=0.38
    ax.bar(x-w/2,pv,w,label="Prosthetic joint infection",color=NEJM_BLUE,zorder=3)
    ax.bar(x+w/2,ov,w,label="Native osteomyelitis",color=NEJM_RED,zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([SHORT.get(n,n) for n in top6],fontsize=8)
    ax.set_ylabel("Percentage of isolates")
    ax.legend(frameon=False,loc="upper center",bbox_to_anchor=(0.5,1.16),ncol=2,fontsize=8.5)
    faint_grid(ax,"y"); panel(ax,"B")
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure1_organism_spectrum"))

# ---------------- Figure 2 (3 panels: source, type, sampling gradient) ----------------
def fig2():
    a2=R["aim2_culture_negative"]
    fig,axes=plt.subplots(1,3,figsize=(13,4.5))
    # A: by source
    ax=axes[0]; cats=["deep_tissue_bone","synovial_joint","implant_sonication"]
    fr=[a2["by_source_category"][c]["frac"]*100 for c in cats]
    lo=[a2["by_source_category"][c]["ci"][0]*100 for c in cats]; hi=[a2["by_source_category"][c]["ci"][1]*100 for c in cats]
    x=np.arange(len(cats))
    ax.bar(x,fr,color=NEJM_BLUE,zorder=3,width=0.62,yerr=err_from(fr,lo,hi),capsize=4,error_kw=dict(lw=1,ecolor=LABEL))
    ax.set_xticks(x); ax.set_xticklabels([CAT[c].replace(" ","\n") for c in cats],fontsize=8)
    ax.set_ylabel("No-growth specimens (%)")
    for xv,fv,hv in zip(x,fr,hi): ax.text(xv,hv+1.8,f"{fv:.1f}",ha="center",fontsize=8.5,color=LABEL)
    faint_grid(ax,"y"); ax.set_ylim(0,70); panel(ax,"A")
    # B: by infection type
    ax=axes[1]; its=["PJI","Osteomyelitis","Device (other)"]
    fr=[a2["by_infection_type"][i]["frac"]*100 for i in its]
    lo=[a2["by_infection_type"][i]["ci"][0]*100 for i in its]; hi=[a2["by_infection_type"][i]["ci"][1]*100 for i in its]
    x=np.arange(len(its))
    ax.bar(x,fr,color=[NEJM_BLUE,NEJM_RED,GREY],zorder=3,width=0.62,yerr=err_from(fr,lo,hi),capsize=4,error_kw=dict(lw=1,ecolor=LABEL))
    ax.set_xticks(x); ax.set_xticklabels([IT[i] for i in its],fontsize=8)
    ax.set_ylabel("No-growth specimens (%)")
    for xv,fv,hv in zip(x,fr,hi): ax.text(xv,hv+1.8,f"{fv:.1f}",ha="center",fontsize=8.5,color=LABEL)
    faint_grid(ax,"y"); ax.set_ylim(0,70); panel(ax,"B")
    # C: by sampling intensity (the ascertainment gradient)
    ax=axes[2]; cc=a2["cn_by_specimen_count"]; bands=["1","2-3","4-6","7+"]
    fr=[cc[b]["frac"]*100 for b in bands]; lo=[cc[b]["ci"][0]*100 for b in bands]; hi=[cc[b]["ci"][1]*100 for b in bands]
    x=np.arange(len(bands))
    ax.errorbar(x,fr,yerr=err_from(fr,lo,hi),fmt="o-",color=NEJM_ORANGE,ecolor=LABEL,
                elinewidth=1,capsize=3,ms=7,mfc=NEJM_ORANGE,mec="white",mew=1,zorder=3,lw=1.6)
    ax.set_xticks(x); ax.set_xticklabels(bands)
    ax.set_xlabel("Deep specimens per episode"); ax.set_ylabel("No-growth specimens (%)")
    for xv,fv,hv in zip(x,fr,hi): ax.text(xv,hv+1.6,f"{fv:.1f}",ha="center",fontsize=8.5,color=LABEL)
    faint_grid(ax,"y"); ax.set_ylim(0,70); panel(ax,"C")
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure2_culture_negative"))

# ---------------- Figure 3 ----------------
def _hpanel(ax, panel_data, order, color, letter):
    order=[a for a in order if a in panel_data]
    fr=[panel_data[a]["pctR"] for a in order]; lo=[panel_data[a]["ci"][0] for a in order]; hi=[panel_data[a]["ci"][1] for a in order]
    y=np.arange(len(order))[::-1]
    ax.barh(y,fr,color=color,zorder=3,height=0.66,xerr=err_from(fr,lo,hi),capsize=3,error_kw=dict(lw=0.9,ecolor=LABEL))
    nice={"TRIMETHOPRIM/SULFA":"TMP-SMX","PIPERACILLIN/TAZO":"Piperacillin-tazobactam"}
    ax.set_yticks(y); ax.set_yticklabels([nice.get(a,a.title()) for a in order],fontsize=8.5)
    ax.set_xlabel("Isolates resistant (%)")
    for yv,fv,hv in zip(y,fr,hi): ax.text(hv+1.4,yv,f"{fv:.0f}",va="center",fontsize=7.5,color=LABEL)
    faint_grid(ax,"x"); ax.set_xlim(0,max(hi+[10])*1.22); panel(ax,letter)

def fig3():
    sa=R["aim3_resistance"]["saureus_panel"]; gn=R["aim3_resistance"]["gramneg_panel"]
    fig,axes=plt.subplots(1,2,figsize=(11,5.0))
    _hpanel(axes[0], sa, ["OXACILLIN","ERYTHROMYCIN","LEVOFLOXACIN","CLINDAMYCIN","TETRACYCLINE",
                          "TRIMETHOPRIM/SULFA","RIFAMPIN","GENTAMICIN","VANCOMYCIN"], NEJM_RED, "A")
    _hpanel(axes[1], gn, ["CIPROFLOXACIN","TRIMETHOPRIM/SULFA","CEFTRIAXONE","CEFEPIME","GENTAMICIN",
                          "PIPERACILLIN/TAZO","TOBRAMYCIN","MEROPENEM"], NEJM_BLUE, "B")
    mr=R["aim3_resistance"]["mrsa_among_saureus"]
    axes[0].text(0.98,0.02,f"MRSA {mr['frac']*100:.0f}% (95% CI {mr['ci'][0]*100:.0f}-{mr['ci'][1]*100:.0f}; n={mr['tested']})",
            transform=axes[0].transAxes,ha="right",va="bottom",fontsize=8,color=MUTED)
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure3_resistance"))

# ---------------- Figure 4 ----------------
def fig4():
    yld=R["aim4_intensity"]["yield_by_source_category"]
    cats=[c for c in ["deep_tissue_bone","synovial_joint","implant_sonication","abscess_deep_fluid","blood"] if c in yld]
    fig,axes=plt.subplots(1,2,figsize=(11,4.6))
    ax=axes[0]
    fr=[yld[c]["frac"]*100 for c in cats]; lo=[yld[c]["ci"][0]*100 for c in cats]; hi=[yld[c]["ci"][1]*100 for c in cats]
    y=np.arange(len(cats))[::-1]
    ax.barh(y,fr,color=NEJM_BLUE,zorder=3,height=0.64,xerr=err_from(fr,lo,hi),capsize=3,error_kw=dict(lw=0.9,ecolor=LABEL))
    ax.set_yticks(y); ax.set_yticklabels([CAT[c] for c in cats],fontsize=8.5)
    ax.set_xlabel("Culture-positive (%)"); faint_grid(ax,"x"); ax.set_xlim(0,100); panel(ax,"A")
    for yv,fv,hv in zip(y,fr,hi): ax.text(hv+1.8,yv,f"{fv:.0f}",va="center",fontsize=8,color=LABEL)
    ax=axes[1]
    labels=["Clinical\ncontext","+ Inflammatory\nlabs"]
    au=[M["M1_context"]["auroc"],M["M2_with_labs"]["auroc"]]; ci=[M["M1_context"]["auroc_ci"],M["M2_with_labs"]["auroc_ci"]]
    x=np.arange(2)
    # dot-with-CI (not bars): bar length on a truncated AUROC axis exaggerates a near-null difference
    ax.errorbar(x,au,yerr=err_from(au,[c[0] for c in ci],[c[1] for c in ci]),fmt="o",ms=8,
                mfc=NEJM_BLUE,mec="white",mew=1.2,color=LABEL,ecolor=LABEL,elinewidth=1.2,capsize=5,zorder=3)
    ax.plot(x,au,color=NEJM_LTBLUE,lw=1,zorder=2)
    ax.axhline(0.5,ls="--",lw=0.9,color="#9CA3AF",zorder=1)
    ax.text(1.98,0.505,"chance",ha="right",va="bottom",fontsize=7.5,color=MUTED)
    ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=8.5); ax.set_ylabel("Out-of-fold AUROC")
    ax.set_ylim(0.45,0.75); ax.set_xlim(-0.5,1.6)
    for xv,av,c in zip(x,au,ci): ax.text(xv+0.06,av,f"{av:.3f}",ha="left",va="center",fontsize=9,color=LABEL)
    ax.text(0.5,0.02,f"Δ = {M['paired_auroc_gain']['delta']:+.3f} (95% CI {M['paired_auroc_gain']['ci'][0]:+.3f} to {M['paired_auroc_gain']['ci'][1]:+.3f})",
            transform=ax.transAxes,ha="center",va="bottom",fontsize=8,color=MUTED)
    panel(ax,"B")
    fig.tight_layout(); save(fig,os.path.join(FIG,"Figure4_yield_and_probe"))

fig1(); fig2(); fig3(); fig4()
print("NEJM-style figures written:")
for f in sorted(os.listdir(FIG)):
    if f.endswith(".pdf"): print("  ",f)

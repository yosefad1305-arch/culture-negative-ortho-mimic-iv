"""
Organism normalization + grouping for MIMIC-IV microbiologyevents (version-controlled; shipped as eTable).
classify(org_name) -> dict with:
  species        : canonical reporting label (e.g. 'Staphylococcus aureus')
  genus_group    : coarse reporting genus/group ('Staphylococcus aureus','Coagulase-negative staphylococci',...)
  broad_group    : 'Gram-positive' | 'Gram-negative' | 'Anaerobe' | 'Fungal' | 'Mycobacterial' | 'Other' | 'Non-organism'
  is_organism    : True if the row represents real microbial growth (incl. low-resolution morphotypes)
  is_species_level : True if identified to genus/species (not a low-resolution morphotype or administrative)
  is_low_resolution: True for morphotype-only / mixed-flora positives
  is_non_organism: True for administrative / viral-antigen / bare POSITIVE-NEGATIVE strings
  is_staph_aureus: True for S. aureus (incl. MRSA-flagged string)
The order of rules matters: first match wins within each block.
"""
import re

def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip().upper())

# administrative / non-organism (not real bacterial/fungal growth)
_NONORG_EXACT = {"CANCELLED", "POSITIVE", "NEGATIVE", "VIRUS", "MOLD"}
_VIRAL = ("HERPES", "CYTOMEGALOVIRUS", "VARICELLA", "ADENOVIRUS", "INFLUENZA",
          "PARAINFLUENZA", "HSV", "CMV", "ROTAVIRUS")

# low-resolution morphotype / mixed (real growth but not species-level)
_LOWRES = ("MIXED BACTERIAL FLORA", "GRAM NEGATIVE ROD", "GRAM POSITIVE COCCUS",
           "GRAM POSITIVE COCCI", "GRAM POSITIVE ROD", "GRAM POSITIVE BACTERIA",
           "GRAM NEGATIVE ROD(S)", "ENTEROBACTERIACEAE", "GRAM POSITIVE RODS")

_FUNGAL = ("YEAST", "CANDIDA", "ASPERGILLUS", "TRICHOPHYTON", "TRICHOSPORON", "FUSARIUM",
           "PENICILLIUM", "CRYPTOCOCCUS", "COCCIDIOIDES", "PAECILOMYCES", "CLADOSPORIUM",
           "SYNCEPHALASTRUM", "EMMONSIA", "SPOROBOLOMYCES", "BEAUVERIA", "PAPILIOTREMA",
           "ALTERNARIA", "MOLD", "ASPERGILLUS FUMIGATUS")

_MYCO = ("MYCOBACTERIUM", "ACIDFAST", "ACID FAST", "AFB", "M. TUBERCULOSIS", "MTD")

# anaerobes (override gram assignment)
_ANAEROBE = ("BACTEROIDES", "PREVOTELLA", "PEPTOSTREPTOCOCCUS", "CLOSTRIDIUM", "FUSOBACTERIUM",
             "VEILLONELLA", "FINEGOLDIA", "EGGERTHELLA", "PORPHYROMONAS", "ANAEROBIC GRAM",
             "PROPIONIBACTERIUM", "CUTIBACTERIUM")

# CoNS species (all non-aureus staph collapse here)
_CONS = ("EPIDERMIDIS", "LUGDUNENSIS", "CAPITIS", "WARNERI", "HOMINIS", "HAEMOLYTICUS",
         "SIMULANS", "CAPRAE", "SCIURI", "COHNII", "LENTUS", "PSEUDINTERMEDIUS",
         "SAPROPHYTICUS", "COAGULASE NEGATIVE", "COAGULASE-NEGATIVE")

# Gram-negative genera (Enterobacterales + non-fermenters)
_GNB = ("ESCHERICHIA", "KLEBSIELLA", "PROTEUS", "ENTEROBACTER", "SERRATIA", "CITROBACTER",
        "MORGANELLA", "PROVIDENCIA", "HAFNIA", "PANTOEA", "RAOULTELLA", "SALMONELLA",
        "PSEUDOMONAS", "ACINETOBACTER", "STENOTROPHOMONAS", "ACHROMOBACTER", "ALCALIGENES",
        "SPHINGOMONAS", "BURKHOLDERIA", "CHRYSEOBACTERIUM", "ELIZABETHKINGIA", "OCHROBATRUM",
        "OCHROBACTRUM", "COMAMONAS", "BREVUNDIMONAS", "MORAXELLA", "SHEWANELLA", "AEROMONAS",
        "EIKENELLA", "HAEMOPHILUS", "NEISSERIA", "CAPNOCYTOPHAGA", "AGGREGATIBACTER",
        "CAMPYLOBACTER", "GARDNERELLA", "NON-FERMENTER", "GRAM NEGATIVE ROD")

def classify(org_name):
    o = _norm(org_name)
    r = dict(species=None, genus_group=None, broad_group="Other", is_organism=True,
             is_species_level=True, is_low_resolution=False, is_non_organism=False,
             is_staph_aureus=False)

    # --- non-organism / administrative ---
    if o in _NONORG_EXACT or any(v in o for v in _VIRAL) or o.startswith("POSITIVE FOR") and any(v in o for v in _VIRAL):
        # viral antigen results & bare positive/negative — not bacterial/fungal growth
        if o.startswith("POSITIVE FOR") and ("STAPH" in o or "METHICILLIN" in o):
            pass  # handled below (MRSA string)
        elif o.startswith("POSITIVE FOR") and ("TUBERCULOSIS" in o or "M. TUBERCULOSIS" in o):
            pass  # mycobacteria below
        else:
            r.update(is_organism=False, is_species_level=False, is_non_organism=True,
                     broad_group="Non-organism", species="(non-organism result)", genus_group="(non-organism)")
            return r

    # --- Staphylococcus aureus (incl. MRSA-flag string) ---
    if ("STAPH AUREUS" in o) or ("STAPHYLOCOCCUS AUREUS" in o) or ("METHICILLIN RESISTANT STAPH AUREUS" in o):
        r.update(species="Staphylococcus aureus", genus_group="Staphylococcus aureus",
                 broad_group="Gram-positive", is_staph_aureus=True)
        return r

    # --- Mycobacteria ---
    if any(k in o for k in _MYCO):
        r.update(species="Mycobacterium spp.", genus_group="Mycobacteria", broad_group="Mycobacterial")
        return r

    # --- Fungal ---
    if any(k in o for k in _FUNGAL):
        sp = "Candida spp." if "CANDIDA" in o else ("Aspergillus spp." if "ASPERGILLUS" in o else
              ("Yeast" if "YEAST" in o else "Other fungus"))
        r.update(species=sp, genus_group="Fungi/yeast", broad_group="Fungal")
        return r

    # --- Low-resolution morphotypes / mixed flora (real growth, not species) ---
    if any(k in o for k in _LOWRES):
        grp = "Gram-negative" if "NEGATIVE" in o else ("Gram-positive" if "POSITIVE" in o else "Mixed/unspecified")
        r.update(species="(morphotype/mixed, not speciated)", genus_group="Low-resolution/mixed",
                 broad_group=grp if grp != "Mixed/unspecified" else "Other",
                 is_species_level=False, is_low_resolution=True)
        return r

    # --- Anaerobes (override) ---
    if any(k in o for k in _ANAEROBE):
        if "CUTIBACTERIUM" in o or "PROPIONIBACTERIUM" in o:
            sp = "Cutibacterium acnes" if "ACNES" in o else "Cutibacterium/Propionibacterium spp."
        elif "BACTEROIDES" in o: sp = "Bacteroides spp."
        elif "CLOSTRIDIUM" in o: sp = "Clostridium spp."
        elif "PREVOTELLA" in o: sp = "Prevotella spp."
        elif "PEPTOSTREPTOCOCCUS" in o or "FINEGOLDIA" in o: sp = "Anaerobic gram-positive cocci"
        elif "ANAEROBIC GRAM" in o:
            sp = "Anaerobic gram-positive" if "POSITIVE" in o else "Anaerobic gram-negative"
            r["is_species_level"] = False
        else: sp = "Other anaerobe"
        r.update(species=sp, genus_group="Anaerobe", broad_group="Anaerobe")
        return r

    # --- CoNS ---
    if "STAPHYLOCOCCUS" in o and any(k in o for k in _CONS):
        r.update(species="Coagulase-negative staphylococci", genus_group="Coagulase-negative staphylococci",
                 broad_group="Gram-positive")
        return r
    if o.startswith("STAPHYLOCOCCUS"):  # any other staph
        r.update(species="Coagulase-negative staphylococci", genus_group="Coagulase-negative staphylococci",
                 broad_group="Gram-positive")
        return r

    # --- Enterococcus ---
    if "ENTEROCOCCUS" in o or "PROBABLE ENTEROCOCCUS" in o:
        r.update(species="Enterococcus spp.", genus_group="Enterococcus", broad_group="Gram-positive")
        return r

    # --- Streptococci (beta/viridans/anginosus/nutritionally variant/gemella/aerococcus) ---
    if ("STREPTOCOCC" in o or "STREPTOCOCCI" in o or "ABIOTROPHIA" in o or "GRANULICATELLA" in o
            or "GEMELLA" in o or "AEROCOCCUS" in o or "PEDIOCOCCUS" in o or o.startswith("BETA STREPTOCOCCUS")):
        if "GROUP A" in o: sp = "Streptococcus, group A"
        elif "GROUP B" in o: sp = "Streptococcus, group B"
        elif "ANGINOSUS" in o or "MILLERI" in o: sp = "Streptococcus anginosus group"
        elif "PNEUMONIAE" in o: sp = "Streptococcus pneumoniae"
        else: sp = "Streptococcus spp. (other)"
        r.update(species=sp, genus_group="Streptococcus", broad_group="Gram-positive")
        return r

    # --- Corynebacterium / diphtheroids / other GPR skin flora ---
    if "CORYNEB" in o or "DIPHTHEROID" in o or "LACTOBACILLUS" in o or "BACILLUS" in o or \
       "MICROCOCCUS" in o or "KOCURIA" in o or "ROTHIA" in o or "MICROBACTERIUM" in o or "STREPTOMYCES" in o:
        if "CORYNEB" in o or "DIPHTHEROID" in o: sp = "Corynebacterium spp."
        elif "BACILLUS" in o and "ANTHRACIS" not in o: sp = "Bacillus spp. (not anthracis)"
        else: sp = "Other gram-positive rod/coccus (skin flora)"
        r.update(species=sp, genus_group="Other gram-positive", broad_group="Gram-positive")
        return r

    # --- Gram-negative ---
    if any(k in o for k in _GNB):
        if "ESCHERICHIA" in o: sp = "Escherichia coli"
        elif "PSEUDOMONAS AERUGINOSA" in o: sp = "Pseudomonas aeruginosa"
        elif "PSEUDOMONAS" in o: sp = "Pseudomonas spp. (other)"
        elif "KLEBSIELLA" in o: sp = "Klebsiella spp."
        elif "PROTEUS" in o: sp = "Proteus spp."
        elif "ENTEROBACTER" in o: sp = "Enterobacter spp."
        elif "SERRATIA" in o: sp = "Serratia spp."
        elif "CITROBACTER" in o: sp = "Citrobacter spp."
        elif "MORGANELLA" in o: sp = "Morganella morganii"
        elif "PROVIDENCIA" in o: sp = "Providencia spp."
        elif "ACINETOBACTER" in o: sp = "Acinetobacter spp."
        elif "STENOTROPHOMONAS" in o: sp = "Stenotrophomonas maltophilia"
        else: sp = "Other gram-negative bacillus"
        r.update(species=sp, genus_group=("Escherichia coli" if sp=="Escherichia coli" else
                 ("Pseudomonas aeruginosa" if sp=="Pseudomonas aeruginosa" else "Other gram-negative")),
                 broad_group="Gram-negative")
        return r

    # --- MRSA explicit string caught earlier; TB "positive for" ---
    if "TUBERCULOSIS" in o:
        r.update(species="Mycobacterium tuberculosis complex", genus_group="Mycobacteria", broad_group="Mycobacterial")
        return r

    # fallback: unrecognized but treat as species-level other organism
    r.update(species="Other/unclassified organism", genus_group="Other", broad_group="Other")
    return r


if __name__ == "__main__":
    tests = ["STAPH AUREUS COAG +", "STAPHYLOCOCCUS, COAGULASE NEGATIVE", "PSEUDOMONAS AERUGINOSA",
             "ESCHERICHIA COLI", "MIXED BACTERIAL FLORA", "CUTIBACTERIUM (PROPIONIBACTERIUM) ACNES",
             "PROPIONIBACTERIUM ACNES", "CANDIDA ALBICANS", "YEAST", "GRAM NEGATIVE ROD(S)",
             "POSITIVE FOR METHICILLIN RESISTANT STAPH AUREUS", "CANCELLED", "POSITIVE",
             "BETA STREPTOCOCCUS GROUP B", "ENTEROCOCCUS FAECIUM", "BACTEROIDES FRAGILIS GROUP",
             "CORYNEBACTERIUM SPECIES (DIPHTHEROIDS)", "MYCOBACTERIUM TUBERCULOSIS COMPLEX",
             "POSITIVE FOR HERPES SIMPLEX TYPE 1 (HSV1)", "STAPHYLOCOCCUS LUGDUNENSIS"]
    for t in tests:
        c = classify(t)
        print(f"{t:52s} -> {c['broad_group']:14s} | {c['genus_group']:32s} | org={c['is_organism']} sp={c['is_species_level']} lowres={c['is_low_resolution']}")

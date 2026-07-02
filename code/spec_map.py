"""
Specimen-type taxonomy for MIMIC-IV microbiologyevents (version-controlled; shipped as eTable).
classify_spec(spec_type_desc) -> dict:
  source_category : deep_tissue_bone | synovial_joint | implant_sonication | abscess_deep_fluid
                    | superficial_swab | blood | other
  is_deep_msk     : True for the primary deep musculoskeletal categories
                    (deep_tissue_bone, synovial_joint, implant_sonication)
  is_deep_ext     : deep_msk OR abscess_deep_fluid (sensitivity definition)
is_culture(test_name) -> True if the test is a bacterial/fungal CULTURE (not serology/antigen/toxin/smear/PCR).
"""
import re

def _n(s): return re.sub(r"\s+", " ", str(s).strip().upper())

def classify_spec(spec_type_desc):
    s = _n(spec_type_desc)
    cat = "other"
    if "SONICATION" in s or "FOREIGN BODY" in s:
        cat = "implant_sonication"
    elif "PROSTHETIC JOINT" in s or "JOINT FLUID" in s or "SYNOVIAL" in s:
        cat = "synovial_joint"
    elif ("TISSUE" in s or "BIOPSY" in s or "BONE" in s or "FOOT CULTURE" in s):
        cat = "deep_tissue_bone"
    elif "ABSCESS" in s or s in ("FLUID,OTHER", "FLUID, OTHER") or "FLUID RECEIVED IN" in s or s == "FLUID CULTURE":
        cat = "abscess_deep_fluid"
    elif "SWAB" in s:
        cat = "superficial_swab"
    elif "BLOOD CULTURE" in s:
        cat = "blood"
    else:
        cat = "other"
    deep_msk = cat in ("deep_tissue_bone", "synovial_joint", "implant_sonication")
    deep_ext = deep_msk or cat == "abscess_deep_fluid"
    return dict(source_category=cat, is_deep_msk=deep_msk, is_deep_ext=deep_ext)

# test_name values that are true cultures (bacterial/fungal growth-based)
_CULTURE_POS = ("CULTURE",)
_NOT_CULTURE = ("VIRAL", "VIRUS", "ANTIGEN", "TOXIN", "SEROLOGY", "SMEAR", "STAIN",
                "PCR", "VIRAL LOAD", "ANTIBODY", "REAGIN", "EIA", "MTD", "IMMUN",
                "OVA", "PARASITE", "CRYPTOCOCCAL", "LEGIONELLA URINARY", "BLASTOCYSTIS")

def is_culture(test_name):
    t = _n(test_name)
    if any(k in t for k in _NOT_CULTURE):
        # acid-fast/fungal cultures still count as culture even if 'smear' excluded
        if "CULTURE" in t and "VIRAL" not in t and "VIRUS" not in t:
            return True
        return False
    return any(k in t for k in _CULTURE_POS)


if __name__ == "__main__":
    for s in ["TISSUE","JOINT FLUID","PROSTHETIC JOINT FLUID","Foreign Body - Sonication Culture",
              "Sonication culture, prosthetic joint","ABSCESS","SWAB","BLOOD CULTURE","FOOT CULTURE",
              "FLUID,OTHER","URINE","BONE","SPUTUM"]:
        print(f"{s:38s} -> {classify_spec(s)}")
    print("---is_culture---")
    for t in ["Blood Culture, Routine","TISSUE CULTURE","URINE CULTURE","ANAEROBIC CULTURE",
              "FUNGAL CULTURE","ACID FAST SMEAR","HCV VIRAL LOAD","Immunology","C. DIFFICILE TOXIN",
              "Sonication culture, prosthetic joint","GRAM STAIN"]:
        print(f"{t:38s} -> {is_culture(t)}")

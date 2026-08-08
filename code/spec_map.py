"""
Specimen-type taxonomy for MIMIC-IV microbiologyevents (version-controlled; shipped as eTable).

Anatomical-certainty tiers
--------------------------
MIMIC-IV records a free-text specimen label (`spec_type_desc`) and a test label (`test_name`).
Neither carries an anatomical site, a laterality, or a link to the operative procedure. Specimen
labels therefore differ in how confidently they identify a deep musculoskeletal source, and the
taxonomy separates them into two tiers rather than pooling them:

  tier = "strict"   the label names a musculoskeletal structure or an orthopaedic-implant
                    procedure, and cannot plausibly denote another site:
                      JOINT FLUID, PROSTHETIC JOINT FLUID,
                      explicit sonication (spec label or `Sonication culture, prosthetic joint`),
                      explicit prosthetic-joint-fluid culture test.
                    This tier is the primary analytic cohort.

  tier = "generic"  the label is compatible with a deep musculoskeletal source given an
                    orthopaedic-infection admission code, but is not site-specific:
                      TISSUE, BIOPSY, and FOREIGN BODY without a sonication test.
                    Reported as a prespecified sensitivity tier only, never pooled into the
                    primary estimate.

There is no explicit BONE specimen label anywhere in MIMIC-IV v3.1; bone specimens, where they
exist, are submitted under the generic TISSUE label and cannot be distinguished from soft-tissue
specimens. This is a property of the source data, not a choice, and it bounds every estimate the
generic tier contributes to.

classify_spec(spec_type_desc, test_names=None) -> dict:
  source_category : deep_tissue_bone | synovial_joint | implant_sonication | abscess_deep_fluid
                    | superficial_swab | blood | other
  tier            : 'strict' | 'generic' | None
  is_deep_strict  : True for the primary (strict) analytic cohort
  is_deep_generic : True for the sensitivity tier
  is_deep_msk     : is_deep_strict OR is_deep_generic (the pooled legacy definition)
  is_deep_ext     : is_deep_msk OR abscess_deep_fluid (widest sensitivity definition)

is_culture(test_name) -> True if the test is a bacterial/fungal CULTURE (not serology/antigen/
                         toxin/smear/PCR).
"""
import re


def _n(s):
    return re.sub(r"\s+", " ", str(s).strip().upper())


# Test names that by themselves establish an orthopaedic-implant or prosthetic-joint source,
# whatever the specimen label says. In MIMIC-IV these are applied to both
# "Foreign Body - Sonication Culture" and bare "FOREIGN BODY" specimen labels.
_SONICATION_TESTS = ("SONICATION CULTURE, PROSTHETIC JOINT",)
_PJ_FLUID_TESTS = ("ANAEROBIC CULTURE, PROSTHETIC JOINT FLUID",)


def classify_spec(spec_type_desc, test_names=None):
    s = _n(spec_type_desc)
    tests = {_n(t) for t in (test_names or []) if t is not None}

    has_sonication_test = any(t in tests for t in _SONICATION_TESTS)
    has_pj_fluid_test = any(t in tests for t in _PJ_FLUID_TESTS)

    cat = "other"
    tier = None

    if "SONICATION" in s or has_sonication_test:
        # Explicit sonication, either in the specimen label or in the test label.
        cat, tier = "implant_sonication", "strict"
    elif "PROSTHETIC JOINT" in s or "JOINT FLUID" in s or "SYNOVIAL" in s or has_pj_fluid_test:
        cat, tier = "synovial_joint", "strict"
    elif "MARROW" in s:
        cat = "other"                      # bone marrow is not a musculoskeletal-infection specimen
    elif "FOREIGN BODY" in s:
        # A bare "foreign body" is not necessarily an orthopaedic implant; without a sonication
        # test it cannot be attributed to the coded joint or bone infection.
        cat, tier = "implant_sonication", "generic"
    elif "TISSUE" in s or "BIOPSY" in s or "BONE" in s:
        # No explicit BONE label exists in MIMIC-IV; this branch is TISSUE and BIOPSY in practice.
        cat, tier = "deep_tissue_bone", "generic"
    elif ("ABSCESS" in s or s in ("FLUID,OTHER", "FLUID, OTHER")
          or "FLUID RECEIVED IN" in s or s == "FLUID CULTURE"):
        cat = "abscess_deep_fluid"
    elif "SWAB" in s or "FOOT CULTURE" in s:
        # FOOT CULTURE reclassified as superficial: MIMIC foot cultures are frequently superficial
        # diabetic-foot specimens, not deep bone/tissue.
        cat = "superficial_swab"
    elif "BLOOD CULTURE" in s:
        cat = "blood"

    is_strict = tier == "strict"
    is_generic = tier == "generic"
    deep_msk = is_strict or is_generic
    deep_ext = deep_msk or cat == "abscess_deep_fluid"
    return dict(source_category=cat, tier=tier, is_deep_strict=is_strict,
                is_deep_generic=is_generic, is_deep_msk=deep_msk, is_deep_ext=deep_ext)


# test_name values that are true cultures (bacterial/fungal growth-based).
# "TISSUE" is the laboratory's label for the routine aerobic tissue culture and carries no
# "culture" token, so it is allowlisted explicitly.
_CULTURE_EXACT = ("TISSUE",)
_CULTURE_POS = ("CULTURE",)
_NOT_CULTURE = ("VIRAL", "VIRUS", "ANTIGEN", "TOXIN", "SEROLOGY", "SMEAR", "STAIN",
                "PCR", "VIRAL LOAD", "ANTIBODY", "REAGIN", "EIA", "MTD", "IMMUN",
                "OVA", "PARASITE", "CRYPTOCOCCAL", "LEGIONELLA URINARY", "BLASTOCYSTIS")


def is_culture(test_name):
    t = _n(test_name)
    if t in _CULTURE_EXACT:
        return True
    if any(k in t for k in _NOT_CULTURE):
        # acid-fast/fungal cultures still count as culture even if 'smear' excluded
        if "CULTURE" in t and "VIRAL" not in t and "VIRUS" not in t:
            return True
        return False
    return any(k in t for k in _CULTURE_POS)


# ---------------------------------------------------------------------------------------------
# Bacterial-culture subset.
#
# The no-growth measure is defined on routine bacterial culture only. Fungal, acid-fast and
# Nocardia cultures are answered by their own targeted comment language ("NO FUNGUS ISOLATED",
# "NO MYCOBACTERIA ISOLATED"), and a specimen that grows a bacterium is routinely negative on
# those panels. Pooling them would count the same specimen as negative on the targeted panels
# while positive on the bacterial one.
# ---------------------------------------------------------------------------------------------
_NON_BACTERIAL_CULTURE = ("FUNGAL", "ACID FAST", "AFB", "NOCARDIA", "MYCO", "LEGIONELLA",
                          "BRUCELLA", "VIRAL", "VIRUS", "ENTEROVIRUS", "VARICELLA")


def is_bacterial_culture(test_name):
    t = _n(test_name)
    if not is_culture(t):
        return False
    return not any(k in t for k in _NON_BACTERIAL_CULTURE)


if __name__ == "__main__":
    cases = [
        ("TISSUE", []),
        ("BIOPSY", []),
        ("JOINT FLUID", []),
        ("PROSTHETIC JOINT FLUID", ["Anaerobic culture, Prosthetic Joint Fluid"]),
        ("Foreign Body - Sonication Culture", ["Sonication culture, prosthetic joint"]),
        ("FOREIGN BODY", ["Sonication culture, prosthetic joint"]),
        ("FOREIGN BODY", ["WOUND CULTURE"]),
        ("ABSCESS", []),
        ("SWAB", []),
        ("BLOOD CULTURE", []),
        ("FOOT CULTURE", []),
        ("FLUID,OTHER", []),
        ("URINE", []),
        ("BONE MARROW", []),
    ]
    for s, t in cases:
        r = classify_spec(s, t)
        print(f"{s:38s} {str(t):46s} -> {r['source_category']:20s} tier={r['tier']}")
    print("---is_culture / is_bacterial_culture---")
    for t in ["Blood Culture, Routine", "TISSUE", "WOUND CULTURE", "ANAEROBIC CULTURE",
              "FLUID CULTURE", "Sonication culture, prosthetic joint",
              "Anaerobic culture, Prosthetic Joint Fluid", "FUNGAL CULTURE",
              "ACID FAST CULTURE", "ACID FAST SMEAR", "GRAM STAIN", "NOCARDIA CULTURE",
              "HCV VIRAL LOAD", "C. DIFFICILE TOXIN"]:
        print(f"{t:44s} culture={is_culture(t)!s:5s} bacterial={is_bacterial_culture(t)}")

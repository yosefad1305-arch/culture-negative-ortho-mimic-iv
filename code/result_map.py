"""
Culture result-status classification (version-controlled; shipped as eTable).

A specimen enters the no-growth denominator only if the laboratory reported a completed routine
bacterial culture with no growth. Two failure modes are guarded against explicitly:

  Inferring no growth from the absence of an organism row. Cancelled, unsuitable and
  unreportable tests would otherwise be absorbed into the negative numerator.

  Accepting a panel-specific negative as an overall negative. A deep specimen typically carries
  several bacterial cultures (routine aerobic, anaerobic, and sometimes a screen for named
  organisms). "No anaerobes isolated" is a completed negative for the anaerobic panel only; it
  says nothing about whether the routine culture grew. Only an explicit completed no-growth
  statement on a routine bacterial culture establishes that the specimen had no growth.

Precedence, applied in this order:

  1. positive        a recognised organism was recovered on a bacterial-culture row
  2. cancelled       the test was cancelled, credited, or the specimen was unsuitable
  3. indeterminate   the culture was not completed as an ordinary readout: mixed growth or
                     overgrowth, an abbreviated workup, or an inability to exclude pathogens;
                     also an absent or redacted comment
  4. negative        an explicit completed no-growth statement on a routine bacterial culture
  5. indeterminate   anything else

Incomplete and cancelled outcomes therefore take precedence over a negative companion panel: a
specimen reported as "no anaerobes isolated" alongside "mixed bacterial types, abbreviated workup"
is indeterminate, not negative.

Only 'positive' and 'negative' are evaluable. 'cancelled' and 'indeterminate' are excluded and
reported as an explicit accounting line, so the denominator is auditable.

The rules below were written against the complete set of distinct comment strings observed on
deep-tier bacterial-culture rows carrying no organism in this cohort (12 strings), not a sample.
"""
import re

# Explicit completed no-growth on a routine bacterial culture. These, and only these, establish
# that the specimen grew nothing.
_NEGATIVE_PATTERNS = (
    r"\bNO GROWTH\b",
    r"\bNO SIGNIFICANT GROWTH\b",
)

# Completed negatives for a named panel only. Recorded so they are not silently treated as
# uninterpretable, but never sufficient on their own to call a specimen no-growth.
_PANEL_NEGATIVE_PATTERNS = (
    r"\bNO ANAEROBES ISOLATED\b",
    r"\bNO ANAEROBIC ORGANISMS ISOLATED\b",
    r"\bNO FUNG(?:US|I|AL ELEMENTS) (?:ISOLATED|SEEN)\b",
    r"\bNO MYCOBACTERIA ISOLATED\b",
    r"\bNO ACID FAST BACILLI\b",
    r"\bNO MRSA ISOLATED\b",
    r"\bNO CAMPYLOBACTER FOUND\b",
    r"\bNONE ISOLATED\b",
)

# The culture was not completed as an ordinary readout. Growth was present but not worked up, or
# pathogens could not be excluded. These outrank any negative language on the same specimen.
_INCOMPLETE_PATTERNS = (
    r"\bABBREVIATED WORKUP\b",
    r"\bMIXED BACTERIAL (?:FLORA|TYPES)\b",
    r"\bUNABLE TO R/?O\b",
    r"\bOVERGROWTH\b",
    r"\bSWARMING\b",
    r"\bCONSISTENT WITH SKIN AND/OR GENITAL CONTAMINATION\b",
)

# Cancellation / unsuitable specimen.
_CANCELLED_PATTERNS = (
    r"\bTEST CANCELLED\b",
    r"\bCANCELLED\b",
    r"\bCANCELED\b",
    r"\bPATIENT CREDITED\b",
    r"\bINAPPROPRIATE SPECIMEN\b",
    r"\bUNABLE TO PROCESS\b",
    r"\bNOT PROCESSED\b",
    r"\bSPECIMEN REJECTED\b",
    r"\bUNSATISFACTORY\b",
    r"\bDUPLICATE (?:SPECIMEN|REQUEST|ORDER)\b",
    r"\bTEST NOT PERFORMED\b",
)

# org_name strings that record an administrative outcome rather than microbial growth.
_ADMIN_ORG = {"CANCELLED", "CANCELED"}

_NEG_RE = re.compile("|".join(_NEGATIVE_PATTERNS))
_PANEL_RE = re.compile("|".join(_PANEL_NEGATIVE_PATTERNS))
_INCOMPLETE_RE = re.compile("|".join(_INCOMPLETE_PATTERNS))
_CANC_RE = re.compile("|".join(_CANCELLED_PATTERNS))


def _n(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().upper())


def is_admin_org(org_name):
    """True if org_name records an administrative outcome, not growth."""
    return _n(org_name) in _ADMIN_ORG


def comment_status(comment):
    """
    Classify a single laboratory comment.

    Returns one of: 'cancelled', 'incomplete', 'negative', 'panel_negative', 'indeterminate'.
    Cancellation and incompleteness are tested before negative language, because a cancelled or
    unworked-up culture frequently carries a negative-sounding clause.
    """
    c = _n(comment)
    if not c or c == "___":
        # "___" is the de-identification placeholder: a comment existed but its content was
        # removed, so it establishes neither a completed negative nor a cancellation.
        return "indeterminate"
    if _CANC_RE.search(c):
        return "cancelled"
    if _INCOMPLETE_RE.search(c):
        return "incomplete"
    if _NEG_RE.search(c):
        return "negative"
    if _PANEL_RE.search(c):
        return "panel_negative"
    return "indeterminate"


def classify_result(has_organism, comments):
    """
    has_organism : bool, at least one recognised (non-administrative) organism on the specimen's
                   bacterial-culture rows
    comments     : iterable of comment strings from those same rows
    """
    if has_organism:
        return "positive"
    statuses = [comment_status(c) for c in comments]
    if any(s == "cancelled" for s in statuses):
        return "cancelled"
    if any(s == "incomplete" for s in statuses):
        return "indeterminate"
    if any(s == "negative" for s in statuses):
        return "negative"
    # A panel-specific negative on its own does not establish that the routine culture grew
    # nothing, so it is not evaluable.
    return "indeterminate"


if __name__ == "__main__":
    cases = [
        # (has_organism, comments, expected)
        (False, ["NO GROWTH."], "negative"),
        (False, ["NO SIGNIFICANT GROWTH."], "negative"),
        (False, ["NO GROWTH.", "NO ANAEROBES ISOLATED."], "negative"),
        # Panel-specific negative alone is NOT an overall no-growth result.
        (False, ["NO ANAEROBES ISOLATED."], "indeterminate"),
        (False, ["NO FUNGUS ISOLATED."], "indeterminate"),
        (False, ["NO MYCOBACTERIA ISOLATED."], "indeterminate"),
        # Incompleteness outranks a negative companion panel.
        (False, ["NO ANAEROBES ISOLATED.",
                 "THIS CULTURE CONTAINS MIXED BACTERIAL TYPES (>=3) SO AN ABBREVIATED WORKUP IS "
                 "PERFORMED."], "indeterminate"),
        (False, ["NO GROWTH.", "DUE TO MIXED BACTERIAL TYPES (>=3) AN ABBREVIATED WORKUP IS "
                 "PERFORMED;"], "indeterminate"),
        (False, ["UNABLE TO R/O OTHER PATHOGENS DUE TO OVERGROWTH OF SWARMING PROTEUS SPP."],
         "indeterminate"),
        (False, ["MIXED BACTERIAL FLORA-CULTURE SCREENED FOR B. FRAGILIS, C. PERFRINGENS, AND "
                 "C. SEPTICUM.  NONE ISOLATED."], "indeterminate"),
        # Cancellation outranks everything except recovered growth.
        (False, ["TEST CANCELLED, PATIENT CREDITED."], "cancelled"),
        (False, ["NO GROWTH.", "TEST CANCELLED, PATIENT CREDITED."], "cancelled"),
        (False, ["TEST CANCELLED BY LABORATORY.  PATIENT CREDITED.  INAPPROPRIATE SPECIMEN "
                 "COLLECTION (SWAB) FOR FUNGAL SMEAR (___)."], "cancelled"),
        # Uninterpretable.
        (False, ["___"], "indeterminate"),
        (False, [None], "indeterminate"),
        (False, ["GRAM POSITIVE COCCI IN CLUSTERS."], "indeterminate"),
        # Growth always wins.
        (True, ["NO ANAEROBES ISOLATED."], "positive"),
        (True, ["NO GROWTH."], "positive"),
    ]
    ok = True
    for has_org, cs, expected in cases:
        got = classify_result(has_org, cs)
        flag = "ok " if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"  {flag} org={has_org!s:5s} {str(cs)[:78]:80s} -> {got:14s} (expected {expected})")
    print("\nall result-status tests passed" if ok else "\nRESULT-STATUS TESTS FAILED")

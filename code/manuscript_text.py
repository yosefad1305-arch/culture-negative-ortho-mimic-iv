"""
Manuscript body text. Kept separate from the assembly code in 50_build_docx.py so that the prose
is reviewable on its own and the numbers can be checked line by line against results_digest.json.

Citations are plain bracketed numerals. No reference-manager field codes are used anywhere, as
required by the journal.
"""

TITLE = ("Specimen-label cohorts and culture estimates in code-defined bone and joint infection: "
         "a MIMIC-IV measurement study")

RUNNING_HEAD = "Specimen-label cohorts and culture estimates"

KEYWORDS = ("Prosthetic joint infection; Osteomyelitis; Culture-negative infection; "
            "Antimicrobial resistance; Electronic health records; Measurement bias")

ABSTRACT = [
    ("Purpose", "Culture-based descriptions of bone and joint infection are increasingly drawn "
     "from databases in which specimens carry free-text laboratory labels rather than anatomical "
     "sites. We measured how far such estimates depend on the labels analysed."),
    ("Methods", "Measurement study in MIMIC-IV version 3.1, a de-identified single-centre US "
     "database (anchor-year groups 2008-2010 to 2020-2022), of episodes coded for prosthetic "
     "joint infection, native osteomyelitis or other orthopaedic device infection. Specimen "
     "labels were split into a source-specific tier (joint "
     "fluid, prosthetic joint "
     "fluid, sonication) and a generic tier (tissue, biopsy, foreign body). No growth required a "
     "completed routine bacterial culture; first isolates were defined within each tier. "
     "Proportions carry patient-clustered 95% confidence intervals (CIs)."),
    ("Results", "Of 7697 episodes (4358 patients), 653 contributed 885 evaluable source-specific "
     "and 3397 contributed 6777 generic specimens. Between cohorts, no growth was 48.0% (95% CI, "
     "44.1-51.9) versus 34.0% (32.2-35.8) and the polymicrobial fraction 10.9% (7.7-14.4) versus "
     "42.1% (40.1-44.0), but the cohorts differed in case mix and specimens per episode (median 1 "
     "versus 3). Among the 487 episodes contributing both tiers, the source-specific tier was "
     "entirely negative in 40.7% and the generic tier in 31.6% (difference 9.0 points; 4.1-13.8); "
     "an episode-stratified per-specimen model did not detect an association with the label (odds "
     "ratio, 0.86; 0.64-1.15)."),
    ("Conclusion", "Culture estimates differ substantially between specimen-label-defined "
     "cohorts, while within episodes no per-specimen association with the label was detected. "
     "Such studies should report the label set, deduplication scope and low-resolution-growth "
     "rule."),
]

INTRODUCTION = [
    "Bone and joint infection, whether periprosthetic joint infection or native osteomyelitis, is "
    "diagnosed and managed largely on the output of the clinical microbiology laboratory. The "
    "identity of the organism, whether the infection is polymicrobial, and the susceptibility "
    "profile determine antimicrobial choice and duration and inform the decision to retain or "
    "remove hardware [1-3]. The specimen that yields no organism is a recurring diagnostic "
    "problem: culture-negative infection, reported in 5% to 42% of series, forces prolonged "
    "empiric therapy and complicates source control [2,4].",

    "Because single-centre surgical series are laborious and their underlying records cannot be "
    "re-examined, culture-based descriptions of these infections are increasingly derived from "
    "large electronic health record databases. That shift carries a measurement problem that has "
    "attracted little scrutiny. A surgical series knows which specimen came from the infected "
    "bone; a database does not. Microbiology tables record a free-text specimen label written for "
    "laboratory workflow, not an anatomical site, a laterality, or a link to the operation that "
    "produced the specimen. A tissue culture taken during an admission coded for osteomyelitis "
    "may or may not have come from the infected bone, and a specimen labelled only as a foreign "
    "body may or may not be an orthopaedic implant. Investigators must therefore choose which "
    "labels to admit, and that choice is rarely stated or examined.",

    "We used MIMIC-IV to measure what that choice does. We separated specimen labels by "
    "whether they name a musculoskeletal source, recomputed the organism spectrum, the "
    "polymicrobial fraction, the resistance profile and the no-growth fraction within each label "
    "set, and then asked what a between-cohort comparison cannot answer: within the episodes that "
    "contributed both kinds of specimen, and so hold the patient and admission fixed, do the two "
    "labels behave differently? We applied the same scrutiny to two further choices that database "
    "studies commonly leave implicit: whether repeated recoveries of one strain are counted once "
    "or many times, and how growth that was never speciated is handled.",
]

METHODS = [
    ("Data source and reporting",
     ["We analysed MIMIC-IV version 3.1, a de-identified database of patients admitted to a "
      "single US academic medical centre, available to credentialed users under a data use "
      "agreement [5,6]. Reporting followed the Strengthening the Reporting of Observational "
      "Studies in Epidemiology (STROBE) statement and its extension for routinely collected data "
      "(RECORD) (Online Resource 1)."]),

    ("Ethics",
     ["This study was performed in line with the principles of the Declaration of Helsinki. It is "
      "a secondary analysis of an existing, de-identified, credentialed-access database. The "
      "collection and sharing of MIMIC-IV were approved by the institutional review board of the "
      "Beth Israel Deaconess Medical Center, which granted a waiver of informed consent for that "
      "resource; that approval covers the source database rather than this particular analysis, "
      "and no study-specific ethical review was sought or required for secondary use of "
      "the de-identified database under its data use agreement. No identifiable patient "
      "information was accessed."]),

    ("Cohort",
     ["We identified hospital episodes (unique admissions) carrying an International "
      "Classification of Diseases, Ninth or Tenth Revision, diagnosis of prosthetic joint "
      "infection or native osteomyelitis in any diagnosis position; episodes coded for infection "
      "of other internal orthopaedic devices, which are not joint prostheses, formed a separate "
      "device-infection group. Code lists are given in Online Resource 1. When both prosthetic "
      "joint infection and osteomyelitis codes were present, the episode was assigned to "
      "prosthetic joint infection, with a co-occurrence flag retained for sensitivity analysis.",
      "All eligible episodes in the database were included; no sampling was applied. Individual "
      "chart dates in MIMIC-IV carry a random per-patient offset and have no calendar meaning, so "
      "the study period is defined by the patient anchor-year group, which spans 2008-2010 "
      "through 2020-2022. Episode counts by anchor-year group are given in Online Resource 1."]),

    ("Specimen label tiers",
     ["Specimen labels were assigned to one of two tiers by the rules below, which are published as code. The "
      "source-specific tier comprises labels that name a musculoskeletal structure or an "
      "orthopaedic-implant procedure: joint fluid, prosthetic joint fluid, and explicit implant "
      "sonication, the last identified either from the specimen label or from a sonication "
      "culture test name. The generic tier comprises labels compatible with a deep "
      "musculoskeletal source in an orthopaedic-infection admission but not specific to one: "
      "tissue, biopsy, and foreign body without an accompanying sonication test. The full "
      "label-to-tier mapping, with counts, is given in Online Resource 1.",
      "MIMIC-IV contains no explicit bone specimen label. Bone specimens, where they exist, are "
      "submitted under the generic tissue label and cannot be distinguished from soft tissue. This "
      "is a property of the source data rather than an analytic choice, and it bounds every "
      "estimate the generic tier contributes to.",
      "The tiers separate specimen-category specificity, not infection attribution. A "
      "source-specific label identifies the kind of structure sampled; it does not establish that "
      "the specimen came from the bone, joint, side or prosthesis named in the diagnosis code, and "
      "MIMIC-IV records no laterality or operative linkage that would allow this to be checked. "
      "Joint fluid may be aspirated during an osteomyelitis-coded admission for a concurrent or "
      "unrelated indication. Neither tier is a validated sample of the coded infection, and the "
      "infection-type subgroups inherit that limitation.",
      "Organism names were normalised with a version-controlled dictionary. Laboratory strings "
      "that name an organism in order to exclude it, such as a non-fermenting gram-negative rod "
      "reported as not Pseudomonas aeruginosa, are parsed for negation so the excluded organism is "
      "not recorded as present."]),

    ("Culture result status",
     ["A specimen was counted in the no-growth denominator only where the laboratory reported a "
      "completed routine bacterial culture with no growth. Each specimen was classified from the "
      "laboratory's own reported comments in a fixed precedence: recovered growth, then "
      "cancellation or an unsuitable specimen, then an incomplete readout, then an explicit "
      "completed no-growth statement, then uninterpretable. Only the first and fourth are "
      "evaluable.",
      "Two distinctions matter. First, incompleteness outranks negative language on the same "
      "specimen: a culture reported as mixed bacterial types with an abbreviated workup, or as "
      "unable to exclude pathogens because of overgrowth, is not evaluable even if a companion "
      "panel was negative. Second, a panel-specific negative is not an overall negative. A deep "
      "specimen typically carries several cultures, and a statement that no anaerobes, fungi or "
      "mycobacteria were isolated is a completed negative for that panel only. These rules were "
      "written against the complete set of distinct comment strings observed on deep-tier "
      "bacterial-culture rows carrying no organism in this cohort, which numbered 12, rather than "
      "against a sample; they and an audit of classified specimens are given in Online Resource 1. "
      "Non-culture tests (serology, antigen, toxin, viral and smear-only assays) were excluded "
      "throughout."]),

    ("Isolate deduplication",
     ["An organism recovered from several specimens in one admission represents one infecting "
      "strain, not several isolates. Organism-spectrum and resistance analyses were therefore "
      "computed on first isolates, defined as the first recovery of a given organism identity in "
      "collection-time order, within an episode (primary) and within a patient (sensitivity), "
      "following the first-isolate principles of Clinical and Laboratory Standards Institute "
      "document M39 [16]. Results for all isolates are reported alongside so the effect of the "
      "rule is visible.",
      "First-isolate flags were computed separately within each analytic tier. Computing them "
      "once across every culture in the admission would allow an earlier blood, urine, swab or "
      "generic-tissue isolate to suppress a later source-specific isolate of the same organism, "
      "so that the first isolate among source-specific specimens would silently mean the first "
      "such isolate not preceded by that organism anywhere else. The scope of the rule is "
      "reported because it is consequential."]),

    ("Polymicrobial infection",
     ["A specimen or episode was polymicrobial if at least two distinct organisms were recovered. "
      "Because two laboratory strings can denote one organism, and because collapsing to a coarse "
      "reporting label can merge two genuinely different organisms, the fraction is reported "
      "under both the raw laboratory string and the normalised dictionary identity.",
      "Both of those rules count only growth that was identified to genus or species. Growth that "
      "was never speciated, principally an explicit report of mixed bacterial flora, contributes "
      "no organisms under a speciated-only rule and is scored monomicrobial, which is a reporting "
      "artefact rather than a microbiological finding. A third rule therefore counts "
      "an explicit report of mixed flora as polymicrobial, and the fraction of episodes with such "
      "a report is given separately."]),

    ("Microbiological methods and susceptibility interpretation",
     ["MIMIC-IV records the result of routine clinical microbiology testing as reported by the "
      "hospital laboratory. It does not record culture media, incubation atmosphere or duration, "
      "whether periprosthetic tissue was inoculated into blood culture bottles [13], or whether "
      "explanted hardware underwent sonication under a defined protocol [14]; specimens labelled "
      "as sonicate were taken at face value. It likewise does not record how many independent "
      "periprosthetic specimens were submitted per procedure, which underpins the conventional "
      "microbiological criterion for prosthetic joint infection [15]. Prolonged incubation for "
      "indolent organisms such as "
      "Cutibacterium, which requires at least 13 days for reliable recovery [7], cannot be "
      "verified. Nucleic acid amplification and 16S rRNA results are not captured, so a specimen "
      "negative by culture but positive by a molecular assay is counted here as no growth.",
      "Susceptibility results are stored as the laboratory's categorical interpretation "
      "(susceptible, intermediate, resistant); minimum inhibitory concentrations and the "
      "breakpoint version applied are not available. Because the source institution is a United "
      "States academic centre, interpretations reflect contemporaneous Clinical and Laboratory "
      "Standards Institute breakpoints rather than EUCAST. Resistance is reported throughout as "
      "laboratory-reported categorical resistance and is not directly comparable with "
      "EUCAST-interpreted series. Methicillin-resistant S. aureus was defined by an "
      "oxacillin-resistant isolate among S. aureus with an interpretable oxacillin result."]),

    ("Statistical analysis",
     ["Specimens are clustered within episodes and episodes within patients, so every interval and "
      "comparison accounts for that clustering. Proportions carry a patient-clustered bootstrap "
      "percentile 95% CI from 2000 resamples of patients; exact Clopper-Pearson intervals appear in "
      "Online Resource 1 for reference only. Where no events were observed, no interval is reported "
      "as zero to zero; instead an exact one-sided 97.5% upper bound is computed on the "
      "contributing patients. Group comparisons use logistic regression with patient-clustered "
      "robust standard errors rather than specimen-level chi-square tests, which would treat "
      "correlated specimens as independent.",
      "The primary comparison between tiers is made within episodes that contributed both, so "
      "that the patient and admission are held fixed. A tier counts as negative for an episode "
      "only when every one of its evaluable specimens grew nothing; defining it as any negative "
      "specimen would not be an episode-level measure and would favour whichever tier contributes "
      "more specimens. Because episodes are correlated within patients, paired inference uses a "
      "bootstrap of the paired difference that resamples patients rather than episodes; the exact "
      "McNemar test is reported alongside for reference only, as it assumes independent pairs.",
      "Because even the all-negative definition depends on how many specimens each tier "
      "contributes, two further analyses remove that dependence. An episode-stratified "
      "conditional logistic model uses only within-episode variation and conditions out every "
      "episode-level characteristic, at the cost of discarding episodes in which all specimens "
      "shared the same result. Because episodes are nested within patients, the conditional "
      "likelihood's model-based standard errors understate uncertainty, so its interval is "
      "obtained by resampling patients and refitting; the model-based interval is reported "
      "alongside for reference. A one-to-one matched subset is restricted to episodes contributing "
      "exactly one evaluable specimen in each tier. Between-cohort comparisons are reported "
      "alongside and are interpreted as descriptions of differently selected cohorts, not as "
      "effects of the label.",
      "Variation in no growth by age band, sex, race group, insurance category and infection type "
      "was estimated with and without adjustment for the number of specimens obtained, with "
      "prosthetic joint infection as the reference category for infection type. The "
      "Benjamini-Hochberg procedure controlled the false discovery rate within each model "
      "(2-sided alpha of .05). Era was represented by the MIMIC-IV anchor-year group, the only "
      "admissible era marker given per-patient date shifting. Agent-level resistance was not "
      "reported where fewer than 10 isolates were tested.",
      "Analyses used Python 3.13 with fixed random seeds; package versions are in Online Resource 1. "
      "All study design, analyses, interpretations and conclusions are the authors' own, and the "
      "authors take full responsibility for the integrity of the work."]),
]

RESULTS = [
    ("Cohort and specimen accounting",
     ["Of 7697 orthopaedic-infection episodes in 4358 patients, 5715 (74.3%) were native "
      "osteomyelitis, 1089 (14.1%) prosthetic joint infection, and 893 (11.6%) other device "
      "infection (Table 1). A source-specific specimen was obtained in 653 episodes (8.5%; 552 "
      "patients) and a generic specimen in 3397 (44.1%). The source-specific cohort was "
      "predominantly prosthetic joint infection (439 of 653, 67.2%), whereas the generic tier was "
      "predominantly osteomyelitis.",
      "Requiring a completed, reported routine bacterial culture excluded few specimens: of 887 "
      "source-specific and 6811 generic bacterial cultures, 885 and 6777 respectively were "
      "evaluable, an exclusion of 0.47% across all deep specimens (Online Resource 1)."]),

    ("Estimates differ between label-defined cohorts",
     ["No growth was reported in 48.0% of evaluable source-specific specimens (425 of 885; "
      "patient-clustered 95% CI, 44.1-51.9) against 34.0% of generic specimens (2304 of 6777; "
      "32.2-35.8); the pooled figure was 35.6% (2729 of 7662; 33.9-37.4), close to the generic "
      "tier because generic specimens outnumber source-specific ones almost eightfold (Fig. 1a).",
      "Among source-specific culture-positive episodes, 10.9% were polymicrobial (38 of 348; "
      "7.7-14.4), against 42.1% pooled (1174 of 2789; 40.1-44.0). Using the normalised dictionary "
      "rather than the raw laboratory string changed this by about a percentage point in either "
      "tier (source-specific 10.3%; pooled 41.1%).",
      "Within the source-specific tier, no growth was higher in synovial or joint fluid (55.1%; "
      "50.8-59.7) than in implant sonicate (24.5%; 18.4-30.6) (Fig. 1b)."]),

    ("Within-episode analyses did not detect a per-specimen association with label tier",
     ["In the 487 episodes (421 patients) that contributed both a source-specific and a generic "
      "evaluable specimen, the patient and admission are held fixed. The two tiers differ in how "
      "much they contribute: the median episode supplied 1 evaluable source-specific specimen and "
      "3 generic ones.",
      "Counting a tier as negative for an episode only when every one of its evaluable specimens "
      "grew nothing, the source-specific tier was entirely negative in 198 of 487 episodes "
      "(40.7%) and the generic tier in 154 of 487 (31.6%), a paired difference of 9.0 percentage "
      "points (patient-clustered 95% CI, 4.1-13.8; bootstrap P = .0005). Of the 487 episodes, 102 "
      "were entirely negative on both tiers and 237 had at least one positive specimen in each; "
      "of the 148 discordant episodes, 96 were entirely negative only on the source-specific tier "
      "and 52 only on the generic tier (Fig. 1d). This episode-level difference runs in the same "
      "direction as the between-cohort comparison.",
      "Two further analyses, which do not depend on how many specimens each tier contributed, did "
      "not detect a statistically significant within-episode association. An episode-stratified "
      "conditional logistic model uses only "
      "within-episode variation and conditions out every episode-level characteristic; episodes "
      "whose specimens do not vary in both outcome and tier contribute nothing to the conditional "
      "likelihood, so the estimate rests on 1227 specimens in 252 informative episodes from 233 "
      "patients, of whom 16 contributed more than one informative episode. With uncertainty "
      "clustered on patients, the odds of no growth for a source-specific rather than a generic "
      "specimen were 0.86 (95% CI, 0.64-1.15; P = .33); the unclustered model-based interval was "
      "narrower (0.67-1.10). In the 75 episodes (74 patients) that contributed exactly one "
      "evaluable specimen in each tier, and where the two are matched one to one by construction, "
      "25 were negative only on the source-specific specimen and 14 only on the generic one "
      "(exact McNemar P = .11).",
      "The full paired cohort, both inference approaches and the retained conditional sample are "
      "tabulated in Online Resource 1, eTable 12."]),

    ("Deduplication scope and low-resolution growth",
     ["Scoping the first-isolate rule "
      "within the tier being analysed, rather than across every culture in the admission, changed "
      "the source-specific isolate count by 43%: 175 of 405 episode-first source-specific "
      "isolates (43.2%) had been preceded by the same organism on a blood, urine, swab or generic "
      "specimen and would have been discarded by a globally scoped rule, though they are the first "
      "recovery among source-specific specimens.",
      "Counting an explicit report of mixed bacterial flora as polymicrobial, rather than "
      "scoring it monomicrobial because nothing was speciated, raised the pooled polymicrobial "
      "fraction from 42.1% to 50.8% (1417 of 2789; 48.7-52.8). Mixed flora was reported in 23.3% "
      "of pooled culture-positive episodes (651 of 2789; 21.7-24.9) but only 0.3% of "
      "source-specific ones, so it affects generic tissue almost exclusively."]),

    ("Organism spectrum and resistance",
     ["Among source-specific isolates, S. aureus was the most frequent organism under every rule, "
      "at 48.2% of 510 unduplicated isolates, 45.3% of 395 first isolates per episode (179 of "
      "395; 39.9-50.9) and 43.3% of 367 first isolates per patient (Table 2, Fig. 2). "
      "Coagulase-negative staphylococci (15.7%), streptococci (11.4%) and Cutibacterium (3.3%) "
      "followed under the episode-first rule. "
      "The pooled tier gives a different spectrum, with S. aureus at 29.0% of 4547 episode-first "
      "isolates and a larger contribution from enterococci, anaerobes and gram-negative "
      "organisms.",
      "Across all deep specimens, 43.2% of 1143 S. aureus isolates with an interpretable "
      "oxacillin result were resistant; restricting to first isolates gave 43.0% per episode (353 "
      "of 820; 39.3-46.6) and 40.5% per patient (274 of 676; 36.8-44.2) (Table 3). Erythromycin "
      "resistance was highest in the panel (60.5%; 56.9-63.9), followed by levofloxacin (40.2%) "
      "and clindamycin (39.7%); resistance was low to tetracycline (9.4%), trimethoprim-"
      "sulfamethoxazole (3.2%), rifampin (3.2%) and gentamicin (2.2%), and no isolate was "
      "vancomycin-resistant (0 of 364, upper 97.5% bound 1.1% on the contributing patients). "
      "In the gram-negative panel "
      "resistance was highest to ciprofloxacin (23.7%; 20.5-27.2) and trimethoprim-"
      "sulfamethoxazole (23.5%) and lowest to meropenem (3.9%; 2.6-5.4) and tobramycin (6.1%) "
      "(Table 4, Fig. 3).",
      "Only 15.8% of episodes involved an intensive care stay, and oxacillin resistance was 44.5% "
      "in intensive-care-linked episodes against 42.8% in the remainder (odds ratio, 1.07; "
      "0.74-1.56; P = .70). Across anchor-year groups it fell from 46.0% (2008-2010) to 35.4% "
      "(2020-2022) without reaching significance (omnibus P = .48)."]),

    ("Exploratory infection-type contrast",
     ["Within the source-specific tier, no growth was higher in native osteomyelitis (61.7%; "
      "53.9-69.6) than in prosthetic joint infection (43.4%; 39.1-48.1), and the contrast "
      "persisted in patient-clustered models with prosthetic joint infection as the reference: "
      "odds ratio 2.05 (1.38-3.05) adjusted for age band, sex, race group and insurance category "
      "(Benjamini-Hochberg adjusted P = .004), and 1.96 (1.33-2.90) with further adjustment for "
      "the number of specimens obtained (adjusted P = .009). No sociodemographic coefficient "
      "remained statistically significant after correction, including sex (odds ratio for male "
      "sex, 0.80; 0.58-1.12; P = .19). Complete coefficients, reference categories, denominators, "
      "event counts, and raw and adjusted P values are given in Online Resource 1, eTable 10.",
      "Only 167 osteomyelitis episodes contributed a source-specific specimen."]),
]

DISCUSSION = [
    "In a database study of code-defined bone and joint infection, the quantities most often "
    "reported differed substantially according to which specimen labels were admitted. No growth "
    "was 48.0% among specimens whose label names a musculoskeletal source and 34.0% among generic "
    "tissue, biopsy and foreign-body labels; the polymicrobial fraction was 10.9% against 42.1%. A "
    "reader given only a pooled figure would not know either number existed.",

    "The obvious inference is that the labels themselves behave differently, and the data do not "
    "establish it. Restricting to the 487 episodes that supplied both kinds of specimen holds the "
    "patient and admission fixed. There the source-specific tier was entirely negative more often "
    "than the generic tier, in the same direction as the between-cohort comparison; but that "
    "episode-level contrast is confounded by how much each tier contributes, since a tier "
    "represented by one specimen is more easily entirely negative than one represented by three, "
    "and the median episode supplied one source-specific and three generic specimens. The two "
    "analyses that remove that dependence, an episode-stratified conditional logistic model and a "
    "one-to-one matched subset, did not detect a significant association (odds ratio 0.86, 95% CI "
    "0.64-1.15 with patient-clustered uncertainty; and 25 versus 14 discordant episodes, "
    "P = .11). Within an episode we therefore cannot demonstrate that a source-specific label "
    "yields a different per-specimen result from a generic one, though neither can we exclude it: "
    "the conditional estimate rests on 252 informative episodes and its interval still admits "
    "effects of clinically relevant size.",

    "What remains is a statement about measurement rather than mechanism. The estimates a database "
    "study reports depend substantially on which specimen labels it analyses, and we can quantify "
    "that dependence; we cannot, with these data, decompose it into an effect of the specimen and "
    "an effect of who was sampled. A pooled culture estimate is best read as a weighted average "
    "over label-defined subpopulations differing in case mix and sampling intensity, with the "
    "weights set by the habits of the source institution rather than by anything about the "
    "infections. Two further conventions had effects of similar size and are almost never stated. "
    "Scoping the "
    "first-isolate rule across all cultures rather than within the analytic set discarded 43% of "
    "the source-specific episode-first isolates, because the same organism had already been "
    "recovered from blood, urine or a swab; the resulting quantity is not the first isolate among "
    "the specimens being analysed, though it would be reported as such. Treating an explicit "
    "report of mixed bacterial flora as monomicrobial, which any speciated-only rule does "
    "silently, understated the pooled polymicrobial fraction by nearly nine percentage points.",

    "We would therefore suggest that database-derived culture estimates report four things usually "
    "omitted: the label set admitted and the counts it yields, the scope within which first "
    "isolates are defined, the handling of growth that was never speciated, and an accounting of "
    "which tests entered the negative denominator. Where such a study compares label-defined "
    "subgroups, a within-episode comparison should be preferred, and the episode-level outcome "
    "should not vary with how many specimens a tier happens to contribute. Applying all of this "
    "costs precision and removes several conclusions the pooled analysis would have supported.",

    "Comparison with published culture-negative fractions requires care. Published fractions are "
    "usually computed among cases meeting a formal infection definition, such as the 2018 "
    "International Consensus Meeting criteria [8] or the European Bone and Joint Infection Society "
    "criteria [9]. Neither is constructible here, because MIMIC-IV records no sinus-tract status, "
    "intraoperative histology or synovial biomarkers, which is why the cohort is framed as "
    "code-defined. The gap between the estimands is large: in a single-institution series, "
    "suspected culture-negative prosthetic joint infection affected 22.0% of cases against 6.4% "
    "under Musculoskeletal Infection Society criteria [10]. The quantity reported here is a "
    "specimen-level no-growth fraction in a code-defined cohort and is neither of those, so the 5% "
    "to 42% range in the literature [2,4] is context, not a comparator. Prior antimicrobial "
    "exposure and fastidious organisms are recognised contributors to culture negativity [4,11,12], "
    "and the timing of the first antimicrobial dose relative to sampling is the single most "
    "informative field these data lack; we make no claim about it.",

    "Three of the reported quantities need reading with care. The Cutibacterium fraction is a lower "
    "bound rather than an estimate, because recovery depends on incubation length and these data do "
    "not record it [7]. No vancomycin resistance was observed, which does not establish zero "
    "population risk; the upper bound on the contributing patients is the interpretable quantity. "
    "And the osteomyelitis-versus-prosthetic-joint-infection contrast is exploratory: only 167 "
    "osteomyelitis episodes contributed a source-specific specimen, no bone-specific label exists "
    "in this database, and joint fluid obtained during an osteomyelitis-coded admission need not "
    "come from the infected bone.",

    "This study has clear limitations, several of which are the object of study rather than "
    "incidental to it. The most important is that we address specimen-category specificity without "
    "resolving infection attribution. Even a source-specific label does not establish that the "
    "specimen came from the bone, joint, side or prosthesis carrying the diagnosis code, because "
    "MIMIC-IV records no laterality and no link between a specimen and an operation. The estimates "
    "describe deep musculoskeletal specimens obtained during an orthopaedic-infection admission, "
    "not a validated microbiological sample of the coded infection; this applies with particular "
    "force to the osteomyelitis subgroup, where no bone-specific label exists, which is why that "
    "contrast is exploratory. The within-episode analyses hold the patient and admission fixed but "
    "not the indication, and are restricted to 487 predominantly prosthetic-joint episodes. They "
    "are also modest in power: the conditional model discards episodes whose specimens shared the "
    "same result, and the matched subset contains 75 episodes, so a per-specimen difference of the "
    "size seen between cohorts cannot be excluded. Episodes are correlated within patients, which "
    "is why paired inference is patient-clustered. The findings come from one institution and one "
    "labelling system; external replication in a database with a different specimen vocabulary is "
    "the necessary next step. The cohort is code-defined, and codes are imperfect markers of true "
    "infection. The database records the reported result but not the pre-analytical conditions "
    "determining it: media, incubation atmosphere and duration, blood culture bottle use and "
    "sonication protocol are unrecorded, so the Cutibacterium fraction is a lower bound. "
    "Culture-independent diagnostics are not captured, so molecularly positive specimens count as "
    "no growth. Susceptibility results are categorical interpretations without minimum inhibitory "
    "concentrations, measured only among isolates the laboratory chose to test, which may "
    "overestimate resistance where testing followed treatment failure. Only in-hospital records "
    "are captured, excluding outpatient antibiotics.",

    "In re-runnable data, the culture-based description of code-defined bone and joint infection is "
    "not a single set of numbers but a family of them, indexed by decisions about which specimen "
    "labels are admitted, how isolates are deduplicated and how unspeciated growth is counted. "
    "Those decisions moved the headline quantities materially, "
    "and within-episode analyses do not show that the label itself "
    "produces the difference. We report the family rather than one member of it, and provide the "
    "code and dictionaries so others can substitute their own rules and see what changes.",
]

REFERENCES = [
    "Lew DP, Waldvogel FA (2004) Osteomyelitis. Lancet 364:369-379. "
    "https://doi.org/10.1016/S0140-6736(04)16727-5",
    "Tande AJ, Patel R (2014) Prosthetic joint infection. Clin Microbiol Rev 27:302-345. "
    "https://doi.org/10.1128/CMR.00111-13",
    "Zimmerli W, Trampuz A, Ochsner PE (2004) Prosthetic-joint infections. N Engl J Med "
    "351:1645-1654. https://doi.org/10.1056/NEJMra040181",
    "Berbari EF, Marculescu C, Sia I, Lahr BD, Hanssen AD, Steckelberg JM, Gullerud R, Osmon DR "
    "(2007) Culture-negative prosthetic joint infection. Clin Infect Dis 45:1113-1119. "
    "https://doi.org/10.1086/522184",
    "Johnson AEW, Bulgarelli L, Shen L et al (2023) MIMIC-IV, a freely accessible electronic "
    "health record dataset. Sci Data 10:1. https://doi.org/10.1038/s41597-022-01899-x",
    "Johnson A, Bulgarelli L, Pollard T et al (2024) MIMIC-IV (version 3.1). PhysioNet. "
    "https://doi.org/10.13026/kpb9-mt58",
    "Butler-Wu SM, Burns EM, Pottinger PS, Magaret AS, Rakeman JL, Matsen FA, Cookson BT (2011) "
    "Optimization of periprosthetic culture for diagnosis of Propionibacterium acnes prosthetic "
    "joint infection. J Clin Microbiol 49:2490-2495. https://doi.org/10.1128/JCM.00450-11",
    "Parvizi J, Tan TL, Goswami K et al (2018) The 2018 definition of periprosthetic hip and knee "
    "infection: an evidence-based and validated criteria. J Arthroplasty 33:1309-1314.e2. "
    "https://doi.org/10.1016/j.arth.2018.02.078",
    "McNally M, Sousa R, Wouthuyzen-Bakker M et al (2021) The EBJIS definition of periprosthetic "
    "joint infection. Bone Joint J 103-B:18-25. "
    "https://doi.org/10.1302/0301-620X.103B1.BJJ-2020-1381.R1",
    "Tan TL, Kheir MM, Shohat N et al (2018) Culture-negative periprosthetic joint infection: an "
    "update on what to expect. JB JS Open Access 3:e0060. "
    "https://doi.org/10.2106/JBJS.OA.17.00060",
    "Osmon DR, Berbari EF, Berendt AR et al (2013) Diagnosis and management of prosthetic joint "
    "infection: clinical practice guidelines by the Infectious Diseases Society of America. Clin "
    "Infect Dis 56:e1-e25. https://doi.org/10.1093/cid/cis803",
    "Malekzadeh D, Osmon DR, Lahr BD, Hanssen AD, Berbari EF (2010) Prior use of antimicrobial "
    "therapy is a risk factor for culture-negative prosthetic joint infection. Clin Orthop Relat "
    "Res 468:2039-2045. https://doi.org/10.1007/s11999-010-1338-0",
    "Peel TN, Dylla BL, Hughes JG, Lynch DT, Greenwood-Quaintance KE, Cheng AC, Mandrekar JN, "
    "Patel R (2016) Improved diagnosis of prosthetic joint infection by culturing periprosthetic "
    "tissue specimens in blood culture bottles. mBio 7:e01776-15. "
    "https://doi.org/10.1128/mBio.01776-15",
    "Trampuz A, Piper KE, Jacobson MJ et al (2007) Sonication of removed hip and knee prostheses "
    "for diagnosis of infection. N Engl J Med 357:654-663. "
    "https://doi.org/10.1056/NEJMoa061588",
    "Atkins BL, Athanasou N, Deeks JJ, Crook DW, Simpson H, Peto TE, McLardy-Smith P, Berendt AR "
    "(1998) Prospective evaluation of criteria for microbiological diagnosis of prosthetic-joint "
    "infection at revision arthroplasty. J Clin Microbiol 36:2932-2939. "
    "https://doi.org/10.1128/jcm.36.10.2932-2939.1998",
    "Clinical and Laboratory Standards Institute (2022) Analysis and presentation of cumulative "
    "antimicrobial susceptibility test data, 5th edn. CLSI guideline M39. Clinical and Laboratory "
    "Standards Institute, Wayne, PA",
]

FIGURE_LEGENDS = [
    ("Fig. 1", "No growth in deep musculoskeletal specimens. a Percentage of evaluable specimens "
     "with no growth by specimen label tier; the pooled estimate tracks the generic tier because "
     "generic specimens outnumber source-specific ones almost eightfold. b No growth by specimen "
     "source within the source-specific tier. c No growth by the number of evaluable "
     "source-specific specimens obtained per episode; the highest stratum contains 10 specimens "
     "and is drawn as an unconnected open marker because its patient-clustered interval is not "
     "estimable, and the connecting line is not intended to imply a dose-response relationship. "
     "d Episode-level comparison restricted to the 487 episodes that contributed both tiers, so "
     "that the patient and admission are held fixed; a tier counts as negative for an episode "
     "only when every one of its evaluable specimens grew nothing. The difference runs in the "
     "same direction as a, but is confounded by specimen count (median 1 source-specific versus 3 "
     "generic specimens per episode); the paired difference is 9.0 percentage points (95% CI, "
     "4.1-13.8), and an episode-stratified per-specimen model does not detect an association with "
     "the label. Error bars are patient-clustered bootstrap 95% confidence intervals; numerals are "
     "specimen counts in a to c and episode counts in d"),
    ("Fig. 2", "Organism spectrum of source-specific deep musculoskeletal isolates under three "
     "deduplication rules, all scoped within the source-specific tier. The eight most frequent "
     "organism groups under the episode-first rule are shown. Counting every recovery rather than "
     "first isolates raises the apparent share of Staphylococcus aureus by approximately three "
     "percentage points"),
    ("Fig. 3", "Antimicrobial resistance among deep musculoskeletal isolates. a Staphylococcus "
     "aureus panel and b gram-negative panel, first isolate per episode, pooled tier; numerals "
     "give the number of isolates tested for each agent. c Oxacillin resistance by anchor-year "
     "group. TMP-SMX trimethoprim-sulfamethoxazole. Error bars are patient-clustered bootstrap "
     "95% confidence intervals"),
]

DECLARATIONS = [
    ("Funding", "The authors did not receive support from any organization for the submitted "
     "work."),
    ("Competing interests", "The authors have no relevant financial or non-financial interests to "
     "disclose."),
    ("Ethics approval", "This study was performed in line with the principles of the Declaration "
     "of Helsinki. It is a secondary analysis of an existing, fully de-identified, publicly "
     "credentialed-access database (MIMIC-IV version 3.1). The collection and sharing of MIMIC-IV were "
     "approved by the institutional review board of the Beth Israel Deaconess Medical Center, "
     "which granted a waiver of informed consent for that resource. That approval covers the "
     "source database rather than this particular analysis; no study-specific ethical review was "
     "sought or required for secondary use of the de-identified database under its data use "
     "agreement."),
    ("Consent to participate", "Not applicable. The study used a de-identified, credentialed-access database "
     "for which a waiver of informed consent was granted; no individual participants were "
     "recruited or contacted."),
    ("Consent to publish", "Not applicable. The manuscript contains no data, images or details "
     "relating to an identifiable individual."),
    ("Data availability", "MIMIC-IV version 3.1 is available to credentialed users under a data "
     "use agreement from PhysioNet (https://doi.org/10.13026/kpb9-mt58). All analysis code, "
     "dictionaries required to reproduce the reported analyses are publicly archived (https://doi.org/10.5281/zenodo.21268251)."),
    ("Code availability", "See Data availability."),
]

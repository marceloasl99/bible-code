# Conclusion and Detailed Interpretation

## Executive finding

For the selected Torah edition, nine exploratory Hebrew terms, bidirectional ELS search through absolute skip 1,000, and three tested null models, **no term showed an adjusted empirical p-value below 0.05**. The observed counts were generally close to the null-model means. This run does not provide evidence of predictive ability or an intentionally encoded historical message.

This is a bounded conclusion about this corpus and protocol. It is not a mathematical proof that every conceivable ELS hypothesis is impossible, and it is not a prospective prediction test.

## Analysis performed

- Corpus: “Tanach with Text Only,” 305,172 normalized Hebrew letters, with final forms preserved.
- Corpus SHA-256: `25ec653a8ace4263331f85048e5a3bf08487119f7d9cf6684e345eea7a149270`.
- Search: nine terms, both directions, skips through 1,000, no wrap-around.
- Controls: 100 IID permutations, 100 block permutations (block length 20), and 100 first-order Markov replicas.
- Random seed base: `20261025`; 12 logical processors; CPU multiprocessing. CUDA was not used.
- Runtime reported by the script: 10,653.3 seconds, about 2 hours 58 minutes.
- Main report: [`../results/final/analysis_20261025_100perm_en.json`](../results/final/analysis_20261025_100perm_en.json).

Each simulated corpus was searched for all nine terms. For each term and model, the empirical upper-tail p-value is `(number of null counts >= observed + 1) / 101`. It tests for an excess count, not a two-sided difference or equivalence. The minimum possible raw p-value with 100 replicas is 1/101 ≈ 0.0099. Bonferroni and Benjamini–Hochberg adjustments were calculated over the nine declared terms separately within each model.

## Results

| Hebrew term | Observed | IID expected | IID mean (p) | Block mean (p) | Markov mean (p) | Largest BH q across models |
|---|---:|---:|---:|---:|---:|---:|
| רבין (Rabin) | 2,712 | 2,798.7 | 2,803.3 (0.9307) | 2,813.3 (0.9604) | 2,794.8 (0.8911) | 1.0000 |
| קנדי (Kennedy) | 768 | 724.1 | 729.0 (0.0990) | 726.4 (0.0495) | 722.4 (0.0693) | 0.6238 |
| סאדאת (Sadat) | 40 | 39.0 | 39.6 (0.5050) | 38.5 (0.4455) | 39.6 (0.4752) | 0.9802 |
| היטלר (Hitler) | 150 | 143.8 | 146.3 (0.3861) | 145.2 (0.3267) | 144.2 (0.3366) | 0.9802 |
| שואה (Holocaust) | 25,148 | 25,417.3 | 25,439.4 (0.9703) | 25,405.2 (0.9604) | 25,394.1 (0.8119) | 1.0000 |
| תאומים (Twins) | 60 | 54.2 | 54.4 (0.2079) | 54.9 (0.2673) | 54.0 (0.3069) | 0.9802 |
| מטוס (Aircraft) | 88 | 102.8 | 103.0 (0.9703) | 106.2 (0.9703) | 105.0 (0.9703) | 1.0000 |
| אש (Fire) | 2,714,810 | 2,763,811.7 | 2,763,943.6 (1.0000) | 2,763,987.2 (1.0000) | 2,764,429.9 (1.0000) | 1.0000 |
| נפל (Fell) | 18,606 | 18,164.5 | 18,152.3 (0.0099) | 18,608.0 (0.5446) | 18,290.9 (0.2079) | 0.9802 |

### The two smallest raw p-values

- **נפל under IID:** none of the 100 IID replicas reached the observed count, producing the minimum raw p-value, 0.0099. The nine-term adjusted value is 0.0891. Under block permutation, the observed count is nearly identical to the null mean (18,608) and p = 0.5446; under Markov, p = 0.2079. The apparent IID result is therefore model-sensitive and does not survive the declared adjustment.
- **קנדי under block permutation:** raw p = 0.0495, but the adjusted value is 0.4455. This is not significant after testing the nine terms.

The table's “largest BH q” is deliberately conservative as a compact summary: it shows the maximum adjusted q for that term across the three models. The full JSON provides each model's own Bonferroni and BH values.

## What the four proposed arguments establish

### 1. Empirical null controls

The controls show that counts of this magnitude are common under these particular randomization schemes, and no excess remains statistically significant after the declared adjustment. It is accurate to say **this analysis found no adjusted significant excess**.

“Statistically indistinguishable” is stronger than what was tested. The p-values are one-sided tests for counts at least as high as observed. The analysis did not run a two-sided equivalence test, so failure to detect an excess does not prove that observed and null distributions are identical. The three null models preserve different properties and none is a perfect model of Hebrew language or textual history.

### 2. Prediction and retrospective selection

The targets are explicitly exploratory examples selected with knowledge of historical events. This run is not a test of prediction. A prospective test would need to register, before the event, every prediction, spelling variant, time window, search rule, scoring criterion, and treatment of ambiguous outcomes, and then score failures as well as successes.

Searching many words, spellings, skip values, directions, and contexts allows retrospective selection. This is a strong reason to require preregistration and an untouched confirmation set. However, the claim that blind searches produce “millions of contradictory combinations” was not directly measured here: the report does not enumerate semantic statements or contradictory predictions. Present it as a concern about researcher flexibility, not as a count produced by this project.

### 3. Combinatorial search space and short words

For a 305,172-letter corpus, both directions, and skips through 1,000, the search engine counts the following valid position/signed-skip pairs for each fixed target length:

| Target length | Valid position/signed-skip pairs |
|---:|---:|
| 2 letters | 609,343,000 |
| 3 letters | 608,342,000 |
| 4 letters | 607,341,000 |

This is roughly 607–609 million candidate pairs per target before adding alternate spellings, terms, or interpretive choices. A large search space makes hits unsurprising, but the raw space alone does not determine significance; the expected count and an appropriate null comparison matter.

It is not correct to say that 2–4-letter words are guaranteed to occur in every sufficiently long Hebrew text. For the terms tested here, the IID/Poisson approximation estimates at least one occurrence with probability essentially one in this corpus because expected counts are large. That is a model-based estimate for these terms and this text, not a guarantee about every word or text. For example, the IID expected counts were 54.2 for תאומים and 2,798.7 for רבין; the observed counts are then compared with empirical controls rather than interpreted as meaningful merely because they exist.

No result files for *Moby-Dick* or *War and Peace* are included in this repository. The README has a sample command for a Moby-Dick corpus, but that is not evidence that either book was analyzed. Comparable controls would require obtaining and documenting those corpora, matching normalization and protocol, and accounting for language, alphabet, and corpus size.

### 4. Entropy and information-theoretic claims

The report estimates marginal entropy `H0 = 4.245` bits per symbol and third-order conditional entropy `H3 = 2.633` bits per symbol. Multiplying `H3` by 305,172 symbols and dividing by eight gives about 100,428 bytes; using `H0` gives about 161,927 bytes. These are model-based estimates, not measured compressed file sizes or universal bounds on all information that could be encoded in the text. `H3` only models short contexts and does not capture every regularity, external key, editorial structure, or possible coding scheme.

Thus, the statement that it is mathematically impossible for roughly 90 KB to refer to historical events does not follow from this analysis. A short sequence can be associated with large amounts of information when an interpreter already knows a key or event; that association does not demonstrate intent or predictive power. A testable claim would specify a decoding rule in advance and ask whether its prospective results outperform suitable controls. This run found no such evidence, but it did not prove impossibility for every conceivable ELS scheme.

## Research guidelines

For a confirmatory study, specify and timestamp the following before searching:

1. Corpus edition, provenance, license, raw and normalized SHA-256, and exact normalization.
2. Every target and spelling variant, with inclusion/exclusion rules fixed in advance.
3. Search directions, skip range, boundaries, and primary statistic.
4. Full family of tested terms, variants, events, and secondary analyses.
5. Null models and the linguistic/text properties each preserves.
6. Number of replicas, seeds, uncertainty reporting, and family-wise or false-discovery adjustment.
7. A fixed success criterion and an independent confirmation set or prospective evaluation.

Report all searches, including negative results. Do not select a model, corpus, spelling, or statistic because it gives the most favorable result and then report it as if it had been specified in advance.

## Proportionate conclusion

**This exploratory run does not show a statistically adjusted excess for any of its nine terms and provides no evidence of predictive ability.** The counts are compatible with the three tested controls. The raw IID result for נפל does not survive adjustment and is not reproduced by the block or Markov controls. These findings do not support retrospective claims of a predictive historical code; they also are not a mathematical proof about every imaginable ELS hypothesis.

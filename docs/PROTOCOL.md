# Method and Research Protocol

## Search definition

The engine searches a normalized one-dimensional symbol stream for a target whose letters occur at equal signed offsets. For a target of length `k >= 2`, each candidate is defined by a start index and a signed skip. The search does not wrap around at the end of the corpus. `both` searches positive and negative skips; `forward` and `backward` restrict the sign. The maximum absolute skip is an explicit parameter.

For this project the primary corpus is normalized by Unicode NFD, removing combining marks, retaining Hebrew letters Alef through Tav (including final forms), and discarding other characters. Verse and chapter boundaries are not represented in the normalized search stream. Consequently, a sequence can cross a verse boundary. This convention is part of the hypothesis and must be kept consistent in comparisons.

## Control models

| Model | Preserves | Disrupts / caveat |
|---|---|---|
| `iid_perm` | Exact marginal symbol counts | Destroys symbol order and local language structure |
| `block_perm` | Order within blocks of the selected size | Reorders blocks and changes block boundaries; conclusions depend on block size |
| `markov` | Approximate first-order adjacent-symbol transition frequencies | Does not preserve words, syntax, long-range dependence, or the full text composition |

The models are complementary sensitivity checks, not interchangeable or definitive representations of Hebrew. Report each separately. A p-value is conditional on its null model.

## Empirical p-values and multiplicity

For each target and model, the program calculates the upper-tail empirical p-value

```text
(1 + number of simulated counts >= observed count) / (1 + number of replicas)
```

This tests for an unusually large count. It is not a two-sided test, an equivalence test, or a test of semantic meaning. With `B` replicas, the minimum raw p-value is `1/(B+1)`. The primary run has 100 replicas per model, so the resolution is about 0.0099.

The program reports Bonferroni-adjusted p-values and Benjamini–Hochberg q-values within the target family for each model. The analyst must define the full family before searching. These adjustments do not account for unrecorded choices of targets, spellings, translations, skip ranges, directions, layouts, corpora, or interpretations.

## Reproducible confirmatory workflow

Before the search, archive a protocol with:

1. A named corpus edition and source, license, raw file hash, normalized file hash, and normalization rules.
2. The complete list of terms and variants, including rules for final forms, spelling, and synonyms.
3. The allowed direction, skip range, boundary handling, and primary score.
4. The complete multiple-testing family and all planned secondary analyses.
5. Null models, what each preserves, replica count, random seed(s), and adjustment method.
6. The date, version-control commit, and a success criterion stated before results are viewed.

Run the protocol as written. Publish all targets and outcomes, including null and ambiguous cases. If exploration informs a revised protocol, label that result exploratory and confirm the revised protocol on an independent, untouched corpus or prospectively after registration.

## Claims and scope

An occurrence establishes only that a literal sequence exists under the specified normalization and search bounds. A high count by itself does not establish significance, intentional encoding, historical foreknowledge, or prediction. A null result does not prove the impossibility of every imaginable ELS scheme. Conclusions should match the exact tests performed.

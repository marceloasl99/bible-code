# Preliminary 10-replicate pilot

This report is retained for the project history. It is **superseded** by the 100-replicate analysis in [`../final/analysis_20261025_100perm_en.json`](../final/analysis_20261025_100perm_en.json). With only 10 replicas, the minimum raw empirical p-value was 1/11 (about 0.091), so the pilot could not resolve p-values below 0.05.

The pilot used the same nine exploratory terms, bidirectional search through skip 1,000, and three null models. It used 10 replicas per model and block size 20. Do not treat its p-values as confirmatory.

| Term | Hits | IID p | Block p | Markov p |
|---|---:|---:|---:|---:|
| רבין (רבין) | 2,712 | 0.909 | 1.000 | 0.909 |
| קנדי (קנדי) | 768 | 0.091 | 0.091 | 0.182 |
| סאדאת (סאדאת) | 40 | 0.455 | 0.636 | 0.545 |
| היטלר (היטלר) | 150 | 0.545 | 0.273 | 0.455 |
| שואה (שואה) | 25,148 | 1.000 | 1.000 | 0.727 |
| תאומים (תאומים) | 60 | 0.545 | 0.182 | 0.182 |
| מטוס (מטוס) | 88 | 1.000 | 0.818 | 0.909 |
| אש (אש) | 2,714,810 | 1.000 | 1.000 | 1.000 |
| נפל (נפל) | 18,606 | 0.091 | 0.364 | 0.273 |

The later 100-replica run should be used for the main interpretation. Pilot data are preserved in [`analysis_20261025_10rep_en.json`](analysis_20261025_10rep_en.json).

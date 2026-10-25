# Bible Code (ELS) — Local Corpus and Statistical Analysis

This repository contains a reproducible, offline-capable tool for searching Hebrew text for **equidistant letter sequences (ELS)** and comparing observed counts with explicitly defined randomized controls. It includes a locally stored Torah corpus, source files and hashes, the search implementation, example targets, and the completed analysis report.

> **Main finding:** In the exploratory run documented here, none of the nine tested terms showed a statistically significant excess after adjustment for the nine terms. The run does not provide evidence of predictive ability or an intentionally encoded historical message. It also does not prove a mathematical impossibility for every conceivable ELS hypothesis.

Read the detailed [conclusion and interpretation](docs/CONCLUSION.md) before using the result to support a claim.

## Repository contents

```text
.
├── data/
│   ├── source/sefaria/       # Original static JSON source files
│   ├── torah_hebrew.txt     # Concatenated Hebrew text with verse separators
│   ├── torah_els.txt        # Normalized search corpus; final forms preserved
│   ├── torah_els_merged_finals.txt
│   └── torah_manifest.json  # Source, edition, license, counts, normalization, hashes
├── docs/
│   ├── CONCLUSION.md        # Findings, interpretation, limitations
│   └── PROTOCOL.md          # Method, controls, and research guidelines
├── results/
│   ├── final/               # Main completed 100-replicate-per-model report
│   ├── preliminary/         # Earlier 10-replicate pilot report
│   └── validation/          # Small offline smoke-run output
├── scripts/download_torah.py
├── src/                     # Corpus normalization, ELS search, statistics
├── tests/                   # Unit tests
├── menu.py                  # Interactive local menu
├── run_analysis.py          # Command-line analysis runner
├── targets.json             # Exploratory Hebrew example terms
└── targets_latin.json       # Latin example targets
```

The main machine-readable result is [`results/final/analysis_20261025_100perm_en.json`](results/final/analysis_20261025_100perm_en.json). It preserves the numerical output and parameters of the completed run; descriptive metadata and notes are presented in English. The original output is retained locally as `analysis_20261025_100perm_source.json` and is excluded from the GitHub publication because its explanatory text is Portuguese.

## Quick start

Requirements: Python 3.10 or later. The analysis code uses the Python standard library; no API key, network connection, or third-party Python package is needed to search the bundled corpus.

In PowerShell:

```powershell
cd C:\008-BibleCode
python menu.py
```

Choose the local analysis option to search the bundled corpus interactively. To run a smaller command-line analysis:

```powershell
python run_analysis.py `
  --corpus .\data\torah_els.txt `
  --targets .\targets.json `
  --alphabet hebrew `
  --max-skip 100 `
  --direction both `
  --workers 0 `
  --progress `
  --out .\results\analysis.json
```

`--workers 0` uses all detected logical processors. Use a modest `--max-skip` for a first run; larger limits greatly increase the search space and runtime.

To reproduce the full completed analysis, run:

```powershell
python run_analysis.py `
  --corpus .\data\torah_els.txt `
  --targets .\targets.json `
  --alphabet hebrew `
  --max-skip 1000 `
  --direction both `
  --workers 0 `
  --max-locations 100 `
  --out .\results\reproduced_100rep.json `
  --progress `
  --permutations 100 `
  --null-models iid_perm,block_perm,markov `
  --block-size 20 `
  --seed 20261025
```

This run took **10,653.3 seconds (about 2 hours 58 minutes)** on the recorded 12-logical-processor machine. Runtime depends on hardware and system load. It used CPU multiprocessing; the RTX 4060 discussed during development was on a different computer and was not used for this result. The current search engine has no CUDA implementation.

## Corpus provenance

The bundled data comes from the static JSON exports in [Sefaria-Export](https://github.com/Sefaria/Sefaria-Export), downloaded from its public Google Cloud Storage files rather than from an API endpoint. The selected version is **Tanach with Text Only**, whose source metadata identifies `http://www.tanach.us/Tanach.xml` and marks the text as **Public Domain**. See [`data/torah_manifest.json`](data/torah_manifest.json) for per-file source URLs and SHA-256 hashes.

The normalized search corpus contains **305,172 Hebrew letters**, 27 distinct symbols, 187 chapters, and 5,846 verse segments in the source assembly. It differs from some commonly cited counts, including 304,805 letters and 5,845 verses. This project preserves the downloaded edition and records the difference rather than editing the text to match a published count. Edition and segmentation differences must be investigated before comparing results with another study.

Normalization applies Unicode NFD, removes combining marks, retains Hebrew letters Alef through Tav including final forms, and removes other characters. Verse separators are therefore absent from the ELS search stream. The alternative `torah_els_merged_finals.txt` maps final forms to their common forms and is for sensitivity analysis; do not mix its output with the primary corpus without recording the choice.

`python scripts/download_torah.py` can retrieve and validate the source files again. This download step requires network access. All analysis commands that use the bundled files run locally and do not call an API.

## Completed analysis: headline results

The primary run searched nine exploratory Hebrew terms in both directions with absolute skip values through 1,000. It compared the observed counts with 100 simulated corpora for each of three null models. Each simulated corpus was searched for all nine terms.

| Term | Observed hits | IID expected | IID p | Block p | Markov p | Largest BH q across models |
|---|---:|---:|---:|---:|---:|---:|
| רבין (Rabin) | 2,712 | 2,798.7 | 0.9307 | 0.9604 | 0.8911 | 1.0000 |
| קנדי (Kennedy) | 768 | 724.1 | 0.0990 | 0.0495 | 0.0693 | 0.6238 |
| סאדאת (Sadat) | 40 | 39.0 | 0.5050 | 0.4455 | 0.4752 | 0.9802 |
| היטלר (Hitler) | 150 | 143.8 | 0.3861 | 0.3267 | 0.3366 | 0.9802 |
| שואה (Holocaust) | 25,148 | 25,417.3 | 0.9703 | 0.9604 | 0.8119 | 1.0000 |
| תאומים (Twins) | 60 | 54.2 | 0.2079 | 0.2673 | 0.3069 | 0.9802 |
| מטוס (Aircraft) | 88 | 102.8 | 0.9703 | 0.9703 | 0.9703 | 1.0000 |
| אש (Fire) | 2,714,810 | 2,763,811.7 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| נפל (Fell) | 18,606 | 18,164.5 | 0.0099 | 0.5446 | 0.2079 | 0.9802 |

P-values are one-sided empirical estimates for an **excess** at least as large as the observed count. They use the plus-one correction: `(number of null counts >= observed + 1) / 101`. With 100 replicates, the smallest possible raw empirical p-value is 1/101 ≈ 0.0099. Bonferroni and Benjamini–Hochberg adjustments were computed within the family of nine terms for each model.

The IID result for נפל exceeded all 100 IID replicates, giving raw p = 0.0099, but its adjusted p/q is 0.0891 and its observed count is almost identical to the block-control mean (18,608). The block p is 0.5446 and Markov p is 0.2079. It is therefore a model-sensitive exploratory observation, not a robust result. קנדי has a block-control raw p of 0.0495, but its adjusted value is 0.4455. **No term remains below 0.05 after the declared adjustment.**

The IID expected count is a model-based reference, not an empirical p-value. The Poisson approximation that reports the probability of at least one hit is near 1 for these terms because the searched space is large; that does not mean the hits are significant or meaningful.

See [the full conclusion](docs/CONCLUSION.md) for the per-model means, adjustments, caveats, and a detailed assessment of claims that these results can and cannot support.

## Statistical controls and research guidelines

- **IID permutation (`iid_perm`)** shuffles all letters and preserves marginal letter counts while destroying sequence order.
- **Block permutation (`block_perm`)** shuffles contiguous blocks of 20 letters and preserves order within each block, but changes boundaries between blocks.
- **First-order Markov (`markov`)** generates letters using observed adjacent-letter transitions approximately; it does not preserve words, syntax, or the full Hebrew language structure.

These nulls answer different questions. None is a perfect model of the text. A sound analysis should state what each null preserves and avoid treating agreement across three imperfect models as proof about every possible model.

For future confirmatory work, preregister the corpus edition and hash, normalization, exact terms and spelling variants, directions, maximum skip, primary statistic, full test family, null models, number of replicates, random seed, and success criterion **before inspecting the results**. Include all terms and variants attempted, not only interesting hits. Use independent data or an untouched corpus for confirmation when possible. Label post hoc searches exploratory.

The family of nine terms adjusted in this report does not automatically account for unrecorded choices of names, spellings, skip limits, translations, event interpretations, or other analyses. No finite set of runs literally covers every possible search choice.

## Output fields

- `hits`: complete observed count for the declared search configuration.
- `locations_sample`: up to the configured number of zero-based start coordinates and signed skips; the count is complete even when locations are sampled.
- `iid_expected_hits`: expected count under a model with independent symbols and empirical marginal frequencies.
- `iid_poisson_approx_p_at_least_one`: Poisson approximation, not an empirically calibrated significance test.
- `empirical_p_plus_one`: one-sided null-tail estimate with plus-one correction.
- `bonferroni_p_within_model`: Bonferroni-adjusted p-value for the declared target family in one null model.
- `bh_q_within_model`: Benjamini–Hochberg adjusted q-value within that same declared family.
- `null_mean_hits`, `null_min_hits`, `null_max_hits`: simulated count summaries for each term/model.
- `H0`–`H3`: marginal and short-context conditional entropy estimates in bits per symbol; these are not estimates of Kolmogorov complexity or measured compressed file size.

## Development and validation

Run the unit tests from the project root:

```powershell
python -m unittest discover -s tests -v
```

The test suite covers normalization, ELS boundaries and directions, combinatorial counts, entropy, and deterministic resampling. These tests do not establish that a particular corpus edition or null hypothesis is scientifically appropriate.

The small offline smoke output is in [`results/validation/offline_smoke_skip2_en.json`](results/validation/offline_smoke_skip2_en.json). The 10-replicate pilot is retained under [`results/preliminary/`](results/preliminary/); its minimum p resolution was 1/11 (about 0.091), so it is superseded for inference by the completed 100-replicate run.

## Scope and limitations

This project is a local research and teaching tool. It reports literal ELS counts under specified settings and empirical comparisons against specified randomization schemes. It does not establish that ELS searches are universally useless or mathematically impossible, and this run does not test prospective predictions. Conversely, the observed hits do not establish an intentional code, historical message, causal mechanism, or predictive capability.

The exploratory terms were selected with knowledge of historical events. The search has a very large number of positions and skip choices, and the declared multiple-testing correction covers only the nine terms within each model. Claims about findings in *Moby-Dick* or *War and Peace* are not supported by result files in this repository; no comparable analysis of those books is included here.

## License and attribution

The bundled source-text manifest marks the selected Hebrew text as **Public Domain** and records its source metadata. This statement concerns the text edition and does **not** set a license for the Python code or other original project materials. No software license has been selected in this repository yet. Check the source project's current terms and add an explicit software license before redistribution if needed.

## Citation

When citing the result, include the corpus edition, SHA-256, normalization, target list, search parameters, null models, replicate count, seed, and a link to the exact JSON report. Do not cite only the headline conclusion without the protocol.

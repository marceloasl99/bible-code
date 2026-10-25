import random
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.corpus import load_corpus, normalize
from src.els import extract, find_els, sequence_space
from src.statistics import corrected_p, entropy_metrics, expected_hits_iid, resample


class CorpusTests(unittest.TestCase):
    def test_hebrew_diacritics_and_final_forms(self):
        sample = "בְּרֵאשִׁית ךםןףץ"
        self.assertEqual(normalize(sample), "בראשיתךםןףץ")
        self.assertEqual(normalize(sample, map_final_forms=True), "בראשיתכמנפצ")

    def test_latin_normalization(self):
        self.assertEqual(normalize("A-b c!", alphabet="latin"), "ABC")

    def test_sefaria_v3_selects_exact_version_and_keeps_metadata(self):
        payload = {"versions": [
            {"versionTitle": "Edition A", "versionSource": "https://example.test/a", "license": "test", "text": [["אָב"]]},
            {"versionTitle": "Edition B", "text": [["גד"]]},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v3.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            text, manifest = load_corpus(path, "hebrew", raw_json=True, version_title="Edition A")
            self.assertEqual(text, "אב")
            self.assertEqual(manifest["version_title"], "Edition A")
            with self.assertRaises(ValueError):
                load_corpus(path, "hebrew", raw_json=True)


class ElsTests(unittest.TestCase):
    def test_forward_and_backward(self):
        self.assertGreaterEqual(find_els("AXBXC", "ABC", 2, "forward").count, 1)
        self.assertGreaterEqual(find_els("C0B0A", "ABC", 2, "backward").count, 1)

    def test_extract_and_boundary(self):
        self.assertEqual(extract("A0B0C", 0, 2, 3), "ABC")
        self.assertEqual(find_els("A0B", "ABC", 5).count, 0)

    def test_search_space_matches_small_enumeration(self):
        self.assertEqual(sequence_space(5, 3, 2, "forward"), 4)
        self.assertEqual(sequence_space(5, 3, 2, "both"), 8)


class StatisticsTests(unittest.TestCase):
    def test_entropy_and_expected_hits(self):
        self.assertAlmostEqual(entropy_metrics("ABAB")["H0"], 1.0)
        self.assertAlmostEqual(entropy_metrics("ABAB")["H1"], 0.0)
        self.assertAlmostEqual(expected_hits_iid("ABAB", "A", 3), 2.0)

    def test_resampling_is_seeded_and_preserves_length(self):
        for mode in ("iid_perm", "block_perm", "markov"):
            self.assertEqual(resample("ABABAB", mode, random.Random(9)), resample("ABABAB", mode, random.Random(9)))
            self.assertEqual(len(resample("ABABAB", mode, random.Random(9))), 6)

    def test_bonferroni_helper(self):
        self.assertEqual(corrected_p(0.01, 100), 1.0)


class CliTests(unittest.TestCase):
    def test_cli_writes_auditable_json(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            (temp / "corpus.txt").write_text("א0ב0ג ג0ב0א", encoding="utf-8")
            (temp / "targets.json").write_text(json.dumps({"smoke": ["אבג"]}, ensure_ascii=False), encoding="utf-8")
            output = temp / "report.json"
            run = subprocess.run(
                [sys.executable, str(root / "run_analysis.py"), "--corpus", str(temp / "corpus.txt"),
                 "--targets", str(temp / "targets.json"), "--max-skip", "2", "--out", str(output)],
                cwd=root, capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["terms"][0]["hits"], 2)
            self.assertEqual(report["corpus"]["normalized_length"], 6)


if __name__ == "__main__":
    unittest.main()

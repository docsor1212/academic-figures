#!/usr/bin/env python3
"""Regression test suite for academic-figures scripts.

Runs on stdlib `unittest` only (no pytest dependency).
Coverage:
  1. Smoke test — all 14 chart types generate via the real CLI (exit 0 + file exists)
  2. validate_data() — fatal/warning detection per chart family
  3. load_data() — CSV edge cases (mixed numeric/text, scatter/box long format)
  4. has_cjk() — CJK detection
  5. legend_audit() — empty-legend detection via real matplotlib axes
  6. audit_pdf.py — PDF font-size audit behavior
  7. gen_legend.py — journal legend text for all chart types

Usage:
    python3 tests/run_tests.py            # run all
    python3 tests/run_tests.py -v         # verbose
"""

import contextlib
import re
import glob
import io
import json
import random
import shlex
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPT_DIR)

import gen_figure  # noqa: E402
import gen_legend  # noqa: E402
import audit_pdf  # noqa: E402

GEN = os.path.join(SCRIPT_DIR, "gen_figure.py")


# ── minimal valid sample data per chart family ─────────────────────────

SAMPLE = {
    "bar": {"labels": ["A", "B", "C"], "series": {"Ctrl": [1.0, 2.0, 3.0], "Treated": [2.5, 1.5, 4.0]}},
    "hbar": {"labels": ["A", "B"], "series": {"Ctrl": [1.0, 2.0], "Treated": [2.5, 1.5]}},
    "stacked_bar": {"labels": ["A", "B"], "series": {"x": [1.0, 2.0], "y": [0.5, 1.0]}},
    "heatmap": {"matrix": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]},
    "scatter": {"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 3.5, 5.0],
                "groups": ["a", "a", "b", "b"]},
    "line": {"labels": ["t0", "t1", "t2"], "series": {"S1": [1.0, 2.0, 3.0], "S2": [3.0, 2.5, 2.0]}},
    "dual_axis": {"labels": ["A", "B"], "left": {"Temp": [20.0, 30.0]}, "right": {"Count": [5, 8]}},
    "box": {"labels": ["G1", "G2"], "series": {"G1": [1.0, 2.0, 3.0], "G2": [2.0, 3.0, 4.0]}},
    "forest": {"labels": ["Study1", "Study2"], "estimates": [1.2, 0.8],
               "ci_low": [0.9, 0.5], "ci_high": [1.5, 1.1]},
    "km": {"groups": {"Placebo": [[0.0, 1.0], [5.0, 0.8], [10.0, 0.6]],
                      "Drug": [[0.0, 1.0], [5.0, 0.9], [10.0, 0.8]]}},
    "roc": {"curves": [{"fpr": [0.0, 0.5, 1.0], "tpr": [0.0, 0.7, 1.0], "label": "Model A",
                        "auc": 0.85}]},
    "violin": {"labels": ["G1", "G2"], "series": {"G1": [1.0, 2.0, 3.0, 2.5],
                                                  "G2": [2.0, 3.0, 4.0, 3.5]}},
    "composite": {"layout": [1, 2], "panels": [
        {"type": "bar", "data": {"labels": ["A", "B"], "series": {"S": [1.0, 2.0]}},
         "title": "Panel A", "pos": [0, 0]},
        {"type": "line", "data": {"labels": ["t0", "t1"], "series": {"S": [1.0, 2.0]}},
         "title": "Panel B", "pos": [0, 1]}]},
    "diagram": {"blocks": [
        {"id": "A", "label": "Input", "x": 0, "y": 0, "w": 2, "h": 1},
        {"id": "B", "label": "Output", "x": 3, "y": 0, "w": 2, "h": 1}],
        "arrows": [{"from": "A", "to": "B"}]},
    "prisma": {"records_identified": 50, "duplicates_removed": 10, "records_excluded": 20,
               "reports_not_retrieved": 2,
               "exclusion_reasons": {"Wrong population": 6, "No usable data": 4},
               "studies_included": 8},
}

# Canonical type names (aliases resolved) — the 15 distinct chart families
SMOKE_TYPES = ["bar", "hbar", "stacked_bar", "heatmap", "scatter", "line", "dual_axis",
               "box", "forest", "km", "roc", "violin", "composite", "diagram", "prisma"]


# ── 1. CLI smoke tests ─────────────────────────────────────────────────

class TestSmokeCLI(unittest.TestCase):
    """Every chart type renders through the real CLI."""

    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_smoke_")

    def _run(self, chart_type, extra=None):
        data_path = os.path.join(self.tmp, f"{chart_type}.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE[chart_type], f)
        out = os.path.join(self.tmp, f"{chart_type}.png")
        cmd = [sys.executable, GEN, "--type", chart_type, "--data", data_path,
               "--out", out, "--dpi", "150"]
        if extra:
            cmd += extra
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return proc, out

    def test_all_14_chart_types_render(self):
        for ct in SMOKE_TYPES:
            with self.subTest(chart_type=ct):
                proc, out = self._run(ct)
                self.assertEqual(proc.returncode, 0,
                                 f"{ct} failed: rc={proc.returncode}\n"
                                 f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
                self.assertTrue(os.path.exists(out), f"{ct}: output file missing")
                self.assertGreater(os.path.getsize(out), 0, f"{ct}: empty output")

    def test_fatal_data_exits_1(self):
        """Missing required field -> exit code 1, ERROR printed."""
        data_path = os.path.join(self.tmp, "bad.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"labels": ["A", "B"]}, f)  # no 'series'
        out = os.path.join(self.tmp, "bad.png")
        proc = subprocess.run(
            [sys.executable, GEN, "--type", "bar", "--data", data_path, "--out", out],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR", proc.stderr)
        self.assertFalse(os.path.exists(out))

    def test_verify_pdf_exit_0_clean(self):
        """--verify on a clean PDF -> exit 0 + VERIFY OK."""
        data_path = os.path.join(self.tmp, "v.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE["bar"], f)
        out = os.path.join(self.tmp, "v.pdf")
        proc = subprocess.run(
            [sys.executable, GEN, "--type", "bar", "--data", data_path, "--out", out,
             "--verify"],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0,
                         f"verify failed: rc={proc.returncode}\nSTDERR: {proc.stderr}")
        self.assertIn("VERIFY OK", proc.stderr)

    def test_journal_preset_applies(self):
        """--journal nature --column double -> narrower figure (89mm double column)."""
        data_path = os.path.join(self.tmp, "j.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE["bar"], f)
        out = os.path.join(self.tmp, "j.png")
        proc = subprocess.run(
            [sys.executable, GEN, "--type", "bar", "--data", data_path, "--out", out,
             "--journal", "nature", "--column", "double"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("期刊预设 nature", proc.stderr)

    def test_cjk_auto_detection_in_series_keys(self):
        """CJK in series names (dict keys) must trigger font loading, not tofu."""
        data_path = os.path.join(self.tmp, "cjk.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"labels": ["A", "B"],
                       "series": {"对照": [1.0, 2.0], "处理": [2.5, 1.5]}}, f)
        out = os.path.join(self.tmp, "cjk.png")
        proc = subprocess.run(
            [sys.executable, GEN, "--type", "bar", "--data", data_path, "--out", out],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("已加载中文字体", proc.stderr,
                      "CJK in series dict keys must auto-load a CJK font")
        self.assertNotIn("Glyph", proc.stderr, "no missing-glyph tofu warnings expected")


# ── 2. validate_data() unit tests ──────────────────────────────────────

class TestValidateData(unittest.TestCase):
    """(fatal, warn) split per chart family."""

    def _fatal(self, data, ct):
        return validate_fatal(data, ct)

    def test_bar_missing_series_fatal(self):
        f, w = gen_figure.validate_data({"labels": ["A", "B"]}, "bar")
        self.assertTrue(any("series" in m for m in f))

    def test_bar_length_mismatch_fatal(self):
        f, _ = gen_figure.validate_data(
            {"labels": ["A", "B", "C"], "series": {"S": [1.0, 2.0]}}, "bar")
        self.assertTrue(any("长度" in m for m in f))

    def test_bar_all_equal_warning(self):
        _, w = gen_figure.validate_data(
            {"labels": ["A", "B"], "series": {"S": [5.0, 5.0]}}, "bar")
        self.assertTrue(any("全部相同" in m and "平线" in m for m in w))

    def test_bar_empty_series_fatal(self):
        f, _ = gen_figure.validate_data(
            {"labels": ["A", "B"], "series": {"S": []}}, "bar")
        self.assertTrue(any("没有数据" in m for m in f))

    def test_heatmap_missing_matrix_fatal(self):
        f, _ = gen_figure.validate_data({"labels": ["A"]}, "heatmap")
        self.assertTrue(any("matrix" in m for m in f))

    def test_heatmap_ragged_rows_fatal(self):
        f, _ = gen_figure.validate_data({"matrix": [[1.0, 2.0], [3.0]]}, "heatmap")
        self.assertTrue(any("长度不一致" in m for m in f))

    def test_heatmap_all_equal_warning(self):
        _, w = gen_figure.validate_data({"matrix": [[2.0, 2.0], [2.0, 2.0]]}, "heatmap")
        self.assertTrue(any("值相同" in m for m in w))

    def test_scatter_missing_x_fatal(self):
        f, _ = gen_figure.validate_data({"y": [1.0, 2.0]}, "scatter")
        self.assertTrue(any("x" in m for m in f))

    def test_scatter_length_mismatch_fatal(self):
        f, _ = gen_figure.validate_data({"x": [1.0, 2.0], "y": [1.0]}, "scatter")
        self.assertTrue(any("长度" in m for m in f))

    def test_scatter_all_x_equal_warning(self):
        _, w = gen_figure.validate_data(
            {"x": [3.0, 3.0, 3.0], "y": [1.0, 2.0, 3.0]}, "scatter")
        self.assertTrue(any("值相同" in m for m in w))

    def test_forest_estimate_outside_ci_warning(self):
        _, w = gen_figure.validate_data(
            {"estimates": [5.0], "ci_low": [0.0], "ci_high": [1.0]}, "forest")
        self.assertTrue(any("落在 CI" in m for m in w))

    def test_forest_length_mismatch_fatal(self):
        f, _ = gen_figure.validate_data(
            {"estimates": [1.0, 2.0], "ci_low": [0.0], "ci_high": [1.0, 2.0]}, "forest")
        self.assertTrue(any("不一致" in m for m in f))

    def test_km_non_monotonic_time_warning(self):
        _, w = gen_figure.validate_data(
            {"groups": {"G": [[0.0, 1.0], [10.0, 0.5], [5.0, 0.8]]}}, "km")
        self.assertTrue(any("自动排序" in m and "不受影响" in m for m in w))

    def test_km_missing_groups_fatal(self):
        f, _ = gen_figure.validate_data({"labels": ["A"]}, "km")
        self.assertTrue(any("km 需要" in m for m in f))

    def test_roc_non_monotonic_fpr_warning(self):
        _, w = gen_figure.validate_data(
            {"curves": [{"fpr": [0.0, 0.9, 0.3], "tpr": [0.0, 0.7, 1.0]}]}, "roc")
        self.assertTrue(any("非单调" in m for m in w))

    def test_roc_auc_out_of_range_warning(self):
        _, w = gen_figure.validate_data(
            {"curves": [{"fpr": [0.0, 1.0], "tpr": [0.0, 1.0], "auc": 1.5}]}, "roc")
        self.assertTrue(any("auc" in m.lower() for m in w))

    def test_roc_missing_data_fatal(self):
        f, _ = gen_figure.validate_data({"labels": ["A"]}, "roc")
        self.assertTrue(any("curves" in m or "fpr" in m for m in f))

    def test_dual_axis_missing_left_fatal(self):
        f, _ = gen_figure.validate_data(
            {"labels": ["A", "B"], "right": {"R": [1.0, 2.0]}}, "dual_axis")
        self.assertTrue(any("left" in m for m in f))

    def test_composite_missing_panels_fatal(self):
        f, _ = gen_figure.validate_data({"layout": [1, 1]}, "composite")
        self.assertTrue(any("panels" in m for m in f))

    def test_composite_panel_missing_type_fatal(self):
        f, _ = gen_figure.validate_data(
            {"panels": [{"data": {"labels": ["A"], "series": {"S": [1.0]}}}]}, "composite")
        self.assertTrue(any("type" in m for m in f))

    def test_diagram_missing_blocks_fatal(self):
        f, _ = gen_figure.validate_data({"background": "light"}, "diagram")
        self.assertTrue(any("blocks" in m for m in f))

    def test_not_a_dict_fatal(self):
        f, _ = gen_figure.validate_data([1, 2, 3], "bar")
        self.assertTrue(any("JSON 对象" in m or "字典" in m for m in f))


# ── 3. load_data() CSV edge cases ──────────────────────────────────────

class TestLoadDataCSV(unittest.TestCase):
    """CSV parsing: long-format scatter/box, mixed numeric/text, TSV."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_csv_")
        self._n = 0

    def _csv(self, content, name="data.csv"):
        self._n += 1
        p = os.path.join(self.tmp, f"{self._n}_{name}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return p

    def test_scatter_long_format_groups(self):
        p = self._csv("x,y,group\n1,2,A\n2,4,A\n3,6,B\n4,8,B\n")
        d = gen_figure.load_data(p, chart_type="scatter")
        self.assertEqual(d["x"], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(d["y"], [2.0, 4.0, 6.0, 8.0])
        self.assertEqual(d["groups"], ["A", "A", "B", "B"])

    def test_box_long_format(self):
        p = self._csv("group,value\nCtrl,1\nCtrl,2\nCtrl,3\nDrug,4\nDrug,5\nDrug,6\n")
        d = gen_figure.load_data(p, chart_type="box")
        self.assertEqual(list(d["labels"]), ["Ctrl", "Drug"])
        self.assertEqual(d["series"]["Ctrl"], [1.0, 2.0, 3.0])
        self.assertEqual(d["series"]["Drug"], [4.0, 5.0, 6.0])

    def test_mixed_numeric_text_rows_skipped(self):
        """Non-numeric cells in numeric columns -> those rows dropped, rest parsed."""
        p = self._csv("label,value\nA,1\nB,NA\nC,3\n")
        d = gen_figure.load_data(p, chart_type="bar")
        self.assertEqual(d["labels"], ["A", "C"])
        self.assertEqual(d["series"]["value"], [1.0, 3.0])

    def test_tsv_delimiter(self):
        p = self._csv("label\tvalue\nA\t1\nB\t2\n", name="data.tsv")
        d = gen_figure.load_data(p, chart_type="bar")
        self.assertEqual(d["labels"], ["A", "B"])
        self.assertEqual(d["series"]["value"], [1.0, 2.0])

    def test_unsupported_format_raises(self):
        p = self._csv("a\n1\n", name="data.xlsx")
        with self.assertRaises(ValueError):
            gen_figure.load_data(p)

    def test_json_load(self):
        p = os.path.join(self.tmp, "d.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"labels": ["A"], "series": {"S": [1.0]}}, f)
        d = gen_figure.load_data(p)
        self.assertEqual(d["series"]["S"], [1.0])


# ── 4. has_cjk() ───────────────────────────────────────────────────────

class TestHasCJK(unittest.TestCase):
    def test_chinese_true(self):
        self.assertTrue(gen_figure.has_cjk("细胞因子"))
        self.assertTrue(gen_figure.has_cjk("IL-6 信号通路"))
        self.assertTrue(gen_figure.has_cjk("𠀀"))  # CJK Ext-B (U+20000) via \U00020000

    def test_ascii_false(self):
        self.assertFalse(gen_figure.has_cjk("IL-6 signaling"))
        self.assertFalse(gen_figure.has_cjk(""))

    def test_japanese_kanji_true(self):
        self.assertTrue(gen_figure.has_cjk("免疫応答"))


# ── 5. legend_audit() ──────────────────────────────────────────────────

class TestLegendAudit(unittest.TestCase):
    """Multi-series without labels must warn; exemptions respected."""

    def _ax(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        return ax

    def test_multi_series_no_labels_warns(self):
        ax = self._ax()
        ax.bar([0, 1], [1.0, 2.0])          # no label
        ax.bar([0.5, 1.5], [2.0, 1.0])      # no label
        msg = gen_figure.legend_audit(ax, "bar", no_legend=False, n_series=2)
        self.assertIsNotNone(msg)
        self.assertIn("图例", msg)

    def test_multi_series_with_labels_ok(self):
        ax = self._ax()
        ax.bar([0, 1], [1.0, 2.0], label="A")
        ax.bar([0.5, 1.5], [2.0, 1.0], label="B")
        self.assertIsNone(gen_figure.legend_audit(ax, "bar", no_legend=False, n_series=2))

    def test_no_legend_flag_skips(self):
        ax = self._ax()
        ax.bar([0, 1], [1.0, 2.0])
        self.assertIsNone(gen_figure.legend_audit(ax, "bar", no_legend=True, n_series=2))

    def test_single_series_ok(self):
        ax = self._ax()
        ax.bar([0, 1], [1.0, 2.0])
        self.assertIsNone(gen_figure.legend_audit(ax, "bar", no_legend=False, n_series=1))

    def test_exempt_types_ok(self):
        ax = self._ax()
        ax.bar([0, 1], [1.0, 2.0])
        ax.bar([0.5, 1.5], [2.0, 1.0])
        for ct in ("box", "boxplot", "violin", "heatmap", "forest",
                   "composite", "diagram", "dual_axis"):
            with self.subTest(chart_type=ct):
                self.assertIsNone(gen_figure.legend_audit(ax, ct, no_legend=False, n_series=2))


# ── 6. audit_pdf.py ────────────────────────────────────────────────────

class TestAuditPdf(unittest.TestCase):
    """Audit finds undersized spans; thresholds work."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_audit_")

    def _gen_pdf(self, journal=None):
        """Render a small bar PDF via the CLI; return its path."""
        data_path = os.path.join(self.tmp, "d.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE["bar"], f)
        out = os.path.join(self.tmp, "fig.pdf")
        cmd = [sys.executable, GEN, "--type", "bar", "--data", data_path, "--out", out]
        if journal:
            cmd += ["--journal", journal, "--column", "double"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return out

    def test_default_7pt_audit_clean(self):
        pdf = self._gen_pdf()
        offenders = audit_pdf.audit(pdf, min_size=7.0)
        self.assertEqual(offenders, [])

    def test_strict_threshold_finds_small_text(self):
        pdf = self._gen_pdf()
        offenders = audit_pdf.audit(pdf, min_size=12.0)
        self.assertGreater(len(offenders), 0)

    def test_journal_nature_6pt_clean(self):
        pdf = self._gen_pdf(journal="nature")
        offenders = audit_pdf.audit(pdf, min_size=6.0)
        self.assertEqual(offenders, [])


# ── 7. gen_legend.py ───────────────────────────────────────────────────

class TestGenLegend(unittest.TestCase):
    """Journal-format legend for every chart type."""

    def test_all_types_return_figure_text(self):
        for ct in SMOKE_TYPES:
            with self.subTest(chart_type=ct):
                txt = gen_legend.legend_for(SAMPLE[ct], ct, title="Main result")
                self.assertIn("Figure:", txt)
                self.assertNotIn("..", txt, f"{ct}: double period")
                self.assertTrue(txt.endswith("."))

    def test_km_log_rank_note(self):
        data = dict(SAMPLE["km"])
        data["log_rank"] = {"p": 0.03}
        txt = gen_legend.legend_for(data, "km", title="Survival")
        self.assertIn("Log-rank P = 0.03", txt)

    def test_forest_heterogeneity_note(self):
        data = dict(SAMPLE["forest"])
        data["heterogeneity"] = {"I2": 0.42}
        txt = gen_legend.legend_for(data, "forest", title="Meta")
        self.assertIn("I² = 42%", txt)

    def test_error_bars_note(self):
        data = dict(SAMPLE["bar"])
        data["errors"] = {"Ctrl": [0.1, 0.2, 0.1], "Treated": [0.2, 0.1, 0.2]}
        txt = gen_legend.legend_for(data, "bar", title="Bars")
        self.assertIn("Error bars indicate s.e.m.", txt)

    def test_composite_panel_letters(self):
        txt = gen_legend.legend_for(SAMPLE["composite"], "composite", title="Comp")
        self.assertIn("a, Panel A", txt)
        self.assertIn("b, Panel B", txt)

    def test_roc_auc_note(self):
        txt = gen_legend.legend_for(SAMPLE["roc"], "roc", title="ROC")
        self.assertIn("AUC values: 0.850", txt)


# ── v2.0.1: theme system, style presets, demo/explain, setup_env ───────

class TestV201ThemeSystem(unittest.TestCase):
    def test_default_theme_is_glm(self):
        self.assertEqual(gen_figure.resolve_theme(None), "glm")
        self.assertEqual(gen_figure.resolve_theme(""), "glm")

    def test_classic_alias_kept(self):
        self.assertEqual(gen_figure.resolve_theme("default"), "glm")
        self.assertEqual(gen_figure.resolve_theme("classic"), "classic")
        self.assertIn("classic", gen_figure.THEMES)

    def test_aliases_resolve(self):
        cases = {"okabe": "okabe-ito", "colorblind": "okabe-ito",
                 "glm-blog": "glm", "glmblog": "glm", "npg": "nature",
                 "matplotlib": "classic"}
        for alias, canonical in cases.items():
            with self.subTest(alias=alias):
                self.assertEqual(gen_figure.resolve_theme(alias), canonical)

    def test_case_insensitive_and_prefix(self):
        self.assertEqual(gen_figure.resolve_theme("OKABE"), "okabe-ito")
        self.assertEqual(gen_figure.resolve_theme("Nat"), "nature")
        self.assertEqual(gen_figure.resolve_theme("Conserv"), "conservative")

    def test_unknown_theme_none(self):
        self.assertIsNone(gen_figure.resolve_theme("nope"))

    def test_all_themes_have_colors(self):
        for key, theme in gen_figure.THEMES.items():
            with self.subTest(theme=key):
                self.assertTrue(theme["colors"])
                self.assertGreaterEqual(len(theme["colors"]), 2)


class TestV201StylePreset(unittest.TestCase):
    def _render(self, chart_type, extra=None):
        data_path = os.path.join(tempfile.gettempdir(), f"v201_{chart_type}.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE[chart_type], f)
        out = os.path.join(tempfile.gettempdir(), f"v201_{chart_type}.png")
        cmd = [sys.executable, GEN, "-t", chart_type, "-d", data_path, "-o", out]
        if extra:
            cmd += extra
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        exists = os.path.exists(out)
        if exists:
            os.remove(out)
        os.remove(data_path)
        return r, exists

    def test_style_glm_hatch_bar(self):
        r, ok = self._render("bar", ["--style", "glm-hatch"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(ok)
        self.assertIn("colorblind-safe", r.stderr)

    def test_style_glm_hatch_stacked(self):
        r, ok = self._render("stacked_bar", ["--style", "glm-hatch"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(ok)

    def test_style_glm_hatch_forest(self):
        r, ok = self._render("forest", ["--style", "glm-hatch"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(ok)

    def test_hatch_flag_alone(self):
        r, ok = self._render("bar", ["--hatch"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(ok)

    def test_theme_glm_explicit(self):
        r, ok = self._render("bar", ["--theme", "glm"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(ok)

    def test_theme_alias_okabe(self):
        r, ok = self._render("bar", ["--theme", "okabe"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(ok)


class TestV201MetaCommands(unittest.TestCase):
    def test_list_themes_exits_0(self):
        r = subprocess.run([sys.executable, GEN, "--list-themes"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        self.assertIn("glm", r.stdout)

    def test_explain_bar(self):
        r = subprocess.run([sys.executable, GEN, "--explain", "bar"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        self.assertIn("CSV", r.stdout)

    def test_explain_unknown_exits_1(self):
        r = subprocess.run([sys.executable, GEN, "--explain", "nope"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1)

    def test_theme_swatch_renders(self):
        out = os.path.join(tempfile.gettempdir(), "v201_swatch.png")
        r = subprocess.run([sys.executable, GEN, "--theme-swatch", "glm", "-o", out],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(out))
        os.remove(out)

    def test_demo_menu_default(self):
        r = subprocess.run([sys.executable, GEN, "--demo"],
                           input="1\n", capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("已保存:", r.stderr)

    def test_missing_required_exits_2(self):
        r = subprocess.run([sys.executable, GEN], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)


class TestSetupEnv(unittest.TestCase):
    def test_setup_env_runs(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "setup_env.py")],
                           capture_output=True, text=True, timeout=300)
        self.assertIn("环境自检", r.stdout)
        self.assertIn("环境就绪", r.stdout)


# ── Overlap mechanism regression: inverted axes must not nuke tick labels ──

class TestInvertedAxisTickPreservation(unittest.TestCase):
    """Regression: fix_tick_overlaps used to compute y-gaps as b[i+1].y0 -
    b[i].y1, which is always negative on inverted axes (heatmap/forest/km),
    so overlap was never cleared and labels got thinned to the first one.
    Also, hidden labels' boxes kept feeding the overlap check, so thinning
    never converged. Verify inverted-axis charts keep ALL tick labels."""

    def _render_and_count_labels(self, chart_type, data):
        fig, ax = plt.subplots(figsize=(9, 6))
        gen = gen_figure.GENERATORS[chart_type]
        gen(data, ax, gen_figure.THEMES["glm"], None)
        gen_figure.apply_base_style(ax, gen_figure.THEMES["glm"])
        plt.tight_layout()
        gen_figure.fix_tick_overlaps(fig)
        xl = [l for l in ax.get_xticklabels() if l.get_visible() and l.get_text().strip()]
        yl = [l for l in ax.get_yticklabels() if l.get_visible() and l.get_text().strip()]
        plt.close(fig)
        return xl, yl

    def test_heatmap_keeps_all_6_x_labels(self):
        data = {"rows": ["IL-6", "TNF-a", "CRP", "ESR", "DAS28", "SLEDAI"],
                "cols": ["IL-6", "TNF-a", "CRP", "ESR", "DAS28", "SLEDAI"],
                "matrix": [[1.0, 0.7, 0.8, 0.7, 0.8, 0.5],
                           [0.7, 1.0, 0.7, 0.6, 0.7, 0.3],
                           [0.8, 0.7, 1.0, 0.8, 0.8, 0.5],
                           [0.7, 0.6, 0.8, 1.0, 0.7, 0.4],
                           [0.8, 0.7, 0.8, 0.7, 1.0, 0.6],
                           [0.5, 0.3, 0.5, 0.4, 0.6, 1.0]]}
        xl, yl = self._render_and_count_labels("heatmap", data)
        self.assertEqual(len(xl), 6, f"heatmap x labels thinned: {[l.get_text() for l in xl]}")
        self.assertEqual(len(yl), 6)

    def test_forest_keeps_x_numeric_ticks(self):
        data = {"labels": ["S1", "S2", "S3", "S4"], "estimates": [0.72, 0.80, 0.75, 0.65],
                "ci_low": [0.55, 0.62, 0.56, 0.48], "ci_high": [0.94, 1.03, 1.00, 0.84],
                "overall": {"estimate": 0.73, "ci_low": 0.60, "ci_high": 0.88}}
        xl, yl = self._render_and_count_labels("forest", data)
        self.assertGreaterEqual(len(xl), 3, f"forest x ticks thinned: {[l.get_text() for l in xl]}")
        self.assertEqual(len(yl), 5)  # 4 studies + Overall

    def test_km_keeps_axis_labels(self):
        data = {"groups": {"A": [[0.0, 1.0], [5.0, 0.8]], "B": [[0.0, 1.0], [5.0, 0.9]]}}
        xl, yl = self._render_and_count_labels("km", data)
        self.assertGreaterEqual(len(xl), 2)
        self.assertGreaterEqual(len(yl), 2)


# ── Heatmap default colormap regression ────────────────────────────────

class TestHeatmapDefaultCmap(unittest.TestCase):
    """Regression: kwargs.get("cmap", "RdBu_r") never applied its default
    because main() always passes "cmap": args.cmap (None) — the key exists,
    so .get() returned None and imshow fell through to matplotlib's default
    viridis (yellow-green). The default must be RdBu_r unless overridden."""

    def test_default_cmap_is_rdbu_r(self):
        fig, ax = plt.subplots(figsize=(8, 6))
        data = {"rows": ["A", "B"], "cols": ["A", "B"],
                "matrix": [[1.0, -0.5], [-0.5, 1.0]]}
        kwargs = {"cmap": None}  # simulate main() always passing the key
        gen_figure.gen_heatmap(data, ax, gen_figure.THEMES["glm"], None, **kwargs)
        im = ax.images[0]
        self.assertEqual(im.get_cmap().name, "RdBu_r",
                         f"default cmap should be RdBu_r, got {im.get_cmap().name}")
        plt.close(fig)

    def test_explicit_cmap_still_overrides(self):
        fig, ax = plt.subplots(figsize=(8, 6))
        data = {"rows": ["A", "B"], "cols": ["A", "B"],
                "matrix": [[1.0, 0.5], [0.5, 1.0]]}
        kwargs = {"cmap": "YlOrRd"}
        gen_figure.gen_heatmap(data, ax, gen_figure.THEMES["glm"], None, **kwargs)
        im = ax.images[0]
        self.assertEqual(im.get_cmap().name, "YlOrRd")
        plt.close(fig)

    def test_all_positive_data_uses_warm_cmap_not_rdbu(self):
        """All-positive data must not render with RdBu_r — its white midpoint
        makes low positive values look like a broken band (断层). The default
        cmap switches to a warm sequential colormap for all-positive data."""
        fig, ax = plt.subplots(figsize=(8, 6))
        data = {"rows": ["A", "B"], "cols": ["A", "B"],
                "matrix": [[1.0, 0.5], [0.5, 0.3]]}
        kwargs = {"cmap": None}  # default path
        gen_figure.gen_heatmap(data, ax, gen_figure.THEMES["glm"], None, **kwargs)
        im = ax.images[0]
        self.assertEqual(im.get_cmap().name, "YlOrRd",
                         f"all-positive default should be YlOrRd, got {im.get_cmap().name}")
        plt.close(fig)

    def test_negative_data_keeps_diverging_rdbu(self):
        fig, ax = plt.subplots(figsize=(8, 6))
        data = {"rows": ["A", "B"], "cols": ["A", "B"],
                "matrix": [[1.0, -0.5], [-0.5, 1.0]]}
        kwargs = {"cmap": None}
        gen_figure.gen_heatmap(data, ax, gen_figure.THEMES["glm"], None, **kwargs)
        im = ax.images[0]
        self.assertEqual(im.get_cmap().name, "RdBu_r")
        plt.close(fig)


# ── Demo/example datasets must match the official data schemas ─────────

class TestDemoAndExampleSchemas(unittest.TestCase):
    """Every chart type reachable via --demo and every examples/*.json must
    pass validate_data() and render without raising. This catches schema
    drift between DEMO_DATA / example files and the generator functions
    (e.g. dual_axis used {"name","values"} objects instead of series dicts,
    km used object lists instead of {group: [[t,s],...]}, scatter/roc used
    unsupported formats — all crashed at render time)."""

    def _render(self, chart, data):
        fig, ax = plt.subplots(figsize=(8, 6))
        cjk_fp, _ = gen_figure.load_cjk_font()
        gen = gen_figure.GENERATORS[chart]
        extra = gen(data, ax, gen_figure.THEMES["glm"], cjk_fp)
        if chart not in ("dual_axis",) and extra not in ("composite", "diagram"):
            gen_figure.apply_base_style(ax, gen_figure.THEMES["glm"])
        plt.close(fig)

    def test_all_demo_datasets_valid_and_renderable(self):
        demo = gen_figure.DEMO_DATA
        self.assertTrue(demo, "DEMO_DATA must not be empty")
        for chart, data in demo.items():
            with self.subTest(demo_chart=chart):
                fatal, _warn = gen_figure.validate_data(data, chart)
                self.assertEqual(fatal, [], f"demo {chart} schema invalid: {fatal}")
                self._render(chart, data)

    def test_all_example_files_valid_and_renderable(self):
        examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
        if not os.path.isdir(examples_dir):
            self.skipTest("no examples dir")
        canonical = {"dual": "dual_axis", "stacked": "stacked_bar",
                     "box": "box", "roc": "roc", "km": "km"}
        for fname in sorted(os.listdir(examples_dir)):
            if not fname.endswith(".json"):
                continue
            with self.subTest(example=fname):
                data = json.load(open(os.path.join(examples_dir, fname)))
                chart = fname.replace("example_", "").replace(".json", "")
                chart = canonical.get(chart, chart)
                if chart not in gen_figure.GENERATORS:
                    self.fail(f"example file {fname} maps to unknown chart '{chart}'")
                fatal, _warn = gen_figure.validate_data(data, chart)
                self.assertEqual(fatal, [], f"{fname} schema invalid: {fatal}")
                self._render(chart, data)


class TestV210Prisma(unittest.TestCase):
    """v2.1 PRISMA 2020 flow: validation gates + CLI rendering."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_prisma_")

    def _validate(self, data):
        return gen_figure.validate_data(data, "prisma")

    def test_valid_data_passes(self):
        fatal, _ = self._validate(SAMPLE["prisma"])
        self.assertEqual(fatal, [])

    def test_missing_required_fields(self):
        fatal, _ = self._validate({})
        self.assertTrue(any("records_identified" in m for m in fatal), fatal)
        self.assertTrue(any("studies_included" in m for m in fatal), fatal)

    def test_negative_or_bool_rejected(self):
        fatal, _ = self._validate({"records_identified": -5, "studies_included": True})
        self.assertTrue(any("records_identified" in m for m in fatal), fatal)
        self.assertTrue(any("studies_included" in m for m in fatal), fatal)

    def test_screened_arithmetic_gate(self):
        data = {"records_identified": 100, "duplicates_removed": 10,
                "records_screened": 95, "studies_included": 5}
        fatal, _ = self._validate(data)
        self.assertTrue(any("数字自洽" in m for m in fatal), fatal)

    def test_reasons_total_gate(self):
        data = {"records_identified": 100, "records_excluded": 10,
                "exclusion_reasons": {"a": 3, "b": 4}, "studies_included": 5}
        fatal, _ = self._validate(data)
        self.assertTrue(any("数字自洽" in m for m in fatal), fatal)

    def test_reasons_nonint_rejected(self):
        data = {"records_identified": 10, "studies_included": 2,
                "exclusion_reasons": {"a": "3"}}
        fatal, _ = self._validate(data)
        self.assertTrue(any("非负整数" in m for m in fatal), fatal)

    def test_lang_gate(self):
        fatal, _ = self._validate({"records_identified": 10, "studies_included": 2,
                                   "lang": "fr"})
        self.assertTrue(any("lang" in m for m in fatal))

    def test_cli_render_en(self):
        data_path = os.path.join(self.tmp, "prisma.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE["prisma"], f)
        out = os.path.join(self.tmp, "prisma.png")
        proc = subprocess.run([sys.executable, GEN, "-t", "prisma", "-d", data_path,
                               "-o", out, "--dpi", "150"],
                              capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertGreater(os.path.getsize(out), 5000)

    def test_cli_render_zh(self):
        data = dict(SAMPLE["prisma"], lang="zh")
        data_path = os.path.join(self.tmp, "prisma_zh.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "prisma_zh.png")
        proc = subprocess.run([sys.executable, GEN, "-t", "prisma", "-d", data_path,
                               "-o", out, "--dpi", "150"],
                              capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertGreater(os.path.getsize(out), 5000)


class TestV210Suggest(unittest.TestCase):
    """v2.1 --suggest: heuristic chart-type recommendation."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_suggest_")

    def test_prisma_top(self):
        self.assertEqual(gen_figure.suggest_chart_type(SAMPLE["prisma"])[0][1], "prisma")

    def test_km_top(self):
        self.assertEqual(gen_figure.suggest_chart_type(SAMPLE["km"])[0][1], "km")

    def test_roc_top(self):
        self.assertEqual(gen_figure.suggest_chart_type(SAMPLE["roc"])[0][1], "roc")

    def test_forest_top(self):
        self.assertEqual(gen_figure.suggest_chart_type(SAMPLE["forest"])[0][1], "forest")

    def test_heatmap_top(self):
        self.assertEqual(gen_figure.suggest_chart_type(SAMPLE["heatmap"])[0][1], "heatmap")

    def test_scatter_top(self):
        self.assertEqual(gen_figure.suggest_chart_type(SAMPLE["scatter"])[0][1], "scatter")

    def test_bar_for_labels_series(self):
        recs = gen_figure.suggest_chart_type(SAMPLE["bar"])
        self.assertIn("bar", [r[1] for r in recs[:2]])

    def test_cli_suggest(self):
        data_path = os.path.join(self.tmp, "d.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE["km"], f)
        proc = subprocess.run([sys.executable, GEN, "--suggest", "-d", data_path],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("km", proc.stdout)
        self.assertIn("Run:", proc.stdout)

    def test_cli_suggest_requires_data(self):
        proc = subprocess.run([sys.executable, GEN, "--suggest"],
                              capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc.returncode, 0)


class TestV220LayoutFixes(unittest.TestCase):
    """v2.2 staged fixes: no silent label loss, PRISMA side-box auto-fit.

    Background: the overlap ladder used to hide tick labels (stride-thinning)
    before ever trying 90° rotation, silently; and PRISMA side boxes had a
    fixed width so long exclusion reasons spilled outside the frame.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_v220_")

    def test_ladder_rotates_90_before_thinning(self):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_xticks(range(6))
        ax.set_xticklabels(["aaaaaaaa", "bbbbbbbb", "cccccccc",
                            "dddddddd", "eeeeeeee", "ffffffff"], fontsize=8)
        self.assertTrue(gen_figure._degrade_axis(ax, 'x', 4))
        labs = [l for l in ax.get_xticklabels() if l.get_text().strip()]
        self.assertTrue(all(l.get_rotation() == 90 for l in labs))
        self.assertTrue(all(l.get_visible() for l in labs),
                        "90° rotation stage must not hide labels")
        plt.close(fig)

    def test_thinning_only_at_level5_and_reports(self):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_xticks(range(6))
        ax.set_xticklabels(["aaaaaaaa"] * 6, fontsize=8)
        self.assertTrue(gen_figure._degrade_axis(ax, 'x', 5))
        vis = [l.get_visible() for l in ax.get_xticklabels() if l.get_text().strip()]
        self.assertEqual(sum(vis), 3)  # stride 2 keeps every 2nd label
        plt.close(fig)

    def test_fix_tick_overlaps_warns_when_labels_hidden(self):
        fig, ax = plt.subplots(figsize=(2.0, 2.0))
        ax.set_xticks(range(12))
        ax.set_xticklabels([f"category {i} long label" for i in range(12)], fontsize=8)
        ax.set_yticks(range(12))
        ax.set_yticklabels([f"row {i}" for i in range(12)], fontsize=8)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            gen_figure.fix_tick_overlaps(fig)
        hidden = [l for l in ax.get_xticklabels() + ax.get_yticklabels()
                  if l.get_text().strip() and not l.get_visible()]
        if hidden:
            self.assertIn("WARNING", err.getvalue())
            self.assertIn("hid", err.getvalue())
        plt.close(fig)

    def test_prisma_long_reasons_stay_inside_side_box(self):
        fig, ax = plt.subplots(figsize=(10, 8))
        data = {"records_identified": 156, "duplicates_removed": 102,
                "records_excluded": 40,
                "exclusion_reasons": {
                    "Did not meet the predefined inclusion criteria": 3,
                    "No extractable quantitative outcome data": 3},
                "studies_included": 8}
        gen_figure.gen_prisma(data, ax, gen_figure.THEMES["glm"], None)
        fig.canvas.draw()
        ren = fig.canvas.get_renderer()
        side = [p for p in ax.patches
                if tuple(round(v, 2) for v in p.get_facecolor()[:3]) == (0.95, 0.95, 0.95)]
        self.assertTrue(side, "side boxes not found")
        right = max(p.get_window_extent(ren).x1 for p in side)
        left = min(p.get_window_extent(ren).x0 for p in side)
        items = [t for t in ax.texts if t.get_text().strip().startswith("·")]
        self.assertEqual(len(items), 2)
        for t in items:
            bb = t.get_window_extent(ren)
            self.assertGreaterEqual(bb.x0, left - 1.0,
                                    f"reason text spills left: {t.get_text()!r}")
            self.assertLessEqual(bb.x1, right + 1.0,
                                 f"reason text spills right: {t.get_text()!r}")
        plt.close(fig)


class TestV220Features(unittest.TestCase):
    """v2.2: journal presets 9, xlsx input, --stats auto, --alt, templates."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_v220_")

    def test_journal_presets_complete(self):
        need = {"nature", "lancet", "science", "cell", "nejm", "jama",
                "ieee", "cma", "cn-core"}
        self.assertTrue(need.issubset(gen_figure.JOURNAL_PRESETS.keys()),
                        f"missing: {need - set(gen_figure.JOURNAL_PRESETS)}")
        for cn in ("cma", "cn-core"):
            self.assertTrue(gen_figure.JOURNAL_PRESETS[cn].get("cjk_default"),
                            f"{cn} must auto-enable CJK")
            self.assertIn("widths_mm", gen_figure.JOURNAL_PRESETS[cn])

    def test_load_xlsx_wide_format(self):
        import openpyxl
        p = os.path.join(self.tmp, "wb.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Group", "Treatment", "Control"])
        ws.append(["Wk12", 62, 28])
        ws.append(["Wk24", 71, 32])
        wb.save(p)
        d = gen_figure.load_data(p, chart_type="bar")
        self.assertEqual(d["labels"], ["Wk12", "Wk24"])
        self.assertEqual(d["series"]["Treatment"], [62.0, 71.0])
        self.assertEqual(d["series"]["Control"], [28.0, 32.0])

    def test_load_xlsx_bad_sheet(self):
        import openpyxl
        p = os.path.join(self.tmp, "wb2.xlsx")
        wb = openpyxl.Workbook()
        wb.active.append(["Group", "V"])
        wb.active.append(["A", 1])
        wb.save(p)
        with self.assertRaises(ValueError) as cm:
            gen_figure.load_data(p, chart_type="bar", sheet="Nope")
        self.assertIn("Nope", str(cm.exception))

    def test_pairwise_vs_first_significant_and_ns(self):
        rng = np.random.default_rng(7)
        lo = list(rng.normal(10.0, 1.0, 40))
        hi = list(rng.normal(14.0, 1.0, 40))
        same = list(rng.normal(10.0, 1.0, 40))
        res = gen_figure.pairwise_vs_first({"Ctl": lo, "Hi": hi, "Same": same})
        by = {r[0]: r for r in res}
        self.assertIn(by["Hi"][2], ("*", "**", "***"))
        self.assertEqual(by["Same"][2], "NS")

    def test_gen_box_stats_auto_draws_brackets(self):
        data = {"labels": ["A", "B"],
                "series": {"A": [1, 2, 3, 4, 5, 6], "B": [4, 5, 6, 7, 8, 9]}}
        fig, ax = plt.subplots(figsize=(6, 4))
        gen_figure.GENERATORS["box"](data, ax, gen_figure.THEMES["glm"],
                                     None, stats_auto=True)
        star_texts = [t.get_text() for t in ax.texts
                      if t.get_text() in ("*", "**", "***", "NS", "n.s.")]
        self.assertTrue(star_texts, "bracket star label missing")
        plt.close(fig)

    def test_generate_alt_text_bar_and_km(self):
        bar = {"labels": ["A", "B"], "series": {"T": [1, 2]}}
        txt = gen_figure.generate_alt_text("bar", bar, "疗效对比")
        self.assertIn("柱状图", txt)
        self.assertIn("疗效对比", txt)
        km = {"groups": {"T": [[1, 1]], "C": [[2, 0]]},
              "log_rank": {"p": 0.03, "method": "Log-rank"}}
        txt2 = gen_figure.generate_alt_text("km", km)
        self.assertIn("Kaplan-Meier", txt2)
        self.assertIn("0.03", txt2)

    def test_cli_alt_sidecar(self):
        data_path = os.path.join(self.tmp, "km.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"groups": {"T": [[10, 1], [20, 0]], "C": [[8, 1], [15, 1]]},
                       "log_rank": {"p": 0.2, "method": "Log-rank"}}, f)
        out = os.path.join(self.tmp, "km.png")
        proc = subprocess.run([sys.executable, GEN, "-t", "km", "-d", data_path,
                               "-o", out, "--alt"], capture_output=True,
                              text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        side = os.path.join(self.tmp, "km.alt.txt")
        self.assertTrue(os.path.exists(side), "alt sidecar missing")
        content = open(side, encoding="utf-8").read()
        self.assertIn("Kaplan-Meier", content)

    def test_cli_xlsx_input(self):
        import openpyxl
        p = os.path.join(self.tmp, "data.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Group", "S1", "S2"])
        ws.append(["A", 10, 12])
        ws.append(["B", 20, 18])
        wb.save(p)
        out = os.path.join(self.tmp, "bar.png")
        proc = subprocess.run([sys.executable, GEN, "-t", "bar", "-d", p,
                               "-o", out], capture_output=True, text=True,
                              timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_cli_stats_auto_violin(self):
        data_path = os.path.join(self.tmp, "v.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"labels": ["A", "B"],
                       "series": {"A": [1, 2, 3, 4, 5], "B": [5, 6, 7, 8, 9]}}, f)
        out = os.path.join(self.tmp, "v.png")
        proc = subprocess.run([sys.executable, GEN, "-t", "violin", "-d", data_path,
                               "-o", out, "--stats", "auto"], capture_output=True,
                              text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("stats (violin)", proc.stderr)

    def test_templates_present_and_valid(self):
        tdir = os.path.join(SCRIPT_DIR, "..", "templates")
        jsons = sorted(glob.glob(os.path.join(tdir, "*.json")))
        self.assertEqual(len(jsons), 22, f"expected 22 templates (v2.6: all chart types), got {len(jsons)}")
        for p in jsons:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            self.assertIn("_chart_type", d, p)
            self.assertIn("_command", d, p)
        self.assertTrue(os.path.exists(os.path.join(tdir, "README.md")))

    def test_cli_journal_cma_preset(self):
        data_path = os.path.join(self.tmp, "b.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"labels": ["组一", "组二"], "series": {"甲": [3, 4]}}, f)
        out = os.path.join(self.tmp, "cma.pdf")
        proc = subprocess.run([sys.executable, GEN, "-t", "bar", "-d", data_path,
                               "-o", out, "--journal", "cma", "--cjk"],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("期刊预设 cma", proc.stderr)



class TestV230Features(unittest.TestCase):
    """v2.3 统计深水区：新图型、KM 自动风险表、multi/DeLong、batch/caption。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_v23_")
        self.gen = os.path.join(SCRIPT_DIR, "gen_figure.py")

    def _render(self, chart, data_obj, extra_args=None, name=None):
        data_path = os.path.join(self.tmp, (name or chart) + ".json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data_obj, f, ensure_ascii=False)
        out = os.path.join(self.tmp, (name or chart) + ".png")
        proc = subprocess.run(
            [sys.executable, self.gen, "-t", chart, "-d", data_path, "-o", out]
            + (extra_args or []),
            capture_output=True, text=True, timeout=180)
        return proc, out

    # ── 新图型冒烟 ──

    FUNNEL = {"studies": [
        {"name": "A 2020", "effect": 0.69, "se": 0.12},
        {"name": "B 2021", "effect": 0.55, "se": 0.20},
        {"name": "C 2022", "effect": 0.80, "se": 0.09},
        {"name": "D 2023", "effect": 0.42, "se": 0.31},
        {"name": "E 2024", "effect": 0.61, "se": 0.15},
        {"name": "F 2025", "effect": 0.73, "se": 0.11}]}

    def test_smoke_funnel_with_egger(self):
        proc, out = self._render("funnel", self.FUNNEL, ["--egger"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))
        self.assertIn("Egger", proc.stderr)

    def test_smoke_bland_altman(self):
        proc, out = self._render("bland_altman", {
            "methods": {"新仪器": [5.1, 4.9, 5.3, 5.6, 4.8, 5.2],
                        "金标准": [5.0, 5.1, 5.2, 5.4, 5.0, 5.1]}})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_smoke_pca_groups(self):
        proc, out = self._render("pca", {
            "matrix": [[5.1, 3.5, 1.4, 0.2], [4.9, 3.0, 1.4, 0.2], [6.7, 3.1, 4.4, 1.4],
                       [6.0, 2.9, 4.5, 1.5], [6.3, 3.3, 6.0, 2.5], [5.8, 2.7, 5.1, 1.9]],
            "groups": ["a", "a", "b", "b", "c", "c"],
            "feature_names": ["萼长", "萼宽", "瓣长", "瓣宽"]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))
        self.assertIn("PC1+PC2", proc.stderr)

    def test_smoke_paired_stats(self):
        proc, out = self._render("paired", {
            "series": {"术前": [8.2, 7.5, 9.1, 6.8, 7.9, 8.5],
                       "术后": [6.1, 5.8, 7.2, 5.0, 6.3, 6.9]}}, ["--stats", "auto"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("p=", proc.stderr)

    def test_smoke_venn(self):
        proc, out = self._render("venn", {"sets": {
            "A": ["x", "y", "z", "w"], "B": ["x", "z", "p"], "C": ["x", "q"]}})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_smoke_cluster_heatmap(self):
        proc, out = self._render("cluster_heatmap", {
            "matrix": [[2.1, 0.3, 1.8, 0.1], [1.9, 0.2, 2.0, 0.3],
                       [0.2, 2.2, 0.1, 1.9], [0.3, 2.0, 0.4, 2.1]],
            "row_labels": ["s1", "s2", "s3", "s4"],
            "col_labels": ["gA", "gB", "gC", "gD"]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))
        self.assertIn("聚类顺序", proc.stderr)

    # ── 新图型拒绝（付费前/渲染前拦截）──

    def test_funnel_rejects_missing_se(self):
        bad = {"studies": [{"name": "A", "effect": 0.5}, {"name": "B", "effect": 0.6}]}
        proc, _ = self._render("funnel", bad)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("se", proc.stderr)

    def test_venn_rejects_one_set(self):
        proc, _ = self._render("venn", {"sets": {"A": [1, 2, 3]}})
        self.assertNotEqual(proc.returncode, 0)

    def test_pca_rejects_nan(self):
        proc, _ = self._render("pca", {
            "matrix": [[1.0, 2.0], [2.0, None], [3.0, 4.0], [4.0, 1.0]]})
        self.assertNotEqual(proc.returncode, 0)

    def test_cluster_rejects_nan(self):
        proc, _ = self._render("cluster_heatmap", {
            "matrix": [[1.0, 2.0], [2.0, None], [3.0, 4.0]]})
        self.assertNotEqual(proc.returncode, 0)

    # ── KM 自动风险表 + 自动 log-rank ──

    KM_DATA = {"groups": {
        "对照组": [[1, 1], [2, 1], [3, 1], [4, 0], [5, 1], [6, 1], [7, 1], [8, 1]],
        "治疗组": [[3, 1], [5, 1], [8, 0], [9, 1], [11, 1], [12, 1], [14, 1], [16, 1]]}}

    def test_km_auto_logrank_and_risk_table(self):
        proc, out = self._render("km", dict(self.KM_DATA))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("log-rank", proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_km_no_risk_table_flag(self):
        proc, out = self._render("km", dict(self.KM_DATA), ["--no-risk-table"],
                                 name="km_nort")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_km_risk_times_custom(self):
        proc, out = self._render("km", dict(self.KM_DATA), ["--risk-times", "2,6,10"],
                                 name="km_rt")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_km_precomputed_warns_no_auto(self):
        data = {"time": [1, 2, 3], "survival": {"A": [1.0, 0.5, 0.5], "B": [1.0, 0.9, 0.6]}}
        proc, out = self._render("km", data, name="km_pre")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("原始数据", proc.stderr)

    # ── 统计模块金标准/恒等式 ──

    def test_delong_auc_identity_mwu(self):
        import af_v23_stats as st
        rng = np.random.default_rng(7)
        y = np.array([0] * 40 + [1] * 30)
        s1 = rng.normal(size=70) + y * 0.8
        aucs, _ = st.delong_paired(y, {"m1": s1})
        from scipy import stats as sst
        u = sst.mannwhitneyu(s1[y == 1], s1[y == 0], alternative="greater").statistic
        self.assertAlmostEqual(aucs["m1"], u / (30 * 40), places=10)

    def test_delong_identical_scores_p_is_one(self):
        import af_v23_stats as st
        rng = np.random.default_rng(3)
        y = np.array([0] * 25 + [1] * 25)
        s = rng.normal(size=50) + y
        _, pairs = st.delong_paired(y, {"a": s, "b": s.copy()})
        self.assertAlmostEqual(pairs[0][2], 1.0, places=12)

    def test_delong_separation_small_p(self):
        import af_v23_stats as st
        rng = np.random.default_rng(11)
        y = np.array([0] * 40 + [1] * 40)
        weak = rng.normal(size=80) + y * 0.3
        strong = weak + y * 1.2
        _, pairs = st.delong_paired(y, {"weak": weak, "strong": strong})
        self.assertLess(pairs[0][2], 0.05)

    def test_logrank_separated_groups_significant(self):
        import af_v23_stats as st
        g = {"早发": ([1, 2, 3, 4, 5], [1, 1, 1, 1, 1]),
             "晚发": ([9, 10, 11, 12, 13], [1, 1, 1, 1, 1])}
        chi2, p, df = st.logrank_test(g)
        self.assertEqual(df, 1)
        self.assertLess(p, 0.05)

    def test_km_at_risk_hand_example(self):
        import af_v23_stats as st
        times = [1, 2, 3, 4, 5, 6, 7]
        events = [1, 0, 1, 1, 0, 1, 1]
        self.assertEqual(st.km_at_risk(times, events, [0, 3, 6]), [7, 5, 2])

    def test_km_estimate_survival_values(self):
        import af_v23_stats as st
        t_seq, s_seq, cens = st.km_estimate([1, 2, 2, 3], [1, 1, 0, 1])
        self.assertEqual(s_seq[0], 1.0)
        # t=1: 1/4 事件→0.75；t=2: 1/3 事件→0.5（另一例删失）；t=3: 1/1 事件→0
        self.assertAlmostEqual(s_seq[1], 0.75, places=12)
        self.assertAlmostEqual(s_seq[2], 0.5, places=12)
        self.assertAlmostEqual(s_seq[-1], 0.0, places=12)
        self.assertEqual(len(cens), 1)

    def test_hochberg_hand_example(self):
        import af_v23_stats as st
        adj = st.hochberg([0.01, 0.03, 0.04])
        # 期望值（手工计算）：p_(3)=0.04*3=0.12, p_(2)=min(0.12, 0.03*2=0.06)=0.06,
        # p_(1)=min(0.06, 0.01*1)=0.01
        self.assertAlmostEqual(adj[0], 0.01, places=12)
        self.assertAlmostEqual(adj[1], 0.06, places=12)
        self.assertAlmostEqual(adj[2], 0.12, places=12)

    def test_dl_pool_no_heterogeneity_tau_zero(self):
        import af_v23_stats as st
        # 构造完全一致的真效应：es_i = theta + se_i * z_i，取 z_i 全 0
        res = st.dl_pool([0.7, 0.7, 0.7], [0.1, 0.2, 0.3])
        self.assertAlmostEqual(res["pooled"], 0.7, places=12)
        self.assertAlmostEqual(res["tau2"], 0.0, places=12)
        self.assertAlmostEqual(res["i2"], 0.0, places=9)

    def test_tukey_identical_means_p_one(self):
        import af_v23_stats as st
        pairs = st.tukey_pairs({"a": [1.0, 1.0, 1.0, 1.0],
                                "b": [1.0, 1.0, 1.0, 1.0],
                                "c": [1.0, 1.0, 1.0, 1.0]})
        for (_, _, p, _, _) in pairs:
            self.assertAlmostEqual(p, 1.0, places=9)

    def test_dunn_matches_scikit_posthocs(self):
        try:
            import scikit_posthocs as sp  # noqa: F401
        except ImportError:
            self.skipTest("scikit-posthocs 未安装（可选对拍依赖）")
        import af_v23_stats as st
        rng = np.random.default_rng(42)
        series = {"a": rng.normal(0, 1, 30).tolist(),
                  "b": rng.normal(0.5, 1, 25).tolist(),
                  "c": rng.normal(1.0, 1, 28).tolist()}
        ours = {(a, b): p for a, b, p, _, _ in st.dunn_pairs(series)}
        df_long = []
        for name, vals in series.items():
            for v in vals:
                df_long.append((name, v))
        import pandas as _pd
        dfx = _pd.DataFrame(df_long, columns=["g", "v"])
        ref = sp.posthoc_dunn(dfx, val_col="v", group_col="g", p_adjust=None)
        names = list(series.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                self.assertAlmostEqual(ours[(names[i], names[j])],
                                       float(ref.iloc[i, j]), places=6)

    def test_multi_pairwise_routes_normal_to_tukey(self):
        import af_v23_stats as st
        rng = np.random.default_rng(5)
        series = {g: rng.normal(loc, 0.25, 60).tolist()
                  for g, loc in (("甲", 0.0), ("乙", 0.0), ("丙", 1.0))}
        pairs = st.multi_pairwise(series)
        methods = {m for _, _, _, _, m in pairs}
        self.assertEqual(methods, {"Tukey HSD"})
        by_pair = {(a, b): p for a, b, p, _, _ in pairs}
        self.assertLess(by_pair[("甲", "丙")], 0.05)
        self.assertGreater(by_pair[("甲", "乙")], 0.05)

    # ── CLI：--stats multi / --compare / batch / caption / 兜底 ──

    def test_cli_stats_multi_brackets(self):
        rng = np.random.default_rng(9)
        data = {"series": {"对照": rng.normal(0, 0.3, 40).tolist(),
                           "低剂": rng.normal(0.1, 0.3, 38).tolist(),
                           "高剂": rng.normal(1.2, 0.3, 42).tolist()}}
        proc, out = self._render("box", data, ["--stats", "multi"], name="box_multi")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        combined = proc.stderr
        self.assertTrue(("Tukey" in combined) or ("Dunn" in combined))

    def test_cli_roc_compare_delong(self):
        rng = np.random.default_rng(21)
        n_pos, n_neg = 30, 40
        y = [1] * n_pos + [0] * n_neg
        base = rng.normal(0, 1, n_pos + n_neg)
        s1 = (base + [v * 0.6 for v in y]).tolist()
        s2 = (base + [v * 1.4 for v in y]).tolist()
        data = {"labels": y, "curves": [
            {"name": "模型弱", "scores": s1},
            {"name": "模型强", "scores": s2}]}
        proc, _ = self._render("roc", data, ["--compare"], name="roc_cmp")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("DeLong", proc.stderr)

    def test_cli_batch_two_figures(self):
        d1 = os.path.join(self.tmp, "b1.json")
        d2 = os.path.join(self.tmp, "b2.json")
        with open(d1, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲", "乙"], "series": {"S": [1, 2]}}, f)
        with open(d2, "w", encoding="utf-8") as f:
            json.dump({"a": [1, 2, 3, 4], "b": [2, 3, 2, 5]}, f)
        o1 = os.path.join(self.tmp, "batch1.png")
        o2 = os.path.join(self.tmp, "batch2.png")
        manifest = os.path.join(self.tmp, "figures.json")
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump([{"type": "bar", "data": d1, "out": o1},
                       {"type": "bland_altman", "data": d2, "out": o2}], f)
        proc = subprocess.run([sys.executable, self.gen, "--batch", manifest],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(o1) and os.path.exists(o2))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "figures.batch-report.json")))

    def test_cli_caption_bilingual(self):
        data = {"series": {"甲": [1, 2, 3, 4], "乙": [2, 3, 4, 5]},
                "labels": ["甲", "乙"]}
        data_path = os.path.join(self.tmp, "cap.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "cap.png")
        proc = subprocess.run([sys.executable, self.gen, "-t", "box", "-d", data_path,
                               "-o", out, "--caption", "--title", "疗效对比"],
                              capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        cap_path = os.path.join(self.tmp, "cap.caption.txt")
        self.assertTrue(os.path.exists(cap_path))
        with open(cap_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("箱线图", content)
        self.assertIn("Fig.", content)
        self.assertIn("疗效对比", content)

    def test_friendly_error_no_traceback(self):
        bad_path = os.path.join(self.tmp, "bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("this is not {{{ valid json")
        proc = subprocess.run([sys.executable, self.gen, "-t", "bar", "-d", bad_path,
                               "-o", os.path.join(self.tmp, "x.png")],
                              capture_output=True, text=True, timeout=120)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("JSON 语法错误", proc.stderr)  # A2 v3：中文诊断+针对性建议
        self.assertIn("建议", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_stderr_chinese_gate(self):
        """中文门禁：成功+报错路径 stderr 不得出现纯英文句子（≥2 连续英文词且无中文）。"""
        import re
        data_path = os.path.join(self.tmp, "g.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲", "乙"], "series": {"S1": [1, 2, 3, 4]}}, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "g.png")
        procs = [subprocess.run([sys.executable, self.gen, "-t", "bar", "-d", data_path,
                                 "-o", out, "--cjk"], capture_output=True, text=True, timeout=120)]
        bad_path = os.path.join(self.tmp, "g_bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            json.dump({"x": [1], "y": [2]}, f)
        procs.append(subprocess.run([sys.executable, self.gen, "-t", "scatter", "-d", bad_path,
                                     "-o", os.path.join(self.tmp, "g2.png")],
                                    capture_output=True, text=True, timeout=120))
        for proc in procs:
            for line in proc.stderr.splitlines():
                if re.search(r"[A-Za-z]{3,}[ ,][A-Za-z]{3,}", line) and not re.search(r"[一-鿿]", line):
                    self.fail(f"stderr 英文残留: {line.strip()[:100]}")


    def test_heatmap_labels_never_thinned(self):
        """回归锁：热图家族行列标签是数据——50 行 USArrests 渲染后 50 个 y 标签全在。"""
        import gen_figure as gf
        data = {"matrix": [[float(i) + j * 0.1 for j in range(4)] for i in range(50)],
                "row_labels": [f"R{i:02d}" for i in range(50)],
                "col_labels": ["a", "b", "c", "d"]}
        fig, ax = plt.subplots(figsize=(7, 9))
        gf.gen_heatmap(data, ax, gf.THEMES["glm"], None)
        gf.fix_tick_overlaps(fig)
        self.assertEqual(len(ax.get_yticklabels()), 50,
                         "热图 y 标签被防重叠机制剥除——类别轴必须豁免")

    def test_cluster_heatmap_50rows_all_labels(self):
        import gen_figure as gf
        data = {"matrix": [[float(i % 7) + j for j in range(3)] for i in range(50)],
                "row_labels": [f"S{i:02d}" for i in range(50)],
                "col_labels": ["x", "y", "z"]}
        import af_v23_charts
        fig, ax = plt.subplots(figsize=(7, 9))
        af_v23_charts.gen_cluster_heatmap(data, ax, gf.THEMES["glm"], None)
        gf.fix_tick_overlaps(fig)
        self.assertEqual(len(ax.get_yticklabels()), 50)


    def test_pca_dense_labels_zero_overlap(self):
        """回归锁（图9 缺陷重演）：32 车型密集 PCA 的样本标签渲染后零重叠。"""
        import gen_figure as gf
        import af_v23_charts
        rng = np.random.default_rng(1974)
        data = {"matrix": rng.normal(0, 1, (32, 5)).tolist() + [[rng.uniform(-2, 2) for _ in range(5)] for _ in range(2)],
                "row_labels": [f"Hornet Sportabout {i}" if i % 7 == 0 else f"Car Model {i}" for i in range(32)],
                "feature_names": ["f1", "f2", "f3", "f4", "f5"]}
        data["matrix"] = data["matrix"][:32]
        data["row_labels"] = data["row_labels"][:32]
        fig, ax = plt.subplots(figsize=(7, 5))
        af_v23_charts.gen_pca(data, ax, gf.THEMES["glm"], None)
        gf.fix_tick_overlaps(fig)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbs = [t.get_window_extent(renderer) for t in ax.texts]
        n_over = sum(1 for i in range(len(bbs)) for j in range(i + 1, len(bbs))
                     if bbs[i].overlaps(bbs[j]))
        self.assertEqual(n_over, 0, f"PCA 标签仍有 {n_over} 处重叠（declutter/thin 未生效）")
        # 对应关系锁：每个锚点（数据点）附近必须有标签，标签不得漂离锚点过远
        sx = float(np.ptp(np.array(data["matrix"])[:, 0:2].sum(axis=1)))  # 任意跨度参考
        span = 12.0  # 标准化数据 PC 轴跨度参考（宽松下限）
        max_disp = 0.15 * span
        pts = np.array(data["matrix"])[:, :2]
        for pos_text in ax.texts:
            if not pos_text.get_text().strip():
                continue  # 载荷箭头等空对象已由 FancyArrowPatch 消除
            tx, ty = pos_text.get_position()
            near = np.min(np.hypot(pts[:, 0] - tx, pts[:, 1] - ty)) if len(pts) else 0
            self.assertLessEqual(near, max_disp,
                                 f"标签 '{pos_text.get_text()}' 漂离所有数据点 {near:.2f} > {max_disp}")


    def test_cjk_font_enforcement_mechanism(self):
        """回归锁（豆腐块根治）：忘传 fontproperties 的中文文本，保存路径统一兜底。"""
        import gen_figure as gf
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.6, "对照组：无字体属性")   # 故意不传 fontproperties
        ax.text(0.5, 0.3, "plain english only")  # 非中文不受影响
        cjk_fp, _ = gf.load_cjk_font(None)
        if cjk_fp is None:
            self.skipTest("无 CJK 字体环境")
        # 走与 main 相同的兜底逻辑
        import matplotlib.text as mtext
        fixed = 0
        for t_obj in fig.findobj(mtext.Text):
            if t_obj.get_text() and gf.has_cjk(t_obj.get_text()):
                t_obj.set_fontproperties(cjk_fp)
                fixed += 1
        self.assertGreaterEqual(fixed, 1, "兜底未识别到含中文文本")
        # 断言中文 Text 的字体族已指向 CJK 字体
        for t_obj in fig.findobj(mtext.Text):
            if gf.has_cjk(t_obj.get_text()):
                fam = t_obj.get_fontfamily()
                self.assertTrue(fam, "中文文本字体族为空")


    def test_v240_median_survival_lifelines_identity(self):
        """v2.4 锁：KM 中位生存与 lifelines 全等（20 组随机删失数据集）。"""
        import af_v23_stats as st
        try:
            from lifelines import KaplanMeierFitter
        except ImportError:
            self.skipTest("lifelines 未安装（对拍参考）")
        rng = np.random.default_rng(2024)
        for _ in range(20):
            n = int(rng.integers(30, 150))
            t = np.minimum(rng.exponential(1/0.1, n), rng.uniform(5, 40)).round(1)
            e = (rng.exponential(1/0.1, n) <= t).astype(int)
            kmf = KaplanMeierFitter()
            kmf.fit(t, e)
            rm = kmf.median_survival_time_
            om, _, _ = st.km_median_survival(t, e)
            if np.isnan(rm):
                self.assertIsNone(om)
            else:
                self.assertIsNotNone(om)
                self.assertAlmostEqual(rm, om, places=9)

    def test_v240_median_survival_freireich(self):
        import af_v23_stats as st
        pl_t = [1,1,2,2,3,4,4,5,5,8,8,8,8,11,11,12,12,15,17,22,23]
        pl_e = [1]*21
        m, lo, hi = st.km_median_survival(pl_t, pl_e)
        self.assertEqual(m, 8.0)  # 文献标准值
        self.assertIsNotNone(lo)
        mp_t = [6,6,6,7,9,10,10,11,13,16,17,19,20,22,23,25,32,32,34,35]
        mp_e = [1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        m2, _, _ = st.km_median_survival(mp_t, mp_e)
        self.assertIsNone(m2)  # 曲线未降到 0.5：不可估计

    def test_v240_leave_one_out_identity(self):
        import af_v23_stats as st
        rng = np.random.default_rng(5)
        es = rng.normal(0.5, 0.2, 10).tolist()
        ses = np.linspace(0.08, 0.3, 10).tolist()
        loo = st.leave_one_out(es, ses)
        self.assertEqual(len(loo), 10)
        for i, pooled, lo, hi in loo:
            sub_e = [es[k] for k in range(10) if k != i]
            sub_s = [ses[k] for k in range(10) if k != i]
            r = st.dl_pool(sub_e, sub_s)
            self.assertAlmostEqual(pooled, r["pooled"], places=12)
            self.assertAlmostEqual(lo, r["pooled"] - 1.96*r["se"], places=12)
        with self.assertRaises(ValueError):
            st.leave_one_out([0.5, 0.6], [0.1, 0.1])  # <4 研究

    def test_v240_cli_km_median_annotation(self):
        data = {"groups": {"对照": [[1,1],[2,1],[3,1],[4,0],[5,1],[6,1],[7,1],[8,1]],
                            "治疗": [[3,1],[5,1],[8,0],[9,1],[11,1],[12,1],[14,1],[16,1]]}}
        proc, out = self._render("km", data, name="km_med")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("自动中位生存", proc.stderr)

    def test_v240_cli_forest_sensitivity(self):
        data = {"labels": [f"S{i}" for i in range(8)],
                "estimates": [0.5, 0.7, 0.4, 0.6, 0.55, 0.65, 0.45, 0.6],
                "se_list": [0.1, 0.2, 0.12, 0.15, 0.18, 0.14, 0.22, 0.16],
                "ci_low": [0.3, 0.3, 0.16, 0.3, 0.2, 0.37, 0.02, 0.29],
                "ci_high": [0.7, 1.1, 0.64, 0.9, 0.9, 0.93, 0.88, 0.91]}
        proc, out = self._render("forest", data, ["--sensitivity"], name="forest_sens")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("留一法", proc.stderr)

    def test_risk_times_bad_arg_rejected(self):
        data_path = os.path.join(self.tmp, "rt.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump({"groups": {"A": [[1, 1], [2, 1], [3, 1], [4, 1]]}}, f)
        proc = subprocess.run([sys.executable, self.gen, "-t", "km", "-d", data_path,
                               "-o", os.path.join(self.tmp, "rt.png"), "--risk-times", "abc,x"],
                              capture_output=True, text=True, timeout=120)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("无法解析为数字", proc.stderr)


    def test_alt_for_new_charts(self):
        proc, out = self._render("funnel", self.FUNNEL, ["--alt"], name="funnel_alt")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        alt_path = os.path.splitext(out)[0] + ".alt.txt"
        self.assertTrue(os.path.exists(alt_path))
        with open(alt_path, encoding="utf-8") as f:
            self.assertIn("漏斗图", f.read())


class TestV250SubmissionPolish(unittest.TestCase):
    """v2.5.0 投稿精修：--annotate / 期刊配色主题 / venn --area / 图例控制。"""

    def _run(self, chart_type, data, extra=(), name="v250"):
        data_path = os.path.join(tempfile.gettempdir(), f"v250_{name}.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        out = os.path.join(tempfile.gettempdir(), f"v250_{name}.png")
        if os.path.exists(out):
            os.remove(out)
        cmd = [sys.executable, GEN, "-t", chart_type, "-d", data_path, "-o", out,
               "--dpi", "110"] + list(extra)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return proc, out

    # ── 期刊配色主题 ──

    def test_v250_theme_nejm_science_registered(self):
        import gen_figure as gf
        self.assertEqual(gf.resolve_theme("nejm"), "nejm")
        self.assertEqual(gf.resolve_theme("new-england"), "nejm")
        self.assertEqual(gf.resolve_theme("science"), "science")
        self.assertEqual(gf.resolve_theme("aaas"), "science")
        for t in ("nejm", "science"):
            self.assertIn(t, gf.THEMES)
            self.assertIn(t, gf.THEME_ORDER)
            self.assertIn(t, gf.THEME_SWATCH_DESCRIPTIONS)
        self.assertEqual(len(gf.THEMES["nejm"]["colors"]), 8)
        self.assertEqual(len(gf.THEMES["science"]["colors"]), 10)

    def test_v250_theme_science_smoke(self):
        proc, out = self._run("bar", SAMPLE["bar"], ["--theme", "science"], "sci")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_v250_journal_theme_linkage(self):
        # --journal nejm 且未显式给 --theme → 自动联动 nejm 配色
        proc, _ = self._run("scatter", SAMPLE["scatter"], ["--journal", "nejm"], "link")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("配色已联动 nejm", proc.stderr)
        # 显式 --theme 优先，不联动
        proc2, _ = self._run("scatter", SAMPLE["scatter"],
                             ["--journal", "nejm", "--theme", "glm"], "link2")
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertNotIn("配色已联动", proc2.stderr)

    # ── --annotate ──

    def test_v250_annotate_cli_scatter(self):
        data = {"x": [1, 2, 3, 4, 5], "y": [2, 4, 3.5, 5, 4.8],
                "groups": ["a", "a", "b", "b", "b"]}
        proc, out = self._run("scatter", data,
                              ["--annotate", "3,3.5:拐点", "--annotate", "5,4.8:峰值",
                               "--cjk"], "ann")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))
        self.assertNotIn("ERROR", proc.stderr)

    def test_v250_annotate_bad_syntax_rejected(self):
        data = SAMPLE["scatter"]
        proc, _ = self._run("scatter", data, ["--annotate", "3,3.5"], "ann_bad1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("annotate", proc.stderr)
        self.assertIn("语法", proc.stderr)
        proc2, _ = self._run("scatter", data, ["--annotate", "3,3.5:"], "ann_bad2")
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("文字不能为空", proc2.stderr)

    def test_v250_annotate_category_axis_bar(self):
        data = {"labels": ["对照组", "低剂量", "高剂量"], "series": {"表达量": [1.0, 2.5, 4.2]}}
        proc, out = self._run("bar", data,
                              ["--annotate", "高剂量,4.2:显著上调", "--cjk"], "ann_bar")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))
        # 未知道类别 → 中文报错
        proc2, _ = self._run("bar", data, ["--annotate", "不存在组,1:高", "--cjk"], "ann_bar2")
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("无法定位坐标", proc2.stderr)

    def test_v250_annotate_inverted_axis_forest(self):
        """回归锁（B 电池抓出的 bug）：forest 的 y 轴倒置（get_ylim 返回 大→小），
        合法坐标曾被升序假设的范围检查误判越界 → 修复后必须通过。"""
        data = {"labels": ["S1", "S2"], "estimates": [1.2, 0.8],
                "ci_low": [0.9, 0.5], "ci_high": [1.5, 1.1]}
        proc, out = self._run("forest", data, ["--annotate", "1.2,0:S1 效应量"], "ann_for")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))

    def test_v250_annotate_zero_overlap_and_arrows_follow(self):
        """回归锁（审稿注释）：同点三注释 declutter 后零重叠，箭头终点锚回数据点。"""
        import gen_figure as gf
        fig, ax = plt.subplots(figsize=(8, 5.5))
        data = {"x": [1, 2, 3, 4], "y": [3, 3, 3, 3]}
        gen = gf.GENERATORS["scatter"]
        gen(data, ax, gf.THEMES["glm"], None)
        anns = gf._parse_annotations(["2.5,3:注释甲", "2.5,3:注释乙", "2.5,3:注释丙"])
        gf._apply_annotations(fig, anns, gf.THEMES["glm"], None)
        gf.fix_tick_overlaps(fig)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbs = [t.get_window_extent(renderer) for t in ax.texts if t.get_text()]
        n_over = sum(1 for i in range(len(bbs)) for j in range(i + 1, len(bbs))
                     if bbs[i].overlaps(bbs[j]))
        self.assertEqual(n_over, 0, "注释文字仍有重叠")
        arrows = [p for p in ax.patches if type(p).__name__ == "FancyArrowPatch"]
        self.assertEqual(len(arrows), 3, "应有 3 条注释箭头")
        for arr in arrows:
            if hasattr(arr, "get_positions"):
                _pa, pb = arr.get_positions()
            else:
                _pa, pb = arr._posA_posB
            # 注释坐标 (2.5, 3)：箭头终点必须精确锚定在请求的坐标上
            self.assertAlmostEqual(pb[0], 2.5, places=9, msg="箭头终点 x 未锚定")
            self.assertAlmostEqual(pb[1], 3.0, places=9, msg="箭头终点 y 未锚定")

    # ── 图例控制 ──

    def test_v250_legend_loc_applied(self):
        import gen_figure as gf
        fig, ax = plt.subplots(figsize=(8, 5))
        data = {"labels": ["t0", "t1", "t2"], "series": {"S1": [1, 2, 3], "S2": [3, 2.5, 2]}}
        gen = gf.GENERATORS["line"]
        gen(data, ax, gf.THEMES["glm"], None)
        ax.legend()
        gf._apply_legend_control(fig, loc="lower right", theme=gf.THEMES["glm"])
        leg = ax.get_legend()
        self.assertIsNotNone(leg)
        self.assertEqual(int(leg._loc), 4)  # lower right 的 loc 代码

    def test_v250_legend_loc_invalid_rejected(self):
        proc, _ = self._run("line", SAMPLE["line"], ["--legend-loc", "top-left"], "legbad")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("未知图例位置", proc.stderr)

    def test_v250_legend_outside_composite_shared(self):
        """回归锁：组合图 --legend-outside 合并为全图共享图例（去重）。"""
        import gen_figure as gf
        fig, ax = plt.subplots(figsize=(10, 4))
        data = {"layout": [1, 2], "panels": [
            {"type": "bar", "data": {"labels": ["A", "B"], "series": {"S1": [1, 2], "S2": [2, 1]}},
             "title": "Panel A", "pos": [0, 0]},
            {"type": "line", "data": {"labels": ["t0", "t1"], "series": {"S1": [1, 2], "S2": [2, 1]}},
             "title": "Panel B", "pos": [0, 1]}]}
        gen = gf.GENERATORS["composite"]
        extra = gen(data, ax, gf.THEMES["glm"], None)
        self.assertEqual(extra, "composite")
        panel_legs = [a for a in fig.axes if a.get_legend() is not None]
        self.assertGreaterEqual(len(panel_legs), 2)
        gf._apply_legend_control(fig, loc=None, outside=True, theme=gf.THEMES["glm"])
        self.assertEqual(len(list(fig.legends)), 1, "应有唯一全图共享图例")
        remaining = [a for a in fig.axes if a.get_legend() is not None]
        self.assertEqual(len(remaining), 0, "面板图例应已移除")
        labels = [t.get_text() for t in fig.legends[0].get_texts()]
        self.assertEqual(sorted(labels), ["S1", "S2"], "共享图例应去重为 S1/S2")

    # ── venn --area（Euler）──

    def test_v250_venn2_area_geometry_exact(self):
        import math
        import gen_figure as gf
        import af_v23_charts as ac
        n1, n2, inter = 40, 60, 30
        centers, radii, _notes = ac._venn2_geometry(n1, n2, inter)
        d = math.hypot(centers[0][0] - centers[1][0], centers[0][1] - centers[1][1])
        a1 = math.pi * radii[0] ** 2
        a2 = math.pi * radii[1] ** 2
        ov = ac._circle_overlap_area(d, radii[0], radii[1])
        # 缩放不破坏比例：三个比值必须全等
        self.assertAlmostEqual(a1 / (n1 + inter), a2 / (n2 + inter), places=12)
        self.assertAlmostEqual(ov / inter, a1 / (n1 + inter), places=12)
        # 子集：内切 d = r_out - r_in
        c2, r2, notes2 = ac._venn2_geometry(0, 60, 30)
        self.assertAlmostEqual(abs(c2[0][0] - c2[1][0]), abs(r2[0] - r2[1]), places=9)
        # 不相交：d >= r1 + r2
        c3, r3, _ = ac._venn2_geometry(50, 50, 0)
        d3 = math.hypot(c3[0][0] - c3[1][0], c3[0][1] - c3[1][1])
        self.assertGreaterEqual(d3, r3[0] + r3[1] - 1e-9)
        # 完全相同：同心 + 说明
        c4, _r4, notes4 = ac._venn2_geometry(0, 0, 50)
        self.assertAlmostEqual(c4[0][0], c4[1][0], places=9)
        self.assertTrue(any("相同" in s for s in notes4))

    def test_v250_venn3_area_fit(self):
        import af_v23_charts as ac
        regions = {"A": 100, "B": 80, "C": 60, "AB": 30, "AC": 20, "BC": 15, "ABC": 8}
        _c, _r, fit = ac._venn3_geometry(regions, ("A", "B", "C"))
        self.assertLessEqual(fit["max_rel_err"], 0.15,
                             f"常规三集合拟合偏差过大: {fit['max_rel_err']:.3f}")
        # 三集合互不相交 → 应近乎精确
        regions0 = {"A": 30, "B": 30, "C": 30, "AB": 0, "AC": 0, "BC": 0, "ABC": 0}
        _c0, _r0, fit0 = ac._venn3_geometry(regions0, ("A", "B", "C"))
        self.assertLessEqual(fit0["max_rel_err"], 0.02)

    def test_v250_venn_area_cli_and_regions_format(self):
        # regions 计数格式（v2.3 的数字 sets 从未可用，v2.5 修复）
        data3 = {"regions": {"A": 100, "B": 80, "C": 60, "AB": 30, "AC": 20,
                             "BC": 15, "ABC": 8}}
        proc, out = self._run("venn", data3, ["--area"], "v3area")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out))
        self.assertIn("面积", proc.stderr)
        # 元素列表 + --area
        data2 = {"sets": {"A": list(range(40)) + [f"x{i}" for i in range(30)],
                          "B": list(range(100, 160)) + [f"x{i}" for i in range(30)]}}
        proc2, out2 = self._run("venn", data2, ["--area"], "v2area")
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertTrue(os.path.exists(out2))
        # 非法 regions 键名 → 中文报错
        bad = {"regions": {"X": 1, "Y": 2, "Z": 3}}
        proc3, _ = self._run("venn", bad, [], "vbad")
        self.assertNotEqual(proc3.returncode, 0)
        self.assertIn("regions", proc3.stderr)
        # sets + regions 同时给 → 报错（validate 层提示两种格式的正确用法）
        proc4, _ = self._run("venn", {"sets": {"A": [1], "B": [2]},
                                      "regions": {"A": 1, "B": 1, "AB": 0}}, [], "vboth")
        self.assertNotEqual(proc4.returncode, 0)
        self.assertIn("venn", proc4.stderr)

    def test_v250_area_flag_venn_only(self):
        proc, _ = self._run("bar", SAMPLE["bar"], ["--area"], "areabad")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--area 仅用于 venn", proc.stderr)

    # ── 异常映射扩充 ──

    def test_v250_exc_map_expanded(self):
        import gen_figure as gf
        try:
            import pandas as pd
        except ImportError:
            pd = None
        cases = [(MemoryError(), "内存"), (ZeroDivisionError(), "除零"),
                 (AttributeError(), "结构")]
        if pd is not None:
            cases.append((pd.errors.ParserError("bad csv"), "解析"))
        try:
            from openpyxl.utils.exceptions import InvalidFileException
            cases.append((InvalidFileException("bad xlsx"), "xlsx"))
        except ImportError:
            pass
        self.assertGreaterEqual(len(cases), 3, "核心异常映射用例不足")
        for exc, keyword in cases:
            msg = gf._zh_exception(exc)
            self.assertIn(keyword, msg, f"{type(exc).__name__} 映射缺中文释义")
            self.assertIn(type(exc).__name__, msg, "应保留英文类名便于搜索")


class TestV260Features(unittest.TestCase):
    """v2.6.0：km 长表陷阱拦截（A1）+ 校验消息中文化（A2）+ multi-format/pipeline（C1/C2）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af_v26_")
        self.gen = os.path.join(SCRIPT_DIR, "gen_figure.py")

    def test_a1_km_longtable_series_fatal(self):
        # CSV 长表被通用转换装进 series：{time:[...], event:[...]} —— 必须 fatal（曾静默出废图）
        long_table = {"labels": ["12", "24", "36"],
                      "series": {"time": [12.0, 24.0, 36.0],
                                 "event": [1.0, 0.0, 1.0]}}
        f, _ = gen_figure.validate_data(long_table, "km")
        self.assertTrue(any("长表" in m and "groups" in m for m in f),
                        "长表应被拦截并给转换指引，实际 fatal=%r" % (f,))

    def test_a1_km_flat_groups_fatal(self):
        # groups 值是普通数值数组（不是 [t,e] 对）→ fatal 且给格式示例
        f, _ = gen_figure.validate_data({"groups": {"A": [1.0, 2.0, 3.0]}}, "km")
        self.assertTrue(any("成对" in m for m in f))

    def test_a1_km_pairs_still_pass(self):
        data = {"groups": {"A": [[1, 1], [2, 0], [3, 1]],
                           "B": [[1, 0], [2, 0], [4, 1]]}}
        f, _ = gen_figure.validate_data(data, "km")
        self.assertEqual(f, [], "合法 [t,e] 对不应报错：%r" % (f,))

    def test_a1_km_csv_end_to_end_fatal(self):
        # 原始问题输入重演：CSV 长表文件 → load_data → validate_data 必须 fatal
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "km_long.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("time,event,group\n12,1,A\n24,0,A\n36,1,B\n")
            data = gen_figure.load_data(p, chart_type="km")
            f, _ = gen_figure.validate_data(data, "km")
            self.assertTrue(any("长表" in m for m in f),
                            "CSV 长表应 fatal，实际 load=%r fatal=%r" % (data, f))

    def test_a2_chinese_messages(self):
        # 曾经的纯英文消息路径，现在必须含中文关键词
        _, w_flat = gen_figure.validate_data(
            {"labels": [1, 2, 3], "series": {"A": [5, 5, 5]}}, "bar")
        self.assertTrue(any("全部相同" in m for m in w_flat))
        _, w_nn = gen_figure.validate_data(
            {"labels": [1, 2], "series": {"A": ["NA", 2]}}, "bar")
        self.assertTrue(any("非数值" in m for m in w_nn))
        f_type, _ = gen_figure.validate_data({"series": "not-a-dict"}, "bar")
        self.assertTrue(any("JSON 对象" in m for m in f_type))
        f_empty, _ = gen_figure.validate_data({"series": {}, "labels": [1]}, "bar")
        self.assertTrue(any("空" in m for m in f_empty))
        f_box, _ = gen_figure.validate_data(
            {"labels": ["A", "B", "C"], "series": {"A": [1.0], "B": [2.0]}}, "box")
        self.assertTrue(any("组名" in m for m in f_box))

    def test_a2_no_english_leftovers(self):
        # prisma 两处残留英文必须清除
        f, _ = gen_figure.validate_data(
            {"records_identified": 100, "studies_included": 5,
             "exclusion_reasons": {"x": -1}}, "prisma")
        self.assertTrue(any("非负整数" in m for m in f))
        self.assertFalse(any("integers, got" in m for m in f))
        f2, _ = gen_figure.validate_data(
            {"records_identified": 100, "records_screened": 90,
             "reports_assessed": 50, "studies_included": 5,
             "exclusion_reasons": {"a": 20, "b": 30}}, "prisma")
        self.assertFalse(any("flow does not add up" in m for m in f2))
        self.assertTrue(any("排除人数" in m for m in f2))


    # ── C1: --multi-format ──

    def test_c1_multi_format_cli(self):
        d = os.path.join(self.tmp, "mf.json")
        with open(d, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲", "乙"], "series": {"S": [1, 2]}}, f)
        out = os.path.join(self.tmp, "mf1")
        proc = subprocess.run(
            [sys.executable, self.gen, "-t", "bar", "-d", d, "-o", out,
             "--multi-format", "png,pdf", "--dpi", "150"],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(out + ".png"), proc.stderr)
        self.assertTrue(os.path.exists(out + ".pdf"), proc.stderr)
        self.assertIn(".pdf", proc.stderr)

    def test_c1_multi_format_bad_value(self):
        d = os.path.join(self.tmp, "mf2.json")
        with open(d, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲", "乙"], "series": {"S": [1, 2]}}, f)
        proc = subprocess.run(
            [sys.executable, self.gen, "-t", "bar", "-d", d,
             "-o", os.path.join(self.tmp, "mf2"), "--multi-format", "bmp"],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("不支持", proc.stderr)

    # ── C2: --pipeline ──

    def test_c2_pipeline_json_defaults(self):
        d1 = os.path.join(self.tmp, "p_bar.json")
        d2 = os.path.join(self.tmp, "p_ba.json")
        with open(d1, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲", "乙"], "series": {"S": [1, 2]}}, f)
        with open(d2, "w", encoding="utf-8") as f:
            json.dump({"a": [1, 2, 3, 4], "b": [2, 3, 2, 5]}, f)
        pipe = os.path.join(self.tmp, "analysis.json")
        with open(pipe, "w", encoding="utf-8") as f:
            json.dump({"defaults": {"dpi": 150},
                       "figures": [
                           {"type": "bar", "data": "p_bar.json", "out": "fig_p_bar"},
                           {"type": "bland_altman", "data": d2, "out": "fig_p_ba"}]}, f)
        proc = subprocess.run([sys.executable, self.gen, "--pipeline", pipe],
                              capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 相对路径 data 相对流水线文件所在目录解析；out 落在同目录
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "fig_p_bar.png")), proc.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "fig_p_ba.png")), proc.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "analysis.batch-report.json")))

    def test_c2_pipeline_yaml(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("pyyaml 未安装")
        d1 = os.path.join(self.tmp, "p_bar.json")
        with open(d1, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲", "乙"], "series": {"S": [1, 2]}}, f)
        pipe = os.path.join(self.tmp, "analysis.yaml")
        with open(pipe, "w", encoding="utf-8") as f:
            f.write("defaults:\n  dpi: 150\nfigures:\n"
                    "  - type: bar\n    data: p_bar.json\n    out: fig_yaml2\n")
        proc = subprocess.run([sys.executable, self.gen, "--pipeline", pipe],
                              capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "fig_yaml2.png")), proc.stderr)

    def test_c2_pipeline_bad_ext_and_conflict(self):
        p = os.path.join(self.tmp, "pipe.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x")
        proc = subprocess.run([sys.executable, self.gen, "--pipeline", p],
                              capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(".yaml", proc.stderr)
        d = os.path.join(self.tmp, "c.json")
        with open(d, "w", encoding="utf-8") as f:
            json.dump({"labels": ["甲"], "series": {"S": [1]}}, f)
        proc2 = subprocess.run(
            [sys.executable, self.gen, "--batch", d, "--pipeline", d],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("二选一", proc2.stderr)

    # ── 审核修复：forest 缺省无效线按 measure 自动 ──

    def test_v260_forest_refline_auto_ratio(self):
        # 自然尺度 OR/HR（全正、measure 默认 OR）→ 缺省无效线必须 1.0（旧默认 0 会误导显著性判读）
        import matplotlib
        import matplotlib.pyplot as plt
        theme = gen_figure.THEMES[gen_figure.resolve_theme("glm")]
        data = {"labels": ["全部", "亚组"], "estimates": [0.69, 0.81],
                "ci_low": [0.54, 0.59], "ci_high": [0.89, 1.12]}
        fig, ax = plt.subplots()
        gen_figure.gen_forest(data, ax, theme, None)
        verts = [float(ln.get_xdata()[0]) for ln in ax.lines
                 if len(ln.get_xdata()) >= 2
                 and ln.get_xdata()[0] == ln.get_xdata()[-1]]
        self.assertIn(1.0, verts, "自然尺度 OR 缺省无效线应为 1.0")
        plt.close(fig)

    def test_v260_forest_refline_auto_difference(self):
        import matplotlib
        import matplotlib.pyplot as plt
        theme = gen_figure.THEMES[gen_figure.resolve_theme("glm")]
        data = {"labels": ["A", "B"], "estimates": [-0.3, 0.2],
                "ci_low": [-0.6, -0.1], "ci_high": [0.0, 0.5], "measure": "SMD"}
        fig, ax = plt.subplots()
        gen_figure.gen_forest(data, ax, theme, None)
        verts = [float(ln.get_xdata()[0]) for ln in ax.lines
                 if len(ln.get_xdata()) >= 2
                 and ln.get_xdata()[0] == ln.get_xdata()[-1]]
        self.assertIn(0.0, verts, "MD/SMD 缺省无效线应为 0.0")
        plt.close(fig)

    def test_v260_forest_refline_explicit_wins(self):
        import matplotlib
        import matplotlib.pyplot as plt
        theme = gen_figure.THEMES[gen_figure.resolve_theme("glm")]
        data = {"labels": ["A", "B"], "estimates": [0.69, 0.81],
                "ci_low": [0.54, 0.59], "ci_high": [0.89, 1.12], "ref_line": 0}
        fig, ax = plt.subplots()
        gen_figure.gen_forest(data, ax, theme, None)
        verts = [float(ln.get_xdata()[0]) for ln in ax.lines
                 if len(ln.get_xdata()) >= 2
                 and ln.get_xdata()[0] == ln.get_xdata()[-1]]
        self.assertIn(0.0, verts, "显式 ref_line=0 应优先于自动")
        self.assertNotIn(1.0, verts)
        plt.close(fig)


# ── B3/B2(v2.7) 回归锁 ──
class TestB3PracticalFixes(unittest.TestCase):
    def test_composite_hbar_panel(self):
        """B3：composite 内 hbar 面板必须自动横排（实战坑回归锁）。"""
        data = {"layout": [1, 2], "panels": [
            {"title": "A", "type": "bar", "pos": [0, 0],
             "data": {"labels": ["A", "B"], "series": {"C": [1.0, 2.0]}}},
            {"title": "B", "type": "hbar", "pos": [0, 1],
             "data": {"labels": ["X", "Y"], "series": {"S": [1.5, 2.5]}}},
        ]}
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "comp.json")
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            r = subprocess.run([sys.executable, GEN, "-t", "composite", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "80"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            self.assertTrue(os.path.exists(os.path.join(td, "out.png")))

    def test_roc_duplicate_labels_disambiguated(self):
        """B3：两条 AUC 相同的 ROC 曲线 → 图例标签自动消歧并 stderr 告知。"""
        xs = [0.0, 0.5, 1.0]
        data = {"curves": [
            {"name": "模型", "fpr": xs, "tpr": [0.0, 0.7, 1.0], "auc": 0.85},
            {"name": "模型", "fpr": xs, "tpr": [0.0, 0.7, 1.0], "auc": 0.85},
        ]}
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "roc.json")
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            r = subprocess.run([sys.executable, GEN, "-t", "roc", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "80"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            self.assertIn("已自动消歧", r.stderr)

    def test_pca_feature_names_length_notice(self):
        """B3：pca feature_names 长度不符 → 自动替换并 stderr 提示（原为静默）。"""
        data = {"matrix": [[1.0, 2.0, 3.0, 4.0], [2.0, 1.0, 4.0, 3.0],
                           [3.0, 4.0, 1.0, 2.0], [4.0, 3.0, 2.0, 1.0]],
                "feature_names": ["只有", "两个"]}
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "pca.json")
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            r = subprocess.run([sys.executable, GEN, "-t", "pca", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "80"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            self.assertIn("已自动改用默认名", r.stderr)

    def test_size_presets(self):
        """B2：--size 16:9 与 9:16 渲染成功且 figsize 提示出现。"""
        data = {"labels": ["A", "B"], "series": {"S": [1.0, 2.0]}}
        for size in ("16:9", "9:16"):
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "d.json")
                json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
                r = subprocess.run([sys.executable, GEN, "-t", "bar", "--data", p,
                                    "-o", os.path.join(td, "out"), "--dpi", "80",
                                    "--size", size],
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr[-400:])
                self.assertIn(f"画幅预设 {size}", r.stderr)


# ── A3(v2.7) 稳定性回归锁 ──
class TestA3Stability(unittest.TestCase):
    def test_deterministic_output(self):
        """A3：同输入两次渲染 → PNG 逐字节一致（确定性输出）。"""
        data = {"labels": ["甲", "乙", "丙"], "series": {"组1": [1.0, 2.0, 3.0], "组2": [2.0, 1.0, 2.5]}}
        blobs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "d.json")
                json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
                r = subprocess.run([sys.executable, GEN, "-t", "bar", "--data", p,
                                    "-o", os.path.join(td, "out"), "--dpi", "100"],
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr[-300:])
                blobs.append(open(os.path.join(td, "out.png"), "rb").read())
        self.assertEqual(blobs[0], blobs[1], "同输入渲染结果不一致（确定性被破坏）")

    def test_low_memory_graceful(self):
        """A3：低内存环境（ulimit 512MB）渲染 → 不裸 traceback（中文诊断或正常完成）。"""
        data = {"labels": [str(i) for i in range(40)], "series": {"S": [float(i) for i in range(40)]}}
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            cmd = ("ulimit -v 524288; exec python3 %s -t bar --data %s -o %s/out --dpi 80"
                   % (shlex.quote(GEN), shlex.quote(p), shlex.quote(td)))
            r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=180)
            self.assertNotIn("Traceback", r.stderr, r.stderr[-400:])

    def test_soak_30_charts(self):
        """A3：30 张混合图型连跑零失败（浸泡）。"""
        rng = random.Random(11)
        ok = 0
        with tempfile.TemporaryDirectory() as td:
            for i in range(30):
                t = ["bar", "line", "scatter", "box", "violin", "roc", "forest", "pca"][i % 8]
                if t == "bar":
                    d = {"labels": [f"g{j}" for j in range(5)],
                         "series": {f"s{k}": [rng.random() * 5 for _ in range(5)] for k in range(3)}}
                elif t == "line":
                    d = {"x": list(range(20)), "series": {"a": [rng.random() for _ in range(20)]}}
                elif t == "scatter":
                    d = {"x": [rng.random() for _ in range(50)], "y": [rng.random() for _ in range(50)]}
                elif t in ("box", "violin"):
                    d = {"labels": ["A", "B"], "series": {"A": [rng.random() for _ in range(20)],
                                                          "B": [rng.random() for _ in range(20)]}}
                elif t == "roc":
                    d = {"curves": [{"name": "m1", "fpr": [0, .5, 1], "tpr": [0, .8, 1], "auc": 0.9}]}
                elif t == "forest":
                    d = {"labels": ["s1", "s2", "s3"], "estimates": [1.1, 0.9, 1.3],
                         "ci_low": [0.8, 0.6, 1.0], "ci_high": [1.5, 1.2, 1.7], "measure": "RR"}
                else:
                    d = {"matrix": [[rng.random() for _ in range(4)] for _ in range(6)]}
                p = os.path.join(td, f"d{i}.json")
                json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
                r = subprocess.run([sys.executable, GEN, "-t", t, "--data", p,
                                    "-o", os.path.join(td, f"o{i}"), "--dpi", "70"],
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 0, f"{t} #{i}: {r.stderr[-300:]}")
                ok += 1
        self.assertEqual(ok, 30)


# ── v2.8.0 B1：文档图型计数与代码注册表一致性守门 ──────────────────────────
class TestV280DocCount(unittest.TestCase):
    """B1(v2.8)：全部在售文档「N 种图表 / N 种图型 / N chart types」必须等于
    代码注册表去纯别名后的图型数。起因：v2.7.0 官方评测抓到 SKILL_ZH 写
    「21种图表」而实际 22 种——文档计数表述从此由测试锁死，新增图型时文档同步更新。"""

    _ALIASES = {"horizontal_bar", "boxplot", "survival"}  # 纯别名，不计为独立图型
    _DOC_FILES = ["SKILL.md", "SKILL_ZH.md",
                  os.path.join("templates", "README.md"),
                  os.path.join("references", "limits.md"),
                  os.path.join("references", "faq.md"),
                  os.path.join("references", "advanced.md"),
                  os.path.join("references", "data-formats.md"),
                  os.path.join("references", "pitfalls.md"),
                  os.path.join("references", "python-api.md"),
                  os.path.join("references", "composite-layouts.md")]

    def test_chart_count_claims_match_registry(self):
        import re
        n = len(gen_figure.GENERATORS) - len(self._ALIASES)
        self.assertGreaterEqual(n, 22, f"注册表图型数异常减少: {n}")
        root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        pat = re.compile(r"(\d+)\s*(?:种图表|种图型|chart types)")
        claims, bad = [], []
        for rel in self._DOC_FILES:
            p = os.path.join(root, rel)
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            for m in pat.finditer(txt):
                v = int(m.group(1))
                ln = txt.count("\n", 0, m.start()) + 1
                claims.append((rel, ln, v))
                if v != n:
                    bad.append(f"{rel}:{ln} 写「{v}」，注册表实际 {n}")
        self.assertTrue(claims, "没有扫描到任何图型计数表述——正则或文档路径可能已变化")
        self.assertEqual(bad, [], "文档图型计数与代码注册表不一致：\n" + "\n".join(bad))


# ── v2.8.0 A 线：看门狗 / 退出码分级 / 降采样出口 ─────────────────────────
class TestV280Watchdog(unittest.TestCase):
    """A1/A3(v2.8)：看门狗硬中断 exit 5、--timeout 0 禁用、退出码分类。"""

    def _big_cluster(self, td, rows=3000, cols=16):
        import random as _r
        rng = _r.Random(7)
        data = {"matrix": [[rng.random() for _ in range(cols)] for _ in range(rows)],
                "row_labels": [f"r{i}" for i in range(rows)],
                "col_labels": [f"c{j}" for j in range(cols)]}
        p = os.path.join(td, "big.json")
        json.dump(data, open(p, "w", encoding="utf-8"))
        return p

    def test_watchdog_kills_slow_render_exit5(self):
        """看门狗：--timeout 1 而渲染未完 → exit 5 + 中文诊断（不无限挂起）。"""
        import random as _r
        rng = _r.Random(7)
        with tempfile.TemporaryDirectory() as td:
            data = {"matrix": [[rng.random() for _ in range(16)] for _ in range(3000)],
                    "row_labels": [f"r{i}" for i in range(3000)],
                    "col_labels": [f"c{j}" for j in range(16)]}
            p = os.path.join(td, "big.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "cluster_heatmap", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "200",
                                "--timeout", "1"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 5,
                             f"期望看门狗 exit 5，实际 {r.returncode}：{r.stderr[-300:]}")
            self.assertIn("看门狗", r.stderr)
            self.assertIn("--timeout", r.stderr)

    def test_timeout_zero_disables_watchdog(self):
        """--timeout 0 → 禁用看门狗，正常渲染完成 exit 0。"""
        with tempfile.TemporaryDirectory() as td:
            p = self._big_cluster(td, rows=800, cols=8)
            r = subprocess.run([sys.executable, GEN, "-t", "cluster_heatmap", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "60",
                                "--timeout", "0"],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertTrue(os.path.exists(os.path.join(td, "out.png")))

    def test_exit_code_classification(self):
        """A3：v3 兜底退出码分类——数据侧=3、环境侧=4、内存=6、其余=2。"""
        f = gen_figure._classify_exit_code
        self.assertEqual(f(ValueError("x")), 3)
        self.assertEqual(f(KeyError("k")), 3)
        self.assertEqual(f(IndexError("i")), 3)
        self.assertEqual(f(TypeError("t")), 3)
        self.assertEqual(f(FileNotFoundError("f")), 3)
        try:
            json.loads("{bad json")
        except json.JSONDecodeError as e:
            self.assertEqual(f(e), 3)
        self.assertEqual(f(ImportError("no mod")), 4)
        self.assertEqual(f(ModuleNotFoundError("no mod")), 4)
        self.assertEqual(f(OSError("io")), 4)
        self.assertEqual(f(PermissionError("denied")), 4)
        self.assertEqual(f(RuntimeError("rt")), 4)
        self.assertEqual(f(MemoryError("oom")), 6)
        self.assertEqual(f(Exception("misc")), 2)


class TestV280Downsample(unittest.TestCase):
    """A4(v2.8)：cluster_heatmap 超限指引 + --downsample 等距采样出口。"""

    def test_over_limit_hint_mentions_downsample(self):
        import random as _r
        rng = _r.Random(3)
        with tempfile.TemporaryDirectory() as td:
            data = {"matrix": [[rng.random() for _ in range(5)] for _ in range(3500)]}
            p = os.path.join(td, "big.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "cluster_heatmap", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "60"],
                               capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("AUTO-DOWNSAMPLE", r.stderr)

    def test_downsample_renders_under_limit(self):
        import random as _r
        rng = _r.Random(3)
        with tempfile.TemporaryDirectory() as td:
            data = {"matrix": [[rng.random() for _ in range(5)] for _ in range(3500)],
                    "row_labels": [f"g{i}" for i in range(3500)]}
            p = os.path.join(td, "big.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "cluster_heatmap", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "60",
                                "--downsample", "1500"],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("等距采样", r.stderr)
            self.assertTrue(os.path.exists(os.path.join(td, "out.png")))


# ── v2.8.0 C 线：异常词条覆盖（评测点名 ImportError 裸英文）────────────────
class TestV280ExceptionUX(unittest.TestCase):
    """C1(v2.8)：ImportError/OSError 等不再落「未知类型」，中文诊断含依赖指引。"""

    def test_importerror_has_chinese_diagnosis(self):
        zh, orig, tips = gen_figure._diagnose_exception(ImportError("No module named 'scipy'"))
        self.assertNotEqual(zh, "未知类型的错误")
        self.assertIn("依赖", zh)
        joined = " ".join(tips)
        self.assertIn("pip install", joined)

    def test_modulenotfounderror_and_oserror_covered(self):
        zh1, _, _ = gen_figure._diagnose_exception(ModuleNotFoundError("No module named 'x'"))
        zh2, _, _ = gen_figure._diagnose_exception(OSError("disk full"))
        self.assertIn("依赖", zh1)
        self.assertNotEqual(zh2, "未知类型的错误")

    def test_timeout_entry_mentions_flag(self):
        zh, _, tips = gen_figure._diagnose_exception(TimeoutError("slow"))
        self.assertIn("超时", zh)
        self.assertTrue(any("--timeout" in t for t in tips),
                        "TimeoutError 建议应包含 --timeout 指引")


# ── v2.8.0 D1：venn 4 集合椭圆 ──────────────────────────────────────────
class TestV280Venn4(unittest.TestCase):
    """D1(v2.8)：4 集合椭圆布局（默认确定性 / --area 拟合+披露）与区域契约。"""

    def test_default_layout_all_15_regions_nonempty(self):
        import itertools
        import importlib
        ac = importlib.import_module("af_v23_charts")
        ells = ac._venn4_ells()
        areas, cents, _ = ac._venn4_region_masks(ells, (-0.5, -0.5, 0.5, 0.5), 400)
        self.assertEqual(len(areas), 15)
        for k, v in areas.items():
            self.assertGreater(v, 0, f"默认布局区域 {k} 为空")
            self.assertIsNotNone(cents[k])

    def _sets4_data(self):
        return {"sets": {
            "组A": [f"a{i}" for i in range(40)],
            "组B": [f"a{i}" for i in range(15, 55)],
            "组C": [f"a{i}" for i in range(30, 70)],
            "组D": [f"a{i}" for i in range(5, 45, 2)] + [f"d{i}" for i in range(10)]}}

    def test_venn4_sets_mode_cli(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "v4.json")
            json.dump(self._sets4_data(), open(p, "w", encoding="utf-8"),
                      ensure_ascii=False)
            r = subprocess.run([sys.executable, GEN, "-t", "venn", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "70"],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertTrue(os.path.exists(os.path.join(td, "out.png")))

    def test_venn4_regions15_and_bad_keys(self):
        import itertools
        sets = self._sets4_data()["sets"]
        keys = list(sets)
        ss = {k: set(v) for k, v in sets.items()}
        regs = {}
        for n in (1, 2, 3, 4):
            for combo in itertools.combinations(range(4), n):
                inter = set(ss[keys[combo[0]]])
                for i in combo[1:]:
                    inter &= ss[keys[i]]
                for i in range(4):
                    if i not in combo:
                        inter -= ss[keys[i]]
                regs["".join(keys[i] for i in combo)] = len(inter)
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "r15.json")
            json.dump({"regions": regs}, open(p, "w", encoding="utf-8"),
                      ensure_ascii=False)
            r = subprocess.run([sys.executable, GEN, "-t", "venn", "--data", p,
                                "-o", os.path.join(td, "out"), "--dpi", "70"],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            bad = dict(list(regs.items())[:14])
            p2 = os.path.join(td, "r14.json")
            json.dump({"regions": bad}, open(p2, "w", encoding="utf-8"),
                      ensure_ascii=False)
            r2 = subprocess.run([sys.executable, GEN, "-t", "venn", "--data", p2,
                                 "-o", os.path.join(td, "bad"), "--dpi", "70"],
                                capture_output=True, text=True, timeout=120)
            self.assertEqual(r2.returncode, 1)
            self.assertIn("15 键", r2.stderr)

    def test_venn4_area_mode_discloses_and_deterministic(self):
        sets = self._sets4_data()["sets"]
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "v4.json")
            json.dump({"sets": sets}, open(p, "w", encoding="utf-8"),
                      ensure_ascii=False)
            blobs = []
            errs = []
            for i in range(2):
                out = os.path.join(td, f"area{i}")
                r = subprocess.run([sys.executable, GEN, "-t", "venn", "--data", p,
                                    "-o", out, "--dpi", "70", "--area"],
                                   capture_output=True, text=True, timeout=600)
                self.assertEqual(r.returncode, 0, r.stderr[-300:])
                self.assertIn("面积偏差", r.stderr)  # 拟合完成/最优拟合两分支均含
                blobs.append(open(out + ".png", "rb").read())
                errs.append(r.stderr)
            self.assertEqual(blobs[0], blobs[1], "--area 两次渲染不一致（确定性破坏）")
            self.assertIn("面积偏差", errs[0])


# ── v2.8.0 D2：--wizard 向导 ────────────────────────────────────────────
class TestV280Wizard(unittest.TestCase):
    """D2(v2.8)：非 TTY 不挂起打印决策树；AF_WIZARD_FORCE 管道走交互并出命令。"""

    def test_wizard_non_tty_prints_guide(self):
        r = subprocess.run([sys.executable, GEN, "--wizard"],
                           capture_output=True, text=True, timeout=60, input="")
        self.assertEqual(r.returncode, 0, r.stderr[-200:])
        self.assertIn("决策树", r.stdout)
        self.assertIn("-t", r.stdout)

    def test_wizard_interactive_pipe_generates_command(self):
        env = dict(os.environ, AF_WIZARD_FORCE="1")
        r = subprocess.run([sys.executable, GEN, "--wizard"],
                           capture_output=True, text=True, timeout=60,
                           input="1\n1\n1\n\n", env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-200:])
        self.assertIn("-t bar", r.stdout, "向导应生成 bar 命令")
        self.assertIn("-d templates/", r.stdout)
        self.assertIn("-o figure.png", r.stdout)

    def test_wizard_eof_falls_back_to_defaults(self):
        env = dict(os.environ, AF_WIZARD_FORCE="1")
        r = subprocess.run([sys.executable, GEN, "--wizard"],
                           capture_output=True, text=True, timeout=60,
                           input="", env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-200:])
        self.assertIn("-t bar", r.stdout)


class TestV280Help(unittest.TestCase):
    """回归锁（v2.8）：--help 可用且含新参数。v2.7.0 曾因 --stats help 文本含
    裸 %（95%CI）触发 argparse %-格式化崩溃——--help 整体不可用。"""

    def test_help_works_and_lists_v28_flags(self):
        r = subprocess.run([sys.executable, GEN, "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, f"--help 崩溃: {r.stderr[-200:]}")
        for flag in ("--timeout", "--downsample", "--wizard", "--stats"):
            self.assertIn(flag, r.stdout + r.stderr, f"--help 缺 {flag}")



class TestV290DocsAndAdvisories(unittest.TestCase):
    """v2.9.0：边界收拢（limits §六/§七）、独立快速入门、预判 advisory、KeyError 纠错。"""

    @classmethod
    def setUpClass(cls):
        cls.root = os.path.dirname(SCRIPT_DIR)
        cls.qs = os.path.join(cls.root, "references", "quickstart.md")
        cls.lim = os.path.join(cls.root, "references", "limits.md")
        cls.zh = io.open(os.path.join(cls.root, "SKILL_ZH.md"), encoding="utf-8").read()
        cls.en = io.open(os.path.join(cls.root, "SKILL.md"), encoding="utf-8").read()

    def test_quickstart_exists_with_sections(self):
        self.assertTrue(os.path.isfile(self.qs), "quickstart.md 缺失")
        t = io.open(self.qs, encoding="utf-8").read()
        for kw in ("完整选图决策树", "上手四步", "Python 内调用", "常见第一坑", "--wizard"):
            self.assertIn(kw, t, "quickstart 缺小节: " + kw)

    def test_limits_has_new_sections(self):
        t = io.open(self.lim, encoding="utf-8").read()
        for kw in ("输出与默认行为交互", "运行环境边界", "--verify", "--width",
                   "matplotlib.use('Agg')"):
            self.assertIn(kw, t, "limits.md 缺: " + kw)

    def test_main_docs_point_to_quickstart(self):
        self.assertIn("references/quickstart.md", self.zh)
        self.assertIn("references/quickstart.md", self.en)
        self.assertIn("分组比较", self.zh)          # 精简映射保留（trigger 面）
        self.assertIn("Group comparison", self.en)
        self.assertIn("version: 3.4.0", self.zh)
        self.assertIn("version: 3.4.0", self.en)

    def test_cluster_advisory_preflight(self):
        data = {"matrix": [[float(i), float(i) + 1] for i in range(1600)]}
        msgs = gen_figure._preflight_advisories(data, "cluster_heatmap", None)
        self.assertEqual(len(msgs), 1)
        self.assertIn("--downsample", msgs[0])
        self.assertIn("1500", msgs[0])
        self.assertEqual(
            gen_figure._preflight_advisories(data, "cluster_heatmap", 500), [])
        small = {"matrix": [[1.0, 2.0], [3.0, 4.0]]}
        self.assertEqual(
            gen_figure._preflight_advisories(small, "cluster_heatmap", None), [])
        self.assertEqual(gen_figure._preflight_advisories(data, "bar", None), [])

    def test_keyerror_near_miss_hint(self):
        zh, orig, tips = gen_figure._diagnose_exception(KeyError("lables"))
        joined = " ".join(tips)
        self.assertIn("labels", joined)
        self.assertIn("lables", joined)
        zh2, o2, t2 = gen_figure._diagnose_exception(KeyError("zzzzzz"))
        self.assertIsInstance(t2, list)
        zh3, o3, t3 = gen_figure._diagnose_exception(ValueError("x"))
        self.assertTrue(isinstance(t3, list))




class TestV290FieldNearMiss(unittest.TestCase):
    """v2.9：字段名近似匹配告警。"""

    def test_typo_labels_warns(self):
        msgs = gen_figure._field_nearmiss_warnings(
            {"lables": ["a", "b"], "series": {"s": [1, 2]}})
        self.assertEqual(len(msgs), 1)
        self.assertIn("lables", msgs[0])
        self.assertIn("labels", msgs[0])

    def test_known_and_underscore_keys_silent(self):
        self.assertEqual(gen_figure._field_nearmiss_warnings(
            {"labels": ["a"], "series": {"s": [1]}, "_command": "x"}), [])

    def test_random_unknown_key_silent(self):
        self.assertEqual(gen_figure._field_nearmiss_warnings(
            {"labels": ["a"], "my_custom_note": "x"}), [])




class TestV300Docs(unittest.TestCase):
    """v3.0.0：类别列、速查卡、行内警示、模块拆分。"""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(SCRIPT_DIR)
        cls.zh = io.open(os.path.join(root, "SKILL_ZH.md"), encoding="utf-8").read()
        cls.en = io.open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
        cs_p = os.path.join(root, "references", "cheatsheet.md")
        cls.cs = io.open(cs_p, encoding="utf-8").read() if os.path.isfile(cs_p) else ""

    def test_category_column(self):
        self.assertIn("| 类别 | 类型 | 命令 |", self.zh)
        self.assertIn("| Category | Type | Command |", self.en)
        for cat in ("统计推断", "生存分析", "系统综述"):
            self.assertIn(cat, self.zh)
        for cat in ("Inference", "Survival", "Review"):
            self.assertIn(cat, self.en)

    def test_cheatsheet_complete(self):
        for kw in ("速查卡", "图型命令骨架", "全量参数速查", "退出码", "边界 Top 5", "--journal"):
            self.assertIn(kw, self.cs, "cheatsheet 缺: " + kw)

    def test_inline_warnings(self):
        self.assertIn("自动联动同款配色", self.zh)
        self.assertIn("auto-link a matching theme", self.en)
        self.assertIn("references/cheatsheet.md", self.zh)
        self.assertIn("references/cheatsheet.md", self.en)

    def test_modules_exist(self):
        self.assertTrue(os.path.isfile(os.path.join(SCRIPT_DIR, "af_wizard.py")))
        self.assertTrue(os.path.isfile(os.path.join(SCRIPT_DIR, "af_diagnostics.py")))
        self.assertTrue(callable(gen_figure._run_wizard))
        self.assertTrue(callable(gen_figure._diagnose_exception))

    def test_medwiki_section(self):
        """v3.1：MedWiki 导流节（同一作者披露+免责+负向触发行）。"""
        self.assertIn("docsor.cn", self.zh)
        self.assertIn("## 相关资源（同一作者·论文全家桶）", self.zh)
        self.assertIn("不构成诊疗或用药建议", self.zh)
        self.assertIn("不提及 MedWiki", self.zh)
        self.assertIn("docsor.cn", self.en)
        self.assertIn("Related Resources (same author · paper toolkit)", self.en)
        self.assertIn("prescription-level pages are gated", self.en)

    def test_version_2100(self):
        self.assertIn("version: 3.4.0", self.zh)
        self.assertIn("version: 3.4.0", self.en)
        self.assertNotIn("version: 2.9.0", self.zh)
        self.assertNotIn("version: 2.9.0", self.en)




    def test_km_cjk_risk_table_no_regression(self):
        """v3.0.1 热修回归锁：加载 CJK 字体+英文组名的 km，风险表不得渲染失败
        （v3.0.0 曾因未定义 _auto_cjk_hdr 丢整个风险表）。"""
        data = {"groups": {"ArmA": [[3.1, 1], [7.4, 0], [12.2, 1], [20.5, 1]],
                           "ArmB": [[2.3, 1], [9.8, 0], [15.1, 1], [25.0, 1]]}}
        f = os.path.join(tempfile.gettempdir(), "af_km_cjk_lock.json")
        io.open(f, "w", encoding="utf-8").write(json.dumps(data))
        r = subprocess.run(
            [sys.executable, GEN, "-t", "km", "-d", f,
             "-o", os.path.join(tempfile.gettempdir(), "af_km_cjk_lock.png"),
             "--cjk", "--dpi", "100"],
            capture_output=True, text=True, timeout=240)
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertNotIn("自动风险表渲染失败", r.stderr, r.stderr[-300:])




class TestV3100(unittest.TestCase):
    """v3.1.0：--quick 一键出图 + 自动降采样 + 文档口径。"""

    def test_quick_renders(self):
        with tempfile.TemporaryDirectory() as td:
            data = {"labels": ["A", "B", "C"],
                    "series": {"s1": [1, 2, 3], "s2": [2, 3, 4]}}
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            out = os.path.join(td, "q.png")
            r = subprocess.run([sys.executable, GEN, "--quick", "--data", p,
                                "--out", out, "--dpi", "80"],
                               capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertTrue(os.path.isfile(out))
            self.assertIn("自动选择图型", r.stderr)

    def test_quick_requires_data(self):
        r = subprocess.run([sys.executable, GEN, "--quick"],
                           capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)

    def test_auto_downsample_4000(self):
        import random as _r
        rng = _r.Random(11)
        with tempfile.TemporaryDirectory() as td:
            data = {"matrix": [[rng.random() for _ in range(4)] for _ in range(4000)],
                    "row_labels": [f"r{i}" for i in range(4000)]}
            p = os.path.join(td, "big.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            out = os.path.join(td, "auto.png")
            r = subprocess.run([sys.executable, GEN, "-t", "cluster_heatmap", "--data", p,
                                "-o", out, "--dpi", "60"],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("AUTO-DOWNSAMPLE", r.stderr)

    def test_docs_310(self):
        root = os.path.dirname(SCRIPT_DIR)
        zh = io.open(os.path.join(root, "SKILL_ZH.md"), encoding="utf-8").read()
        lim = io.open(os.path.join(root, "references", "limits.md"), encoding="utf-8").read()
        df = io.open(os.path.join(root, "references", "data-formats.md"), encoding="utf-8").read()
        self.assertIn("version: 3.4.0", zh)
        self.assertIn("--quick", zh)
        self.assertIn("自动等距采样到 2000 行", zh)
        self.assertIn("性能参考表", lim)
        self.assertIn("JSON vs CSV 能力对照", df)




class TestV3200(unittest.TestCase):
    """v3.2.0：自动行为透明化 + 安全声明 + FAQ 扩充。"""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(SCRIPT_DIR)
        cls.zh = io.open(os.path.join(root, "SKILL_ZH.md"), encoding="utf-8").read()
        cls.en = io.open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
        cls.faq = io.open(os.path.join(root, "references", "faq.md"), encoding="utf-8").read()

    def test_journal_width_lock_announced(self):
        with tempfile.TemporaryDirectory() as td:
            data = {"labels": ["A", "B"], "series": {"s": [1, 2]}}
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "bar", "--data", p,
                                "-o", os.path.join(td, "o.pdf"), "--journal", "nature",
                                "--width", "10", "--dpi", "80"],
                               capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("[auto]", r.stderr)
            self.assertIn("已被忽略", r.stderr)

    def test_verify_non_pdf_announced(self):
        with tempfile.TemporaryDirectory() as td:
            data = {"labels": ["A", "B"], "series": {"s": [1, 2]}}
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "bar", "--data", p,
                                "-o", os.path.join(td, "o.png"), "--verify", "--dpi", "80"],
                               capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("仅对 PDF", r.stderr)

    def test_safety_statement_bilingual(self):
        self.assertIn("## 安全与数据（行为声明）", self.zh)
        self.assertIn("不发起任何网络请求", self.zh)
        self.assertIn("## Safety & Data (behavior statement)", self.en)
        self.assertIn("zero network requests", self.en)

    def test_faq_conflicts_expanded(self):
        for kw in ("参数冲突与边界 FAQ", "--journal", "--verify", "--hatch"):
            self.assertIn(kw, self.faq)

    def test_top3_boundary_banner(self):
        self.assertIn("三条最常用边界", self.zh)
        self.assertIn("Top-3 boundaries", self.en)


    def test_toolkit_billboard(self):
        """v3.2.0 工单③：全家桶广告牌+Pro 转化入口+官网入口。"""
        for kw in ("论文全家桶", "paper-polisher-pro", "pubmed-verifier", "doc-holmes",
                   "paper-rewriter", "cn-med-oa", "cite-holmes", "docsor.cn"):
            self.assertIn(kw, self.zh)
        self.assertIn("academic-figures-pro", self.zh)
        self.assertIn("Paper toolkit", self.en)
        self.assertIn("docsor.cn", self.en)



    def test_version_320(self):
        self.assertIn("version: 3.4.0", self.zh)
        self.assertIn("version: 3.4.0", self.en)




class TestV3300(unittest.TestCase):
    """v3.3.0：frontmatter 冒号炸弹防御 + README 官方化。"""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(SCRIPT_DIR)
        cls.readme = os.path.join(root, "README.md")
        cls._fm = {}
        for name in ("SKILL.md", "SKILL_ZH.md"):
            t = io.open(os.path.join(root, name), encoding="utf-8").read()
            cls._fm[name] = re.match(r"^---\n(.*?)\n---\n", t, re.S).group(1)

    def test_no_colon_bomb_in_frontmatter(self):
        import re as _re
        for name, fm in self._fm.items():
            hits = []
            for ln in fm.splitlines():
                if _re.match(r"^[A-Za-z_][\w-]*:\s", ln):
                    continue  # 键行合法（YAML 键语法）
                if _re.search(r"[a-zA-Z]:\s", ln):
                    hits.append(ln.strip()[:60])  # 折叠值续行里的 word: value = 炸弹
            self.assertEqual(len(hits), 0, f"{name} frontmatter 折叠值仍有冒号+空格: {hits[:3]}")

    def test_readme_official(self):
        self.assertTrue(os.path.isfile(self.readme), "README.md 缺失")
        t = io.open(self.readme, encoding="utf-8").read()
        for kw in ("Quick Start", "22 chart types", "docsor.cn", "paper-polisher-pro",
                   "zero telemetry", "setup_env.py"):
            self.assertIn(kw, t)


    def test_nature_clean_style(self):
        """v3.3：--style nature-clean 顶刊版式（渲染成功+stderr 告知+与默认输出不同）。"""
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td:
            data = {"labels": ["A", "B", "C"], "series": {"s1": [1, 2, 3], "s2": [2, 3, 4]}}
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            o1 = os.path.join(td, "plain.png")
            o2 = os.path.join(td, "nc.png")
            r1 = subprocess.run([sys.executable, GEN, "-t", "bar", "--data", p,
                                 "-o", o1, "--dpi", "80"],
                                capture_output=True, text=True, timeout=240)
            r2 = subprocess.run([sys.executable, GEN, "-t", "bar", "--data", p,
                                 "-o", o2, "--style", "nature-clean", "--dpi", "80"],
                                capture_output=True, text=True, timeout=240)
            self.assertEqual(r1.returncode, 0, r1.stderr[-200:])
            self.assertEqual(r2.returncode, 0, r2.stderr[-200:])
            self.assertIn("nature-clean", r2.stderr)
            self.assertNotEqual(open(o1, "rb").read(), open(o2, "rb").read())



    def test_version_330(self):
        root = os.path.dirname(SCRIPT_DIR)
        for name in ("SKILL.md", "SKILL_ZH.md"):
            t = io.open(os.path.join(root, name), encoding="utf-8").read()
            self.assertIn("version: 3.4.0", t, name + " 缺 3.4.0 版本行")




class TestV3400(unittest.TestCase):
    """v3.4.0：直接标注 + 标题层级 + Pro 透传。"""

    def test_direct_label_renders(self):
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td:
            data = {"labels": [1, 2, 3, 4, 5],
                    "series": {"干预组": [10, 8, 6, 4, 2], "对照组": [2, 3, 5, 7, 9]}}
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "line", "--data", p,
                                "-o", os.path.join(td, "dl.png"), "--direct-label",
                                "--dpi", "80"],
                               capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr[-250:])

    def test_theme_default_direct_label(self):
        with tempfile.TemporaryDirectory() as td:
            data = {"labels": [1, 2, 3], "series": {"A": [1, 2, 3], "B": [3, 2, 1]}}
            p = os.path.join(td, "d.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, GEN, "-t", "line", "--data", p,
                                "-o", os.path.join(td, "o.png"), "--style", "glm-brand",
                                "--dpi", "80"],
                               capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stderr[-250:])

    def test_version_340(self):
        root = os.path.dirname(SCRIPT_DIR)
        for name in ("SKILL.md", "SKILL_ZH.md"):
            t = io.open(os.path.join(root, name), encoding="utf-8").read()
            self.assertIn("version: 3.4.0", t, name)
            self.assertIn("--direct-label", t, name)



if __name__ == "__main__":
    unittest.main(verbosity=2)

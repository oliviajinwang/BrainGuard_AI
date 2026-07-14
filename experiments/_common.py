"""Shared metrics/bootstrap/plotting helpers for the SVM vs Random Forest vs
XGBoost comparison scripts. Built once against the lifestyle (binary) model
and reused unchanged for the clinical (3-class) model -- see
experiments/compare_lifestyle_models.py and experiments/compare_clinical_models.py.
"""

import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Categorical palette slots 1/2/3 from the dataviz skill's validated reference
# palette (references/palette.md) -- assigned in fixed order and held constant
# across every plot in both comparison scripts, never re-cycled per chart.
COLOR_XGB = "#2a78d6"  # slot 1 blue -- existing production baseline
COLOR_SVM = "#1baf7a"  # slot 2 aqua
COLOR_RF = "#eda100"  # slot 3 yellow
COLOR_MUTED = "#898781"  # muted ink -- diagonal / reference lines
COLOR_GRID = "#e1e0d9"
COLOR_INK = "#0b0b0b"
SEQUENTIAL_CMAP = "Blues"  # sequential single-hue ramp for confusion-matrix heatmaps

MODEL_ORDER = ["XGBoost", "SVM", "Random Forest"]
MODEL_COLORS = {"XGBoost": COLOR_XGB, "SVM": COLOR_SVM, "Random Forest": COLOR_RF}


def environment_manifest(extra: dict) -> dict:
    """Records package versions, git commit, and seeds alongside the metrics
    output so a later run (or a human) can tell whether a difference is a real
    model difference or just a changed environment."""
    import sklearn
    import xgboost
    import shap

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        commit = None

    return {
        "git_commit": commit,
        "python": sys.version.split()[0],
        "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "shap": shap.__version__,
        **extra,
    }


def save_manifest(manifest: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)


# --------------------------------------------------------------------------
# Binary (lifestyle) metrics
# --------------------------------------------------------------------------


def binary_metrics_at_threshold(y_true, y_prob, threshold: float) -> dict:
    y_pred = (np.asarray(y_prob) >= threshold).astype(int)
    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }


def binary_threshold_independent_metrics(y_true, y_prob) -> dict:
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }


def f2_optimal_threshold(y_true_train, oof_prob_train, beta: float = 2.0) -> float:
    """Recall-favoring threshold tuned on out-of-fold TRAINING predictions
    only (never test) -- mirrors exactly how production's lifestyle threshold
    (~0.05) was chosen in src/lifestyle_predictor.py."""
    precisions, recalls, thresholds = precision_recall_curve(y_true_train, oof_prob_train)
    f_beta = (1 + beta**2) * precisions * recalls / (beta**2 * precisions + recalls + 1e-9)
    best_idx = int(np.argmax(f_beta[:-1]))
    return float(thresholds[best_idx])


# --------------------------------------------------------------------------
# Multiclass (clinical) metrics
# --------------------------------------------------------------------------


def multiclass_metrics(y_true, y_prob, labels: list[int]) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.argmax(y_prob, axis=1)
    per_class = {}
    for lbl in labels:
        binary_true = (y_true == lbl).astype(int)
        binary_pred = (y_pred == lbl).astype(int)
        per_class[str(lbl)] = {
            "n_test": int((y_true == lbl).sum()),
            "precision": float(precision_score(binary_true, binary_pred, zero_division=0)),
            "recall": float(recall_score(binary_true, binary_pred, zero_division=0)),
            "f1": float(f1_score(binary_true, binary_pred, zero_division=0)),
        }
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)),
        "roc_auc_macro_ovr": float(
            roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro", labels=labels)
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "per_class": per_class,
    }


# --------------------------------------------------------------------------
# Paired bootstrap (primary robustness mechanism -- see plan: k-fold CV would
# refit SVM/RF per fold but XGBoost can't be refit, so CV would compare
# "variance shown" against "single frozen point" rather than the models
# themselves. Bootstrap resamples the fixed test set's *predictions*, which
# were already computed once per model, so it applies identically to a frozen
# pretrained model and freshly-trained ones.)
# --------------------------------------------------------------------------


def paired_bootstrap_binary(
    y_true, prob_dict: dict, n_resamples: int = 2000, random_state: int = 42, group_ids=None
) -> tuple[dict, dict]:
    """prob_dict: {model_name: y_prob array}, all computed on the SAME test
    rows. Returns (summary, win_rates) where summary[model][metric] has
    mean/ci_low/ci_high and win_rates[model] is the % of paired resamples
    where that model beat 'XGBoost' on roc_auc / pr_auc."""
    rng = np.random.RandomState(random_state)
    y_true = np.asarray(y_true)
    n = len(y_true)

    if group_ids is not None:
        group_ids = np.asarray(group_ids)
        unique_groups = np.unique(group_ids)

    samples = {name: {"roc_auc": [], "pr_auc": [], "brier": []} for name in prob_dict}

    for _ in range(n_resamples):
        if group_ids is not None:
            sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
            idx = np.concatenate([np.where(group_ids == g)[0] for g in sampled_groups])
        else:
            idx = rng.randint(0, n, size=n)

        yt = y_true[idx]
        if len(np.unique(yt)) < 2:
            continue  # degenerate resample (all one class) -- AUC undefined, skip

        for name, probs in prob_dict.items():
            p = np.asarray(probs)[idx]
            samples[name]["roc_auc"].append(roc_auc_score(yt, p))
            samples[name]["pr_auc"].append(average_precision_score(yt, p))
            samples[name]["brier"].append(brier_score_loss(yt, p))

    summary = _summarize_bootstrap_samples(samples)
    win_rates = _paired_win_rates(samples, baseline="XGBoost", metrics=["roc_auc", "pr_auc"])
    return summary, win_rates


def paired_bootstrap_multiclass(
    y_true, prob_dict: dict, labels: list[int], n_resamples: int = 2000, random_state: int = 42, group_ids=None
) -> tuple[dict, dict]:
    """Multiclass analogue of paired_bootstrap_binary: macro ROC-AUC (OVR) and
    macro-F1 per resample, plus the always-shown Converted-class (or any rare
    class) recall via `per_class_label`."""
    rng = np.random.RandomState(random_state)
    y_true = np.asarray(y_true)
    n = len(y_true)

    if group_ids is not None:
        group_ids = np.asarray(group_ids)
        unique_groups = np.unique(group_ids)

    samples = {name: {"roc_auc_macro_ovr": [], "f1_macro": [], "accuracy": []} for name in prob_dict}
    rare_class_recall = {name: [] for name in prob_dict}
    rare_label = labels[-1]  # convention: rarest/most-clinically-important class passed last

    for _ in range(n_resamples):
        if group_ids is not None:
            sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
            idx = np.concatenate([np.where(group_ids == g)[0] for g in sampled_groups])
        else:
            idx = rng.randint(0, n, size=n)

        yt = y_true[idx]
        if len(np.unique(yt)) < len(labels):
            continue  # a resample missing a whole class can't score macro-OVR AUC

        for name, probs in prob_dict.items():
            p = np.asarray(probs)[idx]
            pred = np.argmax(p, axis=1)
            samples[name]["accuracy"].append(accuracy_score(yt, pred))
            samples[name]["f1_macro"].append(f1_score(yt, pred, average="macro", zero_division=0, labels=labels))
            try:
                samples[name]["roc_auc_macro_ovr"].append(
                    roc_auc_score(yt, p, multi_class="ovr", average="macro", labels=labels)
                )
            except ValueError:
                continue
            rare_true = (yt == rare_label).astype(int)
            rare_pred = (pred == rare_label).astype(int)
            rare_class_recall[name].append(recall_score(rare_true, rare_pred, zero_division=0))

    summary = _summarize_bootstrap_samples(samples)
    for name in prob_dict:
        arr = np.array(rare_class_recall[name])
        summary.setdefault(name, {})[f"recall_class_{rare_label}"] = {
            "mean": float(arr.mean()) if len(arr) else float("nan"),
            "ci_low": float(np.percentile(arr, 2.5)) if len(arr) else float("nan"),
            "ci_high": float(np.percentile(arr, 97.5)) if len(arr) else float("nan"),
        }
    win_rates = _paired_win_rates(samples, baseline="XGBoost", metrics=["roc_auc_macro_ovr", "f1_macro"])
    return summary, win_rates


def _summarize_bootstrap_samples(samples: dict) -> dict:
    summary = {}
    for name, metric_dict in samples.items():
        summary[name] = {}
        for metric, vals in metric_dict.items():
            arr = np.array(vals)
            if len(arr) == 0:
                summary[name][metric] = {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
                continue
            summary[name][metric] = {
                "mean": float(arr.mean()),
                "ci_low": float(np.percentile(arr, 2.5)),
                "ci_high": float(np.percentile(arr, 97.5)),
            }
    return summary


def _paired_win_rates(samples: dict, baseline: str, metrics: list[str]) -> dict:
    win_rates = {}
    if baseline not in samples:
        return win_rates
    for name in samples:
        if name == baseline:
            continue
        win_rates[name] = {}
        for metric in metrics:
            base_arr = np.array(samples[baseline][metric])
            chal_arr = np.array(samples[name][metric])
            m = min(len(base_arr), len(chal_arr))
            if m == 0:
                win_rates[name][f"{metric}_beats_xgb_pct"] = float("nan")
                continue
            win_rates[name][f"{metric}_beats_xgb_pct"] = float((chal_arr[:m] > base_arr[:m]).mean() * 100)
    return win_rates


# --------------------------------------------------------------------------
# Plotting
# --------------------------------------------------------------------------


def _style_axes(ax):
    ax.grid(True, color=COLOR_GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(COLOR_MUTED)
    ax.tick_params(colors=COLOR_INK)


def plot_roc_curve_binary(y_true, prob_dict: dict, save_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    for name in MODEL_ORDER:
        if name not in prob_dict:
            continue
        fpr, tpr, _ = roc_curve(y_true, prob_dict[name])
        auc = roc_auc_score(y_true, prob_dict[name])
        ax.plot(fpr, tpr, color=MODEL_COLORS[name], linewidth=2, label=f"{name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], color=COLOR_MUTED, linewidth=1, linestyle="--", label="Chance")
    ax.set_xlabel("False Positive Rate", color=COLOR_INK)
    ax.set_ylabel("True Positive Rate", color=COLOR_INK)
    ax.set_title(title, color=COLOR_INK)
    _style_axes(ax)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_calibration_curve_binary(y_true, prob_dict: dict, save_path: Path, title: str, n_bins: int = 10) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    max_val = 0.0
    for name in MODEL_ORDER:
        if name not in prob_dict:
            continue
        frac_pos, mean_pred = calibration_curve(y_true, prob_dict[name], n_bins=n_bins, strategy="quantile")
        ax.plot(mean_pred, frac_pos, marker="o", markersize=8, color=MODEL_COLORS[name], linewidth=2, label=name)
        max_val = max(max_val, float(np.max(frac_pos)), float(np.max(mean_pred)))
    # Zoom to the data's actual range instead of a fixed 0-1 axis -- on a low
    # base-rate problem (e.g. ~4.6% positive) every curve otherwise collapses
    # into the bottom-left corner and the calibration quality is unreadable.
    axis_max = min(1.0, max(0.1, max_val * 1.2))
    ax.plot([0, axis_max], [0, axis_max], color=COLOR_MUTED, linewidth=1, linestyle="--", label="Perfectly calibrated")
    ax.set_xlim(0, axis_max)
    ax.set_ylim(0, axis_max)
    ax.set_xlabel("Mean predicted probability", color=COLOR_INK)
    ax.set_ylabel("Observed frequency", color=COLOR_INK)
    ax.set_title(title, color=COLOR_INK)
    _style_axes(ax)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_confusion_matrices(
    y_true, pred_dict: dict, labels: list[int], class_names: list[str], save_path: Path, suptitle: str
) -> None:
    models = [m for m in MODEL_ORDER if m in pred_dict]
    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 4.5))
    if len(models) == 1:
        axes = [axes]
    for ax, name in zip(axes, models):
        cm = confusion_matrix(y_true, pred_dict[name], labels=labels)
        im = ax.imshow(cm, cmap=SEQUENTIAL_CMAP)
        ax.set_title(name, color=COLOR_INK)
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(class_names, rotation=30, ha="right", color=COLOR_INK)
        ax.set_yticklabels(class_names, color=COLOR_INK)
        ax.set_xlabel("Predicted", color=COLOR_INK)
        ax.set_ylabel("True", color=COLOR_INK)
        thresh = cm.max() / 2 if cm.max() else 0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(
                    j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > thresh else COLOR_INK,
                )
    fig.suptitle(suptitle, color=COLOR_INK)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_roc_curves_multiclass_ovr(
    y_true, prob_dict: dict, labels: list[int], class_names: list[str], save_path: Path, suptitle: str
) -> None:
    """One subplot per class, one-vs-rest ROC curve per model overlaid."""
    y_true = np.asarray(y_true)
    models = [m for m in MODEL_ORDER if m in prob_dict]
    fig, axes = plt.subplots(1, len(labels), figsize=(5 * len(labels), 5))
    if len(labels) == 1:
        axes = [axes]
    for ax, lbl, cname in zip(axes, labels, class_names):
        binary_true = (y_true == lbl).astype(int)
        for name in models:
            p = np.asarray(prob_dict[name])[:, lbl]
            fpr, tpr, _ = roc_curve(binary_true, p)
            auc = roc_auc_score(binary_true, p)
            ax.plot(fpr, tpr, color=MODEL_COLORS[name], linewidth=2, label=f"{name} (AUC={auc:.3f})")
        ax.plot([0, 1], [0, 1], color=COLOR_MUTED, linewidth=1, linestyle="--")
        ax.set_title(f"{cname} vs. rest", color=COLOR_INK)
        ax.set_xlabel("False Positive Rate", color=COLOR_INK)
        ax.set_ylabel("True Positive Rate", color=COLOR_INK)
        _style_axes(ax)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(suptitle, color=COLOR_INK)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_calibration_curves_multiclass_ovr(
    y_true, prob_dict: dict, labels: list[int], class_names: list[str], save_path: Path, suptitle: str, n_bins: int = 5
) -> None:
    y_true = np.asarray(y_true)
    models = [m for m in MODEL_ORDER if m in prob_dict]
    fig, axes = plt.subplots(1, len(labels), figsize=(5 * len(labels), 5))
    if len(labels) == 1:
        axes = [axes]
    for ax, lbl, cname in zip(axes, labels, class_names):
        binary_true = (y_true == lbl).astype(int)
        max_val = 0.0
        for name in models:
            p = np.asarray(prob_dict[name])[:, lbl]
            try:
                frac_pos, mean_pred = calibration_curve(binary_true, p, n_bins=n_bins, strategy="quantile")
            except ValueError:
                continue
            ax.plot(mean_pred, frac_pos, marker="o", markersize=8, color=MODEL_COLORS[name], linewidth=2, label=name)
            max_val = max(max_val, float(np.max(frac_pos)), float(np.max(mean_pred)))
        # Same zoom-to-data-range fix as plot_calibration_curve_binary -- a
        # rare class (e.g. Converted) otherwise collapses into one corner.
        axis_max = min(1.0, max(0.1, max_val * 1.2))
        ax.plot([0, axis_max], [0, axis_max], color=COLOR_MUTED, linewidth=1, linestyle="--")
        ax.set_xlim(0, axis_max)
        ax.set_ylim(0, axis_max)
        ax.set_title(f"{cname} vs. rest", color=COLOR_INK)
        ax.set_xlabel("Mean predicted probability", color=COLOR_INK)
        ax.set_ylabel("Observed frequency", color=COLOR_INK)
        _style_axes(ax)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(suptitle, color=COLOR_INK)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor="white")
    plt.close(fig)


def print_section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)

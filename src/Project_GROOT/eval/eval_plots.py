"""Plotting helpers for Project GROOT rollout evaluation."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")
except ImportError:
    plt = None
    logger.info("Warning: matplotlib not installed. Plots will not be generated.")


def plot_hist_with_mean(
    data: list[float],
    xlabel: str,
    ylabel: str,
    title: str,
    mean_fmt: str,
    mean_unit: str,
    color: str,
    path: object,
) -> None:
    """Save a histogram with a mean reference line."""
    if plt is None:
        return
    mean_val = np.mean(data)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(data, bins=20, edgecolor="black", alpha=0.7, color=color)
    ax.axvline(
        mean_val,
        color="red",
        linestyle="--",
        label=f"Mean: {mean_val:{mean_fmt}}{mean_unit}",
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def plot_line_with_mean(
    data: list[float],
    xlabel: str,
    ylabel: str,
    title: str,
    path: object,
) -> None:
    """Save a line plot with a mean reference line."""
    if plt is None:
        return
    mean_val = np.mean(data)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(data, marker="o", markersize=4, alpha=0.6)
    ax.axhline(
        mean_val,
        color="red",
        linestyle="--",
        label=f"Mean: {mean_val:.3f}",
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def plot_scatter(
    x: list[float],
    y: list[float],
    xlabel: str,
    ylabel: str,
    title: str,
    path: object,
) -> None:
    """Save a scatter plot."""
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x, y, alpha=0.6)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

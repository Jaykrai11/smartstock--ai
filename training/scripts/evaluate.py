"""Forecast accuracy + interval-calibration metrics."""
import numpy as np


def mae(y, f): return float(np.mean(np.abs(y - f)))
def rmse(y, f): return float(np.sqrt(np.mean((y - f) ** 2)))
def wape(y, f): return float(np.abs(y - f).sum() / max(np.abs(y).sum(), 1e-9))
def bias(y, f): return float((f - y).sum() / max(y.sum(), 1e-9))          # >0 = over-forecast
def smape(y, f):
    d = np.abs(y) + np.abs(f)
    return float(np.mean(np.where(d == 0, 0.0, 2 * np.abs(y - f) / np.where(d == 0, 1, d))))


def all_metrics(y, f):
    y, f = np.asarray(y, float), np.asarray(f, float)
    return dict(MAE=mae(y, f), RMSE=rmse(y, f), WAPE=wape(y, f), sMAPE=smape(y, f), bias=bias(y, f))


def coverage(y, q):  # share of actuals <= predicted quantile
    return float(np.mean(np.asarray(y) <= np.asarray(q)))


def pinball(y, q, alpha):
    d = np.asarray(y) - np.asarray(q)
    return float(np.mean(np.maximum(alpha * d, (alpha - 1) * d)))

/**
 * @fileoverview API client & core utilities for AI Content Factory Studio
 * @module api-client
 */

"use strict";

/**
 * @type {Record<string, unknown>}
 */
export const state = {
  projects: [],
  selectedId: null,
  pollTimer: null,
  activeTab: "script",
  agents: null,
  styles: [],
  currentAnalysis: null,
};

/**
 * DOM element accessor
 * @param {string} id
 * @returns {Element | null}
 */
export function $(id) {
  return document.getElementById(id);
}

/**
 * API client with JSON error handling
 * @param {string} path
 * @param {RequestInit} [options]
 * @returns {Promise<unknown>}
 */
export async function api(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const isText = options.responseType === "text";
  const res = await fetch(path, {
    ...(isForm ? {} : { headers: { "Content-Type": "application/json" } }),
    ...options,
  });

  if (isText) {
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return await res.text();
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* no JSON body */
  }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `HTTP ${res.status}`;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return body;
}

/**
 * Escape HTML entities
 * @param {unknown} value
 * @returns {string}
 */
export function esc(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

/**
 * Format timestamp
 * @param {string | number | Date | null | undefined} value
 * @returns {string}
 */
export function fmtTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}

/**
 * Format status label
 * @param {string | undefined} status
 * @returns {string}
 */
export function statusLabel(status) {
  return (status || "").replace(/_/g, " ");
}

/**
 * Toast notification system
 * @param {string} message
 * @param {("success" | "error" | "info")} [type="info"]
 */
export function showToast(message, type = "info") {
  const container = $("#toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "✕" : "ℹ"}</span> <span>${esc(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/**
 * Health & service catalog refresh
 */
export async function refreshHealth() {
  try {
    const h = await api("/health");
    const badge = $("#health");
    badge.textContent = `${h.status} · v${h.version}`;
    badge.className = `badge ${h.status === "ok" ? "ok" : "err"}`;
    if (h.providers) {
      const pNames = Object.entries(h.providers)
        .map(([k, v]) => `${k}: ${v}`)
        .join(" | ");
      badge.title = `Providers: ${pNames}`;
    }
  } catch {
    const badge = $("#health");
    badge.textContent = "offline";
    badge.className = "badge err";
    badge.title = "Backend API unavailable";
  }
}

/**
 * Run async function with error handling
 * @param {() => Promise<unknown>} fn
 */
export function run(fn) {
  fn().catch((err) => {
    showToast(err.message || "Operation failed", "error");
    hideError();
  });
}

/**
 * Show error in error box
 * @param {string} message
 */
export function showError(message) {
  const box = $("#error-box");
  if (!box) return;
  box.textContent = message;
  box.hidden = false;
}

/**
 * Hide error box
 */
export function hideError() {
  const box = $("#error-box");
  if (box) box.hidden = true;
}

/**
 * Format pluralized count
 * @param {number} count
 * @param {string} word
 * @returns {string}
 */
export function plural(count, word) {
  return `${count} ${word}${count !== 1 ? "s" : ""}`;
}
/**
 * console-error-utils.ts
 *
 * Shared utilities for tracking, categorizing, and asserting against
 * console errors, page errors, network failures, and specific error patterns.
 *
 * Usage:
 *   const tracker = createConsoleErrorTracker(page);
 *   // ... run test actions ...
 *   assertNoConsoleErrors(tracker, [ /some-allowed-pattern/ ]);
 *   console.log(tracker.getReport());
 */

import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type ConsoleSeverity = "error" | "warning" | "info" | "log" | "debug";

export interface TrackedError {
  type: "console" | "pageerror" | "requestfailed";
  severity: ConsoleSeverity;
  message: string;
  url?: string;
  timestamp: string;
  /** Normalised lower-case message for pattern matching */
  normalised: string;
}

export interface ConsoleTracker {
  /** All captured entries */
  errors: TrackedError[];
  /** Convenience accessor for warnings only */
  warnings: TrackedError[];
  /** Returns a human-readable report string */
  getReport: () => string;
  /** Returns entries matching a specific severity */
  bySeverity: (severity: ConsoleSeverity) => TrackedError[];
  /** Returns entries matching a given RegExp pattern */
  matching: (pattern: RegExp) => TrackedError[];
}

/* ------------------------------------------------------------------ */
/*  Severity helpers                                                   */
/* ------------------------------------------------------------------ */

const consoleSeverity = (type: string): ConsoleSeverity => {
  switch (type) {
    case "error":
      return "error";
    case "warning":
    case "warn":
      return "warning";
    case "info":
      return "info";
    case "debug":
      return "debug";
    default:
      return "log";
  }
};

/* ------------------------------------------------------------------ */
/*  Known-bad patterns                                                 */
/* ------------------------------------------------------------------ */

export const KNOWN_BAD_PATTERNS = [
  /counter\s*oscillation/i,
  /react\s*(error|warning|dom|fiber)/i,
  /undefined\s*(is\s*not|has\s*no)/i,
  /cannot\s*read\s*(property|properties)\s*of\s*(undefined|null)/i,
  /null\s*reference/i,
  /404\s*(not\s*found)?/i,
  /500\s*(internal\s*server\s*error)?/i,
  /failed\s*to\s*load\s*resource/i,
  /uncaught\s*(exception|error)/i,
  /unhandled\s*rejection/i,
  /chunk\s*load\s*error/i,
  /network\s*error/i,
  /hydration\s*mismatch/i,
  /invariant\s*violation/i,
  /typeerror\s*:\s*null/i,
  /typeerror\s*:\s*undefined/i,
];

/* ------------------------------------------------------------------ */
/*  Tracker factory                                                    */
/* ------------------------------------------------------------------ */

export function createConsoleErrorTracker(page: Page): ConsoleTracker {
  const errors: TrackedError[] = [];

  const push = (item: Omit<TrackedError, "normalised" | "timestamp">) => {
    const timestamp = new Date().toISOString();
    const normalised = item.message.toLowerCase();
    errors.push({ ...item, timestamp, normalised });
  };

  /* --- Console messages --- */
  page.on("console", (msg) => {
    const severity = consoleSeverity(msg.type());
    // Only capture errors and warnings by default, but keep info/debug
    // when they contain known-bad keywords so we don't miss silent failures.
    const text = msg.text();
    const hasBadKeyword = KNOWN_BAD_PATTERNS.some((re) => re.test(text));

    if (severity === "error" || severity === "warning" || hasBadKeyword) {
      push({
        type: "console",
        severity,
        message: text,
        url: page.url(),
      });
    }
  });

  /* --- Uncaught JS exceptions --- */
  page.on("pageerror", (err) => {
    push({
      type: "pageerror",
      severity: "error",
      message: err.message,
      url: page.url(),
    });
  });

  /* --- Failed network requests --- */
  page.on("requestfailed", (req) => {
    const failure = req.failure();
    const msg = failure
      ? `Network failure: ${req.method()} ${req.url()} — ${failure.errorText}`
      : `Network failure: ${req.method()} ${req.url()}`;
    push({
      type: "requestfailed",
      severity: "error",
      message: msg,
      url: req.url(),
    });
  });

  return {
    errors,

    get warnings() {
      return errors.filter((e) => e.severity === "warning");
    },

    getReport(): string {
      if (errors.length === 0) {
        return "✅ No console / network / page errors detected.\n";
      }

      const lines: string[] = [
        `⚠️  Captured ${errors.length} error(s) / warning(s):`,
        "",
      ];

      const grouped = errors.reduce<Record<string, TrackedError[]>>((acc, e) => {
        const key = `${e.type} | ${e.severity}`;
        acc[key] = acc[key] ?? [];
        acc[key].push(e);
        return acc;
      }, {});

      for (const [key, items] of Object.entries(grouped)) {
        lines.push(`--- ${key} (${items.length}) ---`);
        for (const it of items.slice(0, 10)) {
          const truncated =
            it.message.length > 300
              ? it.message.slice(0, 300) + " …"
              : it.message;
          lines.push(`  [${it.timestamp}] ${truncated}`);
        }
        if (items.length > 10) {
          lines.push(`  … and ${items.length - 10} more`);
        }
        lines.push("");
      }

      // Highlight known-bad pattern hits
      const badHits = errors.filter((e) =>
        KNOWN_BAD_PATTERNS.some((re) => re.test(e.normalised))
      );
      if (badHits.length > 0) {
        lines.push(
          `🚨 ${badHits.length} entries matched KNOWN_BAD_PATTERNS:`
        );
        for (const hit of badHits.slice(0, 5)) {
          lines.push(`   • ${hit.message.slice(0, 200)}`);
        }
        lines.push("");
      }

      return lines.join("\n");
    },

    bySeverity(severity: ConsoleSeverity) {
      return errors.filter((e) => e.severity === severity);
    },

    matching(pattern: RegExp) {
      return errors.filter((e) => pattern.test(e.message));
    },
  };
}

/* ------------------------------------------------------------------ */
/*  Assertion helper                                                   */
/* ------------------------------------------------------------------ */

export function assertNoConsoleErrors(
  tracker: ConsoleTracker,
  allowedPatterns: RegExp[] = []
): void {
  const disallowed = tracker.errors.filter((e) => {
    // If it matches any allowed pattern, skip it
    return !allowedPatterns.some((re) => re.test(e.message));
  });

  if (disallowed.length > 0) {
    const summary = disallowed
      .map(
        (d, i) =>
          `  ${i + 1}. [${d.type} | ${d.severity}] ${d.message.slice(0, 200)}`
      )
      .join("\n");

    expect(
      disallowed.length,
      `Expected 0 console / page / network errors, but found ${disallowed.length}:\n${summary}`
    ).toBe(0);
  }
}

/**
 * Soft assertion variant — logs but does not throw.
 * Use when you want to collect error data without failing the test immediately.
 */
export function logConsoleErrors(
  tracker: ConsoleTracker,
  allowedPatterns: RegExp[] = []
): boolean {
  const disallowed = tracker.errors.filter((e) => {
    return !allowedPatterns.some((re) => re.test(e.message));
  });

  if (disallowed.length > 0) {
    // eslint-disable-next-line no-console
    console.warn("\n" + tracker.getReport());
    return false;
  }
  return true;
}

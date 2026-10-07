import React, { useState } from "react";
import { MdClose, MdWarning, MdCheckCircle, MdInfo, MdOpenInNew } from "react-icons/md";
import { api } from "api";

export default function ReviewDrawer({ isOpen, onClose, transaction, onReviewed }) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !transaction) return null;

  const score = transaction.score || {
    risk_score: transaction.risk_score || 0,
    tier: transaction.tier || "LOW",
    reasons: transaction.reasons || [],
    contributions: transaction.contributions || [],
  };

  const getTierColor = (tier) => {
    switch (tier) {
      case "HIGH":
        return { text: "text-red-500", bg: "bg-red-50", border: "border-red-200", gauge: "#EE5D50" };
      case "MEDIUM":
        return { text: "text-amber-500", bg: "bg-amber-50", border: "border-amber-200", gauge: "#FFB547" };
      default:
        return { text: "text-green-500", bg: "bg-green-50", border: "border-green-200", gauge: "#05CD99" };
    }
  };

  const colors = getTierColor(score.tier);

  const handleAction = async (decision) => {
    if (!transaction.flag_id) {
      alert("This item does not have an active review flag.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.submitReview(transaction.flag_id, decision, note);
      if (onReviewed) onReviewed(transaction.flag_id, decision);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to submit review");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-navy-900/40 backdrop-blur-sm transition-opacity">
      <div className="relative h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-3xl dark:!bg-navy-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 pb-4 dark:border-navy-700">
          <div>
            <h3 className="text-xl font-bold text-navy-700 dark:text-white">Audit & Explainability</h3>
            <p className="text-sm font-medium text-gray-500">Ref: {transaction.firefly_group_id || transaction.id}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-navy-700 dark:hover:bg-navy-700 dark:hover:text-white"
          >
            <MdClose className="h-6 w-6" />
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Transaction Summary Card */}
        <div className="mt-5 rounded-2xl bg-[#F4F7FE] p-5 dark:!bg-navy-900">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Claim Amount</p>
              <h2 className="text-3xl font-extrabold text-navy-700 dark:text-white">
                ₹{Number(transaction.amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </h2>
            </div>
            <a
              href={`http://localhost:8080/transactions/show/${transaction.firefly_group_id}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 rounded-xl bg-white px-3 py-1.5 text-xs font-bold text-brand-500 shadow-sm hover:bg-gray-50 dark:bg-navy-800 dark:text-white"
            >
              Firefly Core <MdOpenInNew className="h-4 w-4" />
            </a>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-400">Employee:</span>
              <p className="font-bold text-navy-700 dark:text-white">{transaction.employee || "Alex Chen"}</p>
            </div>
            <div>
              <span className="text-gray-400">Category:</span>
              <p className="font-bold text-navy-700 dark:text-white">{transaction.category || "General"}</p>
            </div>
            <div>
              <span className="text-gray-400">Vendor:</span>
              <p className="font-bold text-navy-700 dark:text-white">{transaction.vendor || "Unknown"}</p>
            </div>
            <div>
              <span className="text-gray-400">Submission Date:</span>
              <p className="font-bold text-navy-700 dark:text-white">{transaction.date || "Today"}</p>
            </div>
          </div>
        </div>

        {/* Semi-Circle Risk Score Meter */}
        <div className="mt-6 flex flex-col items-center justify-center rounded-2xl border border-gray-100 p-6 shadow-sm dark:border-navy-700">
          <div className="relative flex flex-col items-center">
            {/* SVG Radial Arc */}
            <svg className="h-28 w-56" viewBox="0 0 200 100">
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#E2E8F0"
                strokeWidth="18"
                strokeLinecap="round"
              />
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke={colors.gauge}
                strokeWidth="18"
                strokeDasharray="251.2"
                strokeDashoffset={251.2 - (251.2 * (score.risk_score || 0)) / 100}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute bottom-0 text-center">
              <span className="text-3xl font-extrabold text-navy-700 dark:text-white">
                {Math.round(score.risk_score || 0)}
              </span>
              <span className="text-xs font-semibold text-gray-400"> / 100</span>
              <p className={`text-xs font-extrabold tracking-wider ${colors.text}`}>{score.tier} RISK TIER</p>
            </div>
          </div>
        </div>

        {/* Plain Language Reasons */}
        <div className="mt-6">
          <h4 className="flex items-center gap-2 text-base font-bold text-navy-700 dark:text-white">
            <MdInfo className="text-brand-500" /> Why was this flagged?
          </h4>
          <div className="mt-3 space-y-2">
            {(score.reasons && score.reasons.length > 0
              ? score.reasons
              : ["Transaction matched standard expenditure boundaries."]
            ).map((reason, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 rounded-xl bg-gray-50 p-3 text-sm font-medium text-navy-700 dark:bg-navy-900 dark:text-gray-200"
              >
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-brand-500 text-[10px] font-bold text-white">
                  {idx + 1}
                </span>
                <span>{reason}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Anomaly Contributions */}
        {score.contributions && score.contributions.length > 0 && (
          <div className="mt-6">
            <h4 className="text-base font-bold text-navy-700 dark:text-white">Feature Outlier Contributions</h4>
            <div className="mt-3 space-y-2.5">
              {score.contributions.map((c, i) => (
                <div key={i} className="text-xs">
                  <div className="mb-1 flex justify-between font-semibold">
                    <span className="text-gray-600 dark:text-gray-300">{c.name || c.feature}</span>
                    <span className="text-navy-700 dark:text-white">{c.impact}% Outlier Driver</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-900">
                    <div
                      className={`h-full rounded-full ${c.is_anomalous ? "bg-red-500" : "bg-brand-500"}`}
                      style={{ width: `${Math.min(100, c.impact)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Auditor Notes & Actions */}
        <div className="mt-8 rounded-2xl border border-gray-100 p-5 dark:border-navy-700">
          <label className="text-xs font-bold uppercase tracking-wider text-gray-500">Auditor Notes</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add justification or policy reference notes..."
            rows={3}
            className="mt-2 w-full rounded-xl border border-gray-200 bg-white p-3 text-sm text-navy-700 focus:border-brand-500 focus:outline-none dark:border-navy-600 dark:bg-navy-900 dark:text-white"
          />

          <div className="mt-4 flex gap-3">
            <button
              onClick={() => handleAction("confirmed")}
              disabled={submitting}
              className="flex-1 rounded-xl bg-red-600 py-3 text-sm font-bold text-white shadow-md hover:bg-red-700 disabled:opacity-50"
            >
              Confirm Anomaly (Fraud/Error)
            </button>
            <button
              onClick={() => handleAction("false_alarm")}
              disabled={submitting}
              className="flex-1 rounded-xl bg-emerald-600 py-3 text-sm font-bold text-white shadow-md hover:bg-emerald-700 disabled:opacity-50"
            >
              Mark False Alarm
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

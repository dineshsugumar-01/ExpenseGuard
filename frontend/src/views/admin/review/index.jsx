import React, { useEffect, useState } from "react";
import { MdWarning, MdCheckCircle, MdCancel, MdRefresh } from "react-icons/md";
import Card from "components/card";
import { api } from "api";
import ReviewDrawer from "views/admin/components/ReviewDrawer";

export default function ReviewQueueView() {
  const [flags, setFlags] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("open");
  const [loading, setLoading] = useState(true);
  const [selectedTx, setSelectedTx] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadFlags = async () => {
    try {
      setLoading(true);
      const res = await api.getFlags(statusFilter, page);
      setFlags(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to load review queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFlags();
  }, [page, statusFilter]);

  const handleQuickReview = async (e, flagId, decision) => {
    e.stopPropagation();
    try {
      await api.submitReview(flagId, decision, "Reviewed via Quick Queue");
      loadFlags();
    } catch (err) {
      alert("Failed to submit review: " + err.message);
    }
  };

  const handleRowClick = (item) => {
    setSelectedTx({
      ...item,
      score: {
        risk_score: item.risk_score,
        tier: item.tier,
        reasons: item.reasons,
        contributions: item.contributions,
      },
    });
    setIsDrawerOpen(true);
  };

  return (
    <div className="pt-2">
      {/* Header */}
      <div className="mb-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-navy-700 dark:text-white">Auditor Review Queue</h2>
          <p className="text-sm font-medium text-gray-400">
            {total} claims flagged for manual inspection. Decisions train the active model nightly.
          </p>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-xl bg-white p-1 shadow-sm dark:bg-navy-800">
            {["open", "confirmed", "false_alarm", "all"].map((s) => (
              <button
                key={s}
                onClick={() => {
                  setStatusFilter(s);
                  setPage(1);
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase transition-all ${
                  statusFilter === s
                    ? "bg-brand-500 text-white shadow-sm"
                    : "text-gray-500 hover:text-navy-700 dark:hover:text-white"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            ))}
          </div>
          <button
            onClick={loadFlags}
            className="rounded-xl bg-white p-2.5 text-brand-500 shadow-sm hover:bg-gray-50 dark:bg-navy-800 dark:text-white"
          >
            <MdRefresh className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main Review Cards List */}
      <div className="space-y-4">
        {loading ? (
          <Card extra="p-10 text-center text-gray-400">Loading audit queue...</Card>
        ) : flags.length === 0 ? (
          <Card extra="p-12 text-center">
            <h3 className="text-lg font-bold text-navy-700 dark:text-white">All Caught Up! 🎉</h3>
            <p className="mt-1 text-sm text-gray-400">No flags currently matching status '{statusFilter}'.</p>
          </Card>
        ) : (
          flags.map((item) => (
            <Card
              key={item.flag_id}
              extra="p-5 cursor-pointer hover:border-brand-500 transition-all border border-transparent"
              onClick={() => handleRowClick(item)}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                {/* Left Info */}
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-red-50 text-red-600 dark:bg-red-900/30">
                    <MdWarning className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-navy-700 dark:text-white">
                        ₹{Number(item.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                      <span className="text-sm font-semibold text-gray-400">• {item.vendor}</span>
                      <span className="rounded-lg bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-navy-900 dark:text-gray-300">
                        {item.category}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Filed by <strong>{item.employee}</strong> on {item.date} (Ref: {item.firefly_group_id})
                    </p>

                    {/* Explanations */}
                    <div className="mt-2.5 space-y-1">
                      {(item.reasons || []).slice(0, 2).map((r, i) => (
                        <p key={i} className="text-xs font-medium text-gray-600 dark:text-gray-300">
                          • {r}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Right Actions */}
                <div className="flex items-center gap-3 self-end lg:self-center">
                  <div className="text-right">
                    <span className="block text-xl font-black text-red-600 dark:text-red-400">
                      {Math.round(item.risk_score)}/100
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                      {item.tier} RISK
                    </span>
                  </div>

                  {item.flag_status === "open" ? (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleQuickReview(e, item.flag_id, "confirmed")}
                        className="rounded-xl bg-red-600 px-3 py-2 text-xs font-bold text-white shadow-sm hover:bg-red-700"
                      >
                        Confirm Anomaly
                      </button>
                      <button
                        onClick={(e) => handleQuickReview(e, item.flag_id, "false_alarm")}
                        className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700"
                      >
                        False Alarm
                      </button>
                    </div>
                  ) : (
                    <span className="rounded-xl bg-gray-100 px-3 py-1.5 text-xs font-bold uppercase text-gray-600 dark:bg-navy-900 dark:text-gray-300">
                      {item.flag_status.replace("_", " ")}
                    </span>
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Review Drawer */}
      <ReviewDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        transaction={selectedTx}
        onReviewed={() => loadFlags()}
      />
    </div>
  );
}

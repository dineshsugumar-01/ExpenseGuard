import React, { useEffect, useState } from "react";
import { MdSearch, MdFileDownload, MdFilterList, MdRefresh } from "react-icons/md";
import Card from "components/card";
import { api } from "api";
import ReviewDrawer from "views/admin/components/ReviewDrawer";

export default function TransactionsView() {
  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [tierFilter, setTierFilter] = useState("ALL");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedTx, setSelectedTx] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadTransactions = async () => {
    try {
      setLoading(true);
      const res = await api.getTransactions({
        page,
        limit: 15,
        tier: tierFilter,
        category: categoryFilter,
        q: search || undefined,
      });
      setTransactions(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to load transactions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [page, tierFilter, categoryFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadTransactions();
  };

  const getTierBadge = (tier, score) => {
    switch (tier) {
      case "HIGH":
        return <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-bold text-red-600 dark:bg-red-900/40 dark:text-red-400">{Math.round(score)} HIGH</span>;
      case "MEDIUM":
        return <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-600 dark:bg-amber-900/40 dark:text-amber-400">{Math.round(score)} MED</span>;
      default:
        return <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-bold text-green-600 dark:bg-green-900/40 dark:text-green-400">{Math.round(score)} LOW</span>;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "confirmed":
        return <span className="text-xs font-bold text-red-600 uppercase">Confirmed Anomaly</span>;
      case "false_alarm":
        return <span className="text-xs font-bold text-emerald-600 uppercase">False Alarm</span>;
      case "open":
        return <span className="text-xs font-bold text-amber-600 uppercase">Needs Audit</span>;
      default:
        return <span className="text-xs font-medium text-gray-400 uppercase">Cleared</span>;
    }
  };

  const handleRowClick = (tx) => {
    setSelectedTx({
      ...tx,
      score: {
        risk_score: tx.risk_score,
        tier: tx.tier,
        reasons: tx.reasons,
      },
    });
    setIsDrawerOpen(true);
  };

  return (
    <div className="pt-2">
      {/* Header & Filters */}
      <div className="mb-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-navy-700 dark:text-white">All Scored Transactions</h2>
          <p className="text-sm font-medium text-gray-400">Total Scored Records: {total.toLocaleString()}</p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="http://localhost:8000/api/transactions/export/csv"
            download
            className="flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-navy-700 shadow-md hover:bg-gray-50 dark:bg-navy-800 dark:text-white"
          >
            <MdFileDownload className="h-5 w-5" /> Export CSV
          </a>
          <button
            onClick={loadTransactions}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white shadow-md hover:bg-brand-600"
          >
            <MdRefresh className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Filter Toolbar Card */}
      <Card extra="p-4 mb-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="flex flex-1 items-center gap-2 min-w-[280px]">
            <div className="relative w-full">
              <MdSearch className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search vendor, employee, or reference ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-xl bg-[#F4F7FE] py-2 pl-10 pr-4 text-sm text-navy-700 outline-none placeholder:text-gray-400 dark:bg-navy-900 dark:text-white"
              />
            </div>
            <button type="submit" className="rounded-xl bg-brand-500 px-4 py-2 text-xs font-bold text-white">
              Search
            </button>
          </form>

          {/* Tier Pills */}
          <div className="flex items-center gap-1.5 rounded-xl bg-[#F4F7FE] p-1 dark:bg-navy-900">
            {["ALL", "LOW", "MEDIUM", "HIGH"].map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTierFilter(t);
                  setPage(1);
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold transition-all ${
                  tierFilter === t
                    ? "bg-white text-brand-500 shadow-sm dark:bg-navy-800 dark:text-white"
                    : "text-gray-500 hover:text-navy-700 dark:hover:text-white"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Transactions Table Card */}
      <Card extra="p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-100 text-xs font-bold uppercase tracking-wider text-gray-400 dark:border-navy-700">
                <th className="pb-3 pl-2">Vendor & Claim</th>
                <th className="pb-3">Employee</th>
                <th className="pb-3">Category</th>
                <th className="pb-3">Date</th>
                <th className="pb-3 text-right">Amount</th>
                <th className="pb-3 text-center">Risk Tier</th>
                <th className="pb-3 text-right pr-2">Review Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm font-medium text-navy-700 dark:divide-navy-700 dark:text-white">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-400">Loading transactions...</td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-400">No transactions match your filters.</td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    onClick={() => handleRowClick(tx)}
                    className="cursor-pointer hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
                  >
                    <td className="py-3.5 pl-2">
                      <p className="font-bold text-navy-700 dark:text-white">{tx.vendor}</p>
                      <p className="text-xs text-gray-400">{tx.firefly_group_id}</p>
                    </td>
                    <td className="py-3.5">{tx.employee}</td>
                    <td className="py-3.5">
                      <span className="rounded-lg bg-gray-100 px-2 py-1 text-xs text-gray-600 dark:bg-navy-900 dark:text-gray-300">
                        {tx.category}
                      </span>
                    </td>
                    <td className="py-3.5 text-xs text-gray-500">{tx.date}</td>
                    <td className="py-3.5 text-right font-bold tabular-nums">
                      ₹{Number(tx.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 text-center">
                      {getTierBadge(tx.tier, tx.risk_score)}
                    </td>
                    <td className="py-3.5 text-right pr-2">
                      {getStatusBadge(tx.flag_status)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="mt-5 flex items-center justify-between border-t border-gray-100 pt-4 dark:border-navy-700">
          <p className="text-xs text-gray-400">Page {page} of {Math.max(1, Math.ceil(total / 15))}</p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-200 disabled:opacity-40 dark:bg-navy-700 dark:text-white"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 15 >= total}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-200 disabled:opacity-40 dark:bg-navy-700 dark:text-white"
            >
              Next
            </button>
          </div>
        </div>
      </Card>

      {/* Review Drawer */}
      <ReviewDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        transaction={selectedTx}
        onReviewed={() => loadTransactions()}
      />
    </div>
  );
}

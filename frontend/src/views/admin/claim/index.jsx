import React, { useState } from "react";
import { MdAddCircle, MdCheckCircle, MdReceipt } from "react-icons/md";
import Card from "components/card";
import { api } from "api";

export default function ClaimSubmissionView() {
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("Travel");
  const [vendor, setVendor] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!amount || !vendor) {
      alert("Please provide amount and vendor.");
      return;
    }

    setSubmitting(true);
    setResult(null);

    const formData = new FormData();
    formData.append("description", description || `${category} expense at ${vendor}`);
    formData.append("amount", amount);
    formData.append("category", category);
    formData.append("vendor", vendor);
    formData.append("notes", notes);
    formData.append("source_account_id", 1);

    try {
      const res = await api.submitClaim(formData);
      setResult(res);
      // Reset form
      setDescription("");
      setAmount("");
      setVendor("");
      setNotes("");
    } catch (err) {
      alert("Submission failed: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="pt-2 max-w-2xl mx-auto">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-navy-700 dark:text-white">Submit Expense Claim</h2>
        <p className="text-sm font-medium text-gray-400">
          Claims are synced directly to Firefly III and evaluated automatically by ExpenseGuard.
        </p>
      </div>

      {result && (
        <Card extra="p-4 mb-5 bg-emerald-50 border border-emerald-200 dark:bg-emerald-900/20">
          <div className="flex items-center gap-2 text-sm font-bold text-emerald-700 dark:text-emerald-400">
            <MdCheckCircle className="h-5 w-5" /> {result.message}
          </div>
          {result.firefly_transaction_id && (
            <p className="mt-1 text-xs text-emerald-600">
              Firefly Core Transaction ID: <strong>{result.firefly_transaction_id}</strong>
            </p>
          )}
        </Card>
      )}

      <Card extra="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-gray-500">Expense Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-gray-200 bg-white p-3 text-sm text-navy-700 outline-none focus:border-brand-500 dark:border-navy-600 dark:bg-navy-900 dark:text-white"
            >
              <option value="Travel">Travel</option>
              <option value="Software">Software & Cloud</option>
              <option value="Meals & Entertainment">Meals & Entertainment</option>
              <option value="Hardware & Office">Hardware & Office</option>
              <option value="Consulting & Legal">Consulting & Legal</option>
              <option value="Telecommunications">Telecommunications</option>
              <option value="Training & Books">Training & Books</option>
            </select>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-gray-500">Amount (₹ INR)</label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 4500.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                className="mt-1.5 w-full rounded-xl border border-gray-200 bg-white p-3 text-sm font-bold text-navy-700 outline-none focus:border-brand-500 dark:border-navy-600 dark:bg-navy-900 dark:text-white"
              />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-gray-500">Vendor / Merchant</label>
              <input
                type="text"
                placeholder="e.g. IndiGo Airlines, AWS"
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                required
                className="mt-1.5 w-full rounded-xl border border-gray-200 bg-white p-3 text-sm text-navy-700 outline-none focus:border-brand-500 dark:border-navy-600 dark:bg-navy-900 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-gray-500">Short Description</label>
            <input
              type="text"
              placeholder="e.g. Flight for client kickoff meeting"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-gray-200 bg-white p-3 text-sm text-navy-700 outline-none focus:border-brand-500 dark:border-navy-600 dark:bg-navy-900 dark:text-white"
            />
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-gray-500">Audit Notes (Optional)</label>
            <textarea
              placeholder="Add any extra context or project allocation code..."
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-gray-200 bg-white p-3 text-sm text-navy-700 outline-none focus:border-brand-500 dark:border-navy-600 dark:bg-navy-900 dark:text-white"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white shadow-md hover:bg-brand-600 disabled:opacity-50"
          >
            <MdAddCircle className="h-5 w-5" />
            {submitting ? "Submitting to Firefly III..." : "Submit Claim"}
          </button>
        </form>
      </Card>
    </div>
  );
}

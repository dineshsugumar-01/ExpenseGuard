import React, { useEffect, useState } from "react";
import { MdAutoAwesome, MdRefresh, MdCheckCircle } from "react-icons/md";
import Card from "components/card";
import { api } from "api";

export default function ModelsView() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);

  const loadModels = async () => {
    try {
      setLoading(true);
      const res = await api.getModels();
      setModels(res || []);
    } catch (err) {
      console.error("Failed to load models:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainResult(null);
    try {
      const res = await api.triggerRetrain();
      setRetrainResult(res);
      await loadModels();
    } catch (err) {
      alert("Retraining failed: " + err.message);
    } finally {
      setRetraining(false);
    }
  };

  return (
    <div className="pt-2">
      {/* Header & Retrain Action */}
      <div className="mb-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-navy-700 dark:text-white">PyOD Anomaly Models & Retraining</h2>
          <p className="text-sm font-medium text-gray-400">
            Unsupervised Tabular Ensembles (ECOD + Isolation Forest) with Active Feedback Retraining.
          </p>
        </div>

        <button
          onClick={handleRetrain}
          disabled={retraining}
          className="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white shadow-md hover:bg-brand-600 disabled:opacity-50"
        >
          <MdAutoAwesome className={`h-4 w-4 ${retraining ? "animate-spin" : ""}`} />
          {retraining ? "Retraining Models..." : "Trigger Retrain Now"}
        </button>
      </div>

      {retrainResult && (
        <Card extra="p-4 mb-5 border border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20">
          <div className="flex items-center gap-2 text-sm font-bold text-emerald-700 dark:text-emerald-400">
            <MdCheckCircle className="h-5 w-5" /> Retraining Succeeded!
          </div>
          <p className="mt-1 text-xs text-emerald-600 dark:text-emerald-300">
            Version <strong>{retrainResult.version_tag}</strong> trained on {retrainResult.training_rows} samples.
            Excluded {retrainResult.confirmed_excluded} confirmed anomalies, included {retrainResult.false_alarms_included} false alarms.
          </p>
        </Card>
      )}

      {/* Models Versions Table */}
      <Card extra="p-5">
        <h4 className="text-lg font-bold text-navy-700 dark:text-white mb-4">Model Versions History</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-100 text-xs font-bold uppercase tracking-wider text-gray-400 dark:border-navy-700">
                <th className="pb-3 pl-2">Version Tag</th>
                <th className="pb-3">Trained At</th>
                <th className="pb-3 text-right">Training Rows</th>
                <th className="pb-3">Included Algorithms</th>
                <th className="pb-3 text-center">Contamination</th>
                <th className="pb-3 text-right pr-2">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm font-medium text-navy-700 dark:divide-navy-700 dark:text-white">
              {models.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-gray-400">
                    No persistent versions yet. Using default baseline ensemble (ECOD + IForest).
                  </td>
                </tr>
              ) : (
                models.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors">
                    <td className="py-3.5 pl-2 font-bold text-brand-500">{m.version_tag}</td>
                    <td className="py-3.5 text-xs text-gray-400">{m.trained_at.slice(0, 19).replace("T", " ")}</td>
                    <td className="py-3.5 text-right font-bold tabular-nums">
                      {m.training_rows.toLocaleString()}
                    </td>
                    <td className="py-3.5">
                      <div className="flex gap-1.5">
                        {(m.models_included || ["ecod", "iforest"]).map((algo) => (
                          <span key={algo} className="rounded-md bg-lightPrimary px-2 py-0.5 text-xs font-bold text-brand-500 dark:bg-navy-900">
                            {algo.toUpperCase()}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 text-center font-mono text-xs">{m.contamination}</td>
                    <td className="py-3.5 text-right pr-2">
                      {m.is_active ? (
                        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">Archived</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

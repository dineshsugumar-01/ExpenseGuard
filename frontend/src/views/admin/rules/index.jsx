import React, { useEffect, useState } from "react";
import { MdTune, MdCheck, MdSave, MdRefresh } from "react-icons/md";
import Card from "components/card";
import { api } from "api";

export default function RulesView() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  const loadRules = async () => {
    try {
      setLoading(true);
      const res = await api.getRules();
      setRules(res || []);
    } catch (err) {
      console.error("Failed to load rules:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleToggle = (ruleId) => {
    setRules((prev) =>
      prev.map((r) => (r.rule_id === ruleId ? { ...r, enabled: !r.enabled } : r))
    );
  };

  const handleSeverityChange = (ruleId, val) => {
    setRules((prev) =>
      prev.map((r) => (r.rule_id === ruleId ? { ...r, severity: parseInt(val) || 10 } : r))
    );
  };

  const handleParamChange = (ruleId, paramKey, val) => {
    setRules((prev) =>
      prev.map((r) => {
        if (r.rule_id !== ruleId) return r;
        return {
          ...r,
          params: {
            ...r.params,
            [paramKey]: isNaN(val) ? val : parseFloat(val),
          },
        };
      })
    );
  };

  const saveRule = async (rule) => {
    setSavingId(rule.rule_id);
    try {
      await api.updateRule(rule.rule_id, {
        enabled: rule.enabled,
        severity: rule.severity,
        params: rule.params,
      });
      alert(`Rule '${rule.name}' saved successfully!`);
    } catch (err) {
      alert("Failed to save rule: " + err.message);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="pt-2">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-navy-700 dark:text-white">Policy Rules Configuration</h2>
          <p className="text-sm font-medium text-gray-400">
            Hard policy constraints evaluated alongside unsupervised PyOD models.
          </p>
        </div>
        <button
          onClick={loadRules}
          className="flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-brand-500 shadow-md hover:bg-gray-50 dark:bg-navy-800 dark:text-white"
        >
          <MdRefresh className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* Rules Cards Grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {rules.map((rule) => (
          <Card key={rule.rule_id} extra="p-5 flex flex-col justify-between">
            <div>
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-brand-500">
                    {rule.rule_id}
                  </span>
                  <h4 className="text-lg font-bold text-navy-700 dark:text-white">{rule.name}</h4>
                </div>

                {/* Enable toggle */}
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    onChange={() => handleToggle(rule.rule_id)}
                    className="peer sr-only"
                  />
                  <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-brand-500 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none dark:border-gray-600 dark:bg-navy-900"></div>
                </label>
              </div>

              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{rule.description}</p>

              {/* Severity Slider */}
              <div className="mt-4 rounded-xl bg-[#F4F7FE] p-3 dark:bg-navy-900">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-gray-500">Risk Severity Boost:</span>
                  <span className="font-bold text-brand-500">+{rule.severity} pts</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="40"
                  step="5"
                  value={rule.severity}
                  onChange={(e) => handleSeverityChange(rule.rule_id, e.target.value)}
                  className="mt-2 w-full accent-brand-500"
                />
              </div>

              {/* Configurable Parameters */}
              {rule.params && Object.keys(rule.params).length > 0 && (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-bold uppercase text-gray-400">Rule Parameters</p>
                  {Object.entries(rule.params).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">{key}:</span>
                      <input
                        type={typeof val === "number" ? "number" : "text"}
                        value={val}
                        onChange={(e) => handleParamChange(rule.rule_id, key, e.target.value)}
                        className="w-24 rounded-lg border border-gray-200 px-2 py-1 text-right text-xs font-bold text-navy-700 outline-none focus:border-brand-500 dark:border-navy-700 dark:bg-navy-800 dark:text-white"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Save Button */}
            <div className="mt-5 pt-3 border-t border-gray-100 dark:border-navy-700">
              <button
                onClick={() => saveRule(rule)}
                disabled={savingId === rule.rule_id}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-500 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-brand-600 disabled:opacity-50"
              >
                <MdSave className="h-4 w-4" />
                {savingId === rule.rule_id ? "Saving..." : "Save Configuration"}
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

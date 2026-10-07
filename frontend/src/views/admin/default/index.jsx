import React, { useEffect, useState } from "react";
import { MdBarChart, MdReceiptLong, MdWarning, MdPendingActions, MdRefresh } from "react-icons/md";
import Widget from "components/widget/Widget";
import Card from "components/card";
import { api } from "api";
import ReviewDrawer from "views/admin/components/ReviewDrawer";
import Chart from "react-apexcharts";

export default function OverviewDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTx, setSelectedTx] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getOverview();
      setData(res);
    } catch (err) {
      console.error("Failed to load overview data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const kpis = data?.kpis || {
    total_spend: 2480500,
    transactions_count: 1420,
    flagged_count: 48,
    flag_rate_pct: 3.4,
    open_reviews: 12,
    avg_risk_score: 28.4,
  };

  const spendTimeline = data?.spend_over_time || [];
  const categoryData = data?.spend_by_category || [];
  const needsAttention = data?.needs_attention || [];

  // Chart options for Spend timeline
  const areaChartOptions = {
    chart: {
      type: "area",
      toolbar: { show: false },
    },
    colors: ["#4318FF"],
    fill: {
      type: "gradient",
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.5,
        opacityTo: 0.05,
        stops: [0, 90, 100],
      },
    },
    dataLabels: { enabled: false },
    stroke: { curve: "smooth", width: 3 },
    xaxis: {
      categories: spendTimeline.map((item) => item.date.slice(5)),
      labels: { style: { colors: "#A3AED0", fontWeight: 500 } },
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      labels: {
        style: { colors: "#A3AED0", fontWeight: 500 },
        formatter: (val) => `₹${Math.round(val / 1000)}k`,
      },
    },
    grid: { strokeDashArray: 5, borderColor: "#E2E8F0" },
    tooltip: {
      theme: "dark",
      y: { formatter: (val) => `₹${Number(val).toLocaleString("en-IN")}` },
    },
  };

  const areaChartSeries = [
    {
      name: "Daily Spend",
      data: spendTimeline.map((item) => item.spend),
    },
  ];

  // Donut chart options
  const donutOptions = {
    chart: { type: "donut" },
    labels: categoryData.map((c) => c.name),
    colors: ["#4318FF", "#6AD2FF", "#EFF4FB", "#FFB547", "#EE5D50", "#05CD99"],
    dataLabels: { enabled: false },
    legend: { position: "bottom", labels: { colors: "#A3AED0" } },
    plotOptions: {
      pie: {
        donut: {
          size: "70%",
          labels: {
            show: true,
            total: {
              show: true,
              label: "Total Categories",
              color: "#1B2559",
              formatter: () => `${categoryData.length}`,
            },
          },
        },
      },
    },
  };

  const donutSeries = categoryData.map((c) => c.value);

  const handleOpenReview = (item) => {
    setSelectedTx({
      ...item,
      amount: item.amount,
      firefly_group_id: item.firefly_group_id,
      flag_id: item.flag_id,
      score: {
        risk_score: item.risk_score,
        tier: item.tier,
        reasons: item.reason_summary ? [item.reason_summary] : [],
      },
    });
    setIsDrawerOpen(true);
  };

  return (
    <div className="pt-2">
      {/* Top Controls */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-navy-700 dark:text-white">Expense Anomaly Dashboard</h2>
          <p className="text-sm font-medium text-gray-400">Intelligent Auditor Workbench & Real-Time PyOD Scoring</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-brand-500 shadow-md hover:bg-gray-50 dark:bg-navy-800 dark:text-white"
        >
          <MdRefresh className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh Data
        </button>
      </div>

      {/* 4 Horizon Metric Widget Cards */}
      <div className="mt-3 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
        <Widget
          icon={<MdBarChart className="h-7 w-7" />}
          title={"Total Spend (₹)"}
          subtitle={`₹${kpis.total_spend.toLocaleString("en-IN")}`}
        />
        <Widget
          icon={<MdReceiptLong className="h-6 w-6" />}
          title={"Scored Transactions"}
          subtitle={`${kpis.transactions_count.toLocaleString("en-IN")}`}
        />
        <Widget
          icon={<MdWarning className="h-6 w-6 text-amber-500" />}
          title={"Flagged Anomalies"}
          subtitle={`${kpis.flagged_count} (${kpis.flag_rate_pct}%)`}
        />
        <Widget
          icon={<MdPendingActions className="h-6 w-6 text-red-500" />}
          title={"Pending Reviews"}
          subtitle={`${kpis.open_reviews} items`}
        />
      </div>

      {/* Main Charts Row */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Spend & Anomaly Area Chart */}
        <Card extra="col-span-2 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Timeline</p>
              <h4 className="text-lg font-bold text-navy-700 dark:text-white">Daily Spend & Trajectory</h4>
            </div>
            <span className="rounded-full bg-lightPrimary px-3 py-1 text-xs font-bold text-brand-500 dark:bg-navy-700">
              Last 14 Days
            </span>
          </div>
          <div className="mt-4 h-72">
            {spendTimeline.length > 0 ? (
              <Chart options={areaChartOptions} series={areaChartSeries} type="area" width="100%" height="100%" />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-gray-400">Loading timeline data...</div>
            )}
          </div>
        </Card>

        {/* Category Donut */}
        <Card extra="p-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Distribution</p>
            <h4 className="text-lg font-bold text-navy-700 dark:text-white">Spend by Category</h4>
          </div>
          <div className="mt-4 flex h-72 items-center justify-center">
            {categoryData.length > 0 ? (
              <Chart options={donutOptions} series={donutSeries} type="donut" width="100%" height="100%" />
            ) : (
              <div className="text-sm text-gray-400">Loading category breakdown...</div>
            )}
          </div>
        </Card>
      </div>

      {/* Needs Immediate Attention & Model Health */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Needs Immediate Attention */}
        <Card extra="col-span-2 p-5">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3 dark:border-navy-700">
            <div>
              <h4 className="text-lg font-bold text-navy-700 dark:text-white">Needs Immediate Attention</h4>
              <p className="text-xs text-gray-400">Top high-risk open claims requiring auditor sign-off</p>
            </div>
            <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-600 dark:bg-red-900/30 dark:text-red-400">
              {needsAttention.length} High Risk
            </span>
          </div>

          <div className="mt-4 divide-y divide-gray-100 dark:divide-navy-700">
            {needsAttention.length === 0 ? (
              <div className="py-8 text-center text-sm font-medium text-gray-400">
                🎉 No open high-risk flags! All transactions clear.
              </div>
            ) : (
              needsAttention.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-900/20">
                      <MdWarning className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-bold text-navy-700 dark:text-white">
                        ₹{Number(item.amount).toLocaleString("en-IN")} • {item.vendor}
                      </p>
                      <p className="text-xs text-gray-500 line-clamp-1">{item.reason_summary}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-bold text-red-600 dark:bg-red-900/40 dark:text-red-400">
                      {Math.round(item.risk_score)} HIGH
                    </span>
                    <button
                      onClick={() => handleOpenReview(item)}
                      className="rounded-xl bg-brand-500 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-brand-600"
                    >
                      Audit
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Model Health Card */}
        <Card extra="p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Engine State</p>
          <h4 className="text-lg font-bold text-navy-700 dark:text-white">PyOD Model Health</h4>

          <div className="mt-4 space-y-4">
            <div className="flex justify-between border-b border-gray-100 pb-2 text-sm dark:border-navy-700">
              <span className="text-gray-400">Active Version</span>
              <span className="font-bold text-navy-700 dark:text-white">{data?.model_health?.version_tag}</span>
            </div>
            <div className="flex justify-between border-b border-gray-100 pb-2 text-sm dark:border-navy-700">
              <span className="text-gray-400">Training Samples</span>
              <span className="font-bold text-navy-700 dark:text-white">
                {data?.model_health?.training_rows.toLocaleString() || "5,000"} rows
              </span>
            </div>
            <div className="flex justify-between border-b border-gray-100 pb-2 text-sm dark:border-navy-700">
              <span className="text-gray-400">Anomaly Rate</span>
              <span className="font-bold text-navy-700 dark:text-white">{data?.model_health?.flag_rate_pct}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Active Algorithms</span>
              <span className="font-bold text-brand-500">ECOD + IForest</span>
            </div>

            <div className="mt-6 rounded-xl bg-lightPrimary p-3.5 text-xs font-medium text-navy-700 dark:bg-navy-900 dark:text-gray-300">
              Auditor review labels directly improve unsupervised scoring precision during nightly retraining.
            </div>
          </div>
        </Card>
      </div>

      {/* Review Drawer Modal */}
      <ReviewDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        transaction={selectedTx}
        onReviewed={() => loadData()}
      />
    </div>
  );
}

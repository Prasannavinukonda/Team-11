import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Layout from "../components/Layout";
import { dashboardApi } from "../api/endpoints";

const GRADE_COLORS = ["#02C39A", "#84cc16", "#f59e0b", "#f97316", "#dc2626"];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    dashboardApi
      .stats()
      .then((res) => setStats(res.data))
      .catch(() => setError("Could not load dashboard stats."));
  }, []);

  return (
    <Layout>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Overview of screenings across your facility.</p>
        </div>
        <ModelStatusBadge stats={stats} />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!stats && !error && <p className="text-sm text-slate-400">Loading…</p>}

      {stats && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Total Patients" value={stats.total_patients} />
            <StatCard label="Total Screenings" value={stats.total_screenings} />
            <StatCard
              label="Referral Rate"
              value={`${Math.round(stats.referral_rate * 100)}%`}
              hint="Grade ≥ 2 screenings"
            />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Severity Distribution">
              {stats.total_screenings === 0 ? (
                <EmptyChart />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={toGradeData(stats.grade_distribution)}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="#94a3b8" />
                    <Tooltip />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                      {toGradeData(stats.grade_distribution).map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card title="Screenings Over Time">
              {stats.screenings_over_time.length === 0 ? (
                <EmptyChart />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={stats.screenings_over_time}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="#94a3b8" />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#028090" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        </>
      )}
    </Layout>
  );
}

function ModelStatusBadge({ stats }) {
  if (!stats) return null;

  if (stats.model_mode === "demo") {
    return (
      <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
        Demo mode — model not yet fine-tuned
      </span>
    );
  }

  const hasMetadata = stats.model_val_f1 != null;
  return (
    <span
      className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
      title="This is an early checkpoint — treat predictions as provisional until further training."
    >
      {hasMetadata
        ? `Trained model — val F1 ${stats.model_val_f1.toFixed(2)} (epoch ${stats.model_epoch})`
        : "Trained model active"}
    </span>
  );
}

function toGradeData(distribution) {
  return Object.entries(distribution).map(([label, count], i) => ({
    label,
    count,
    fill: GRADE_COLORS[i],
  }));
}

function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <p className="mb-4 text-sm font-medium text-slate-700">{title}</p>
      {children}
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="flex h-[260px] items-center justify-center text-sm text-slate-400">
      No data yet — run your first screening.
    </div>
  );
}

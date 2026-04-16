// src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Building2, FileText, TrendingUp, Boxes } from "lucide-react";
import { dashboardApi } from "../services/api";
import { StatCard, Card, PageHeader, Spinner, ErrorState } from "../components/ui";
import "./Dashboard.css";

export default function Dashboard() {
  const [summary,  setSummary]  = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [units,    setUnits]    = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);

  useEffect(() => {
    Promise.all([
      dashboardApi.summary(),
      dashboardApi.pipeline(),
      dashboardApi.units(),
    ])
      .then(([s, p, u]) => { setSummary(s); setPipeline(p); setUnits(u); })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-center"><Spinner size={36} /></div>;
  if (error)   return <ErrorState message={error} />;

  // Pipeline chart data
  const pipelineData = pipeline ? Object.entries(pipeline.pipeline).map(([status, count]) => ({
    name: status.replace(/_/g, " "),
    count,
  })) : [];

  const COLORS = {
    "in progress":       "#00c896",
    "pending gate 1":    "#f0a500",
    "blocked documents": "#e85555",
    "unit matched":      "#7c5cbf",
    "completed":         "#00c896",
    "cancelled":         "#4a6580",
  };

  return (
    <div className="dashboard">
      <PageHeader
        title="Dashboard"
        subtitle="MAF Leasing Agent · Live pipeline overview"
      />

      {/* KPI row */}
      <div className="dashboard-stats">
        <StatCard
          label="Active Leases"
          value={summary.active_leases}
          sub={`AED ${(summary.active_lease_value_aed / 1e6).toFixed(1)}M annual value`}
          accent
          icon={FileText}
        />
        <StatCard
          label="Pipeline Inquiries"
          value={summary.pipeline_inquiries}
          sub={`AED ${(summary.pipeline_value_aed / 1e6).toFixed(1)}M estimated value`}
          icon={TrendingUp}
        />
        <StatCard
          label="Vacant Units"
          value={summary.vacant_units}
          sub={`${summary.expiring_units} expiring soon`}
          icon={Boxes}
        />
        <StatCard
          label="Properties"
          value={summary.properties_count}
          sub={`${summary.occupancy_rate}% portfolio occupancy`}
          icon={Building2}
        />
      </div>

      {/* Pipeline chart + vacancy table */}
      <div className="dashboard-grid">
        {/* Pipeline by stage */}
        <Card>
          <h2 className="section-title">Pipeline by Stage</h2>
          <p className="section-sub">{pipeline?.total_active} active deals in progress</p>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={pipelineData} barCategoryGap="35%">
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#8fafc8", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#8fafc8", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#111e30",
                    border: "1px solid #1e3048",
                    borderRadius: 8,
                    color: "#f0f4f8",
                    fontSize: 13,
                  }}
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {pipelineData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={COLORS[entry.name] || "#4a6580"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Vacancy by property */}
        <Card>
          <h2 className="section-title">Vacancy by Property</h2>
          <p className="section-sub">{units?.portfolio?.vacant_units} vacant across {units?.count} properties</p>
          <div className="vacancy-list">
            {units?.properties?.slice(0, 6).map(p => (
              <div key={p.property_id} className="vacancy-row">
                <div className="vacancy-info">
                  <span className="vacancy-name">{p.property_name}</span>
                  <span className="vacancy-city">{p.city}</span>
                </div>
                <div className="vacancy-bars">
                  <div className="vacancy-bar-wrap">
                    <div
                      className="vacancy-bar"
                      style={{
                        width: `${Math.min(100, (p.vacant_units / (p.total_units || 1)) * 100)}%`
                      }}
                    />
                  </div>
                  <span className="vacancy-count">{p.vacant_units} vacant</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

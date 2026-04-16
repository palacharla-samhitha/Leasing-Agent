// src/pages/Units.jsx
import { useState } from "react";
import { unitsApi } from "../services/api";
import { useApi } from "../hooks/useapi";
import {
  PageHeader, Card, StatusBadge, Spinner,
  ErrorState, Empty, Pagination
} from "../components/ui";
import "./Units.css";

const STATUSES = ["", "vacant", "expiring_soon", "reserved_informally", "signed_unoccupied", "held_strategically"];

export default function Units() {
  const [offset,     setOffset]     = useState(0);
  const [status,     setStatus]     = useState("");
  const [property]   = useState("");
  const LIMIT = 20;

  const { data, loading, error } = useApi(
    () => unitsApi.list({ status, property_id: property, limit: LIMIT, offset }),
    [status, property, offset]
  );

  return (
    <div>
      <PageHeader
        title="Units"
        subtitle="Available leasable spaces across all properties"
      />

      {/* Filters */}
      <div className="filter-bar">
        <div className="filter-group">
          <label className="filter-label">Status</label>
          <select
            className="filter-select"
            value={status}
            onChange={e => { setStatus(e.target.value); setOffset(0); }}
          >
            {STATUSES.map(s => (
              <option key={s} value={s}>{s ? s.replace(/_/g, " ") : "All statuses"}</option>
            ))}
          </select>
        </div>
      </div>

      <Card>
        {loading && <div className="table-loading"><Spinner /></div>}
        {error   && <ErrorState message={error} />}

        {!loading && !error && (
          <>
            {data?.units?.length === 0
              ? <Empty message="No units found" />
              : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Unit ID</th>
                      <th>Property</th>
                      <th>Floor / Zone</th>
                      <th>Size (sqm)</th>
                      <th>Rent / sqm</th>
                      <th>Demand Score</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.units.map(u => (
                      <tr key={u.unit_id} className="table-row">
                        <td className="mono">{u.unit_id}</td>
                        <td className="bold">{u.property_name}</td>
                        <td className="text-sm text-muted">
                          {u.floor} · {u.zone}
                        </td>
                        <td>{u.sqm}</td>
                        <td>
                          {u.base_rent_sqm
                            ? `AED ${Number(u.base_rent_sqm).toLocaleString()}`
                            : "—"
                          }
                        </td>
                        <td>
                          {u.vp_demand_score != null ? (
                            <div className="demand-score">
                              <div
                                className="demand-bar"
                                style={{ width: `${u.vp_demand_score * 100}%` }}
                              />
                              <span>{u.vp_demand_score}</span>
                            </div>
                          ) : "—"}
                        </td>
                        <td><StatusBadge status={u.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            }

            <Pagination
              pagination={data?.pagination}
              onNext={() => setOffset(o => o + LIMIT)}
              onPrev={() => setOffset(o => Math.max(0, o - LIMIT))}
            />
          </>
        )}
      </Card>
    </div>
  );
}

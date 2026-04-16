// src/pages/Inquiries.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { inquiriesApi } from "../services/api";
import { useApi } from "../hooks/useapi";
import {
  PageHeader, Card, StatusBadge, Button,
  Spinner, ErrorState, Empty, Pagination
} from "../components/ui";
import "./Inquiries.css";

const STATUSES = ["", "in_progress", "pending_gate_1", "blocked_documents", "unit_matched", "completed", "cancelled"];
const PRIORITIES = ["", "high", "medium", "low"];

export default function Inquiries() {
  const navigate = useNavigate();
  const [offset,   setOffset]   = useState(0);
  const [status,   setStatus]   = useState("");
  const [priority, setPriority] = useState("");
  const LIMIT = 20;

  const { data, loading, error } = useApi(
    () => inquiriesApi.list({ status, priority, limit: LIMIT, offset }),
    [status, priority, offset]
  );

  function handleFilter(newStatus, newPriority) {
    setStatus(newStatus);
    setPriority(newPriority);
    setOffset(0);
  }

  return (
    <div>
      <PageHeader
        title="Inquiries"
        subtitle="All tenant leasing inquiries"
        action={
          <Button onClick={() => navigate("/inquiries/new")}>
            + New Inquiry
          </Button>
        }
      />

      {/* Filters */}
      <div className="filter-bar">
        <div className="filter-group">
          <label className="filter-label">Status</label>
          <select
            className="filter-select"
            value={status}
            onChange={e => handleFilter(e.target.value, priority)}
          >
            {STATUSES.map(s => (
              <option key={s} value={s}>{s || "All statuses"}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">Priority</label>
          <select
            className="filter-select"
            value={priority}
            onChange={e => handleFilter(status, e.target.value)}
          >
            {PRIORITIES.map(p => (
              <option key={p} value={p}>{p || "All priorities"}</option>
            ))}
          </select>
        </div>

        <Button variant="ghost" size="sm" onClick={() => handleFilter("", "")}>
          Clear
        </Button>
      </div>

      {/* Table */}
      <Card>
        {loading && <div className="table-loading"><Spinner /></div>}
        {error   && <ErrorState message={error} />}
        {!loading && !error && (
          <>
            {data?.inquiries?.length === 0
              ? <Empty message="No inquiries found" />
              : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Inquiry ID</th>
                      <th>Brand</th>
                      <th>Category</th>
                      <th>Mall</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Lead</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.inquiries.map(inq => (
                      <tr
                        key={inq.inquiry_id}
                        className="table-row"
                        onClick={() => navigate(`/inquiries/${inq.inquiry_id}`)}
                      >
                        <td className="mono">{inq.inquiry_id}</td>
                        <td className="bold">{inq.brand_name}</td>
                        <td className="text-sm text-muted">{inq.category}</td>
                        <td>{inq.preferred_mall_name || inq.preferred_mall || "—"}</td>
                        <td><StatusBadge status={inq.priority} /></td>
                        <td><StatusBadge status={inq.status} /></td>
                        <td>
                          {inq.lead_grade
                            ? <span className={`grade grade-${inq.lead_grade?.toLowerCase()}`}>{inq.lead_grade}</span>
                            : "—"
                          }
                        </td>
                        <td>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={e => {
                              e.stopPropagation();
                              navigate(`/inquiries/${inq.inquiry_id}`);
                            }}
                          >
                            View →
                          </Button>
                        </td>
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

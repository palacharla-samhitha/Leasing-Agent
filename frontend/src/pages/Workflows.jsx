// src/pages/Workflows.jsx
import { useState } from "react";
import { workflowsApi } from "../services/api";
import { useApi } from "../hooks/useapi";
import {
  PageHeader, Card, StatusBadge, Button,
  Spinner, ErrorState, Empty
} from "../components/ui";
import "./Workflows.css";

export default function Workflows() {
  const { data, loading, error, refetch } = useApi(() => workflowsApi.active());
  const [resuming, setResuming] = useState(null);
  const [selected, setSelected] = useState(null);

  async function handleResume(thread_id, gate, decision) {
    setResuming(thread_id);
    try {
      await workflowsApi.resume(thread_id, { decision, gate });
      await refetch();
      setSelected(null);
    } catch (err) {
      alert(`Resume failed: ${err.message}`);
    } finally {
      setResuming(null);
    }
  }

  const GATE_LABELS = {
    gate_1: "Gate 1 — Leasing Executive",
    gate_2: "Gate 2 — LCM Document Review",
    gate_3: "Gate 3 — Senior Manager",
  };

  return (
    <div>
      <PageHeader
        title="Workflows"
        subtitle="Active and paused leasing workflows"
        action={
          <Button variant="secondary" onClick={refetch}>
            Refresh
          </Button>
        }
      />

      {loading && <div className="page-center"><Spinner size={36} /></div>}
      {error   && <ErrorState message={error} />}

      {!loading && !error && (
        <>
          <p className="workflows-count">
            {data?.count || 0} active workflow{data?.count !== 1 ? "s" : ""}
          </p>

          {data?.count === 0
            ? <Empty message="No active workflows. Start one from an inquiry." />
            : (
              <div className="workflows-list">
                {data.workflows.map(wf => (
                  <Card
                    key={wf.thread_id}
                    className={`workflow-card ${selected === wf.thread_id ? "workflow-card--open" : ""}`}
                  >
                    <div
                      className="workflow-header"
                      onClick={() => setSelected(s => s === wf.thread_id ? null : wf.thread_id)}
                    >
                      <div className="workflow-meta">
                        <span className="workflow-inquiry">{wf.inquiry_id}</span>
                        <StatusBadge status={wf.status} />
                        {wf.paused_at && (
                          <span className="workflow-gate">
                            ⏸ {GATE_LABELS[wf.paused_at] || wf.paused_at}
                          </span>
                        )}
                      </div>
                      <span className="workflow-thread">{wf.thread_id?.slice(0, 8)}…</span>
                    </div>

                    {/* Gate approval panel */}
                    {selected === wf.thread_id && wf.paused_at && (
                      <div className="gate-panel">
                        <div className="gate-panel-title">
                          {GATE_LABELS[wf.paused_at]}
                        </div>
                        <p className="gate-panel-desc">
                          Review the agent's output and approve or reject to continue the workflow.
                        </p>
                        <div className="gate-actions">
                          <Button
                            variant="primary"
                            loading={resuming === wf.thread_id}
                            onClick={() => handleResume(wf.thread_id, wf.paused_at, "approve")}
                          >
                            ✓ Approve
                          </Button>
                          <Button
                            variant="danger"
                            loading={resuming === wf.thread_id}
                            onClick={() => handleResume(wf.thread_id, wf.paused_at, "reject")}
                          >
                            ✗ Reject
                          </Button>
                          <Button
                            variant="ghost"
                            onClick={() => window.open(`/api/workflows/${wf.thread_id}/state`)}
                          >
                            View State
                          </Button>
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )
          }
        </>
      )}
    </div>
  );
}

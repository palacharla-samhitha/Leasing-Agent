// src/pages/Properties.jsx
import { useNavigate } from "react-router-dom";
import { propertiesApi } from "../services/api";
import { useApi } from "../hooks/useapi";
import { PageHeader, Card, StatusBadge, Spinner, ErrorState, Empty } from "../components/ui";
import "./Properties.css";

export default function Properties() {
  const navigate = useNavigate();
  const { data, loading, error } = useApi(() => propertiesApi.list({ status: "active" }));

  if (loading) return <div className="page-center"><Spinner size={36} /></div>;
  if (error)   return <ErrorState message={error} />;

  return (
    <div>
      <PageHeader
        title="Properties"
        subtitle={`${data?.count || 0} active MAF malls`}
      />

      <div className="properties-grid">
        {data?.properties?.length === 0
          ? <Empty message="No properties found" />
          : data.properties.map(p => (
            <Card
              key={p.property_id}
              className="property-card"
              onClick={() => navigate(`/properties/${p.property_id}`)}
            >
              <div className="property-header">
                <div>
                  <h3 className="property-name">{p.name}</h3>
                  <p className="property-location">{p.address_city} · {p.address_country}</p>
                </div>
                <div className="property-code">{p.code}</div>
              </div>

              <div className="property-stats">
                <div className="prop-stat">
                  <span className="prop-stat-val">{p.total_units}</span>
                  <span className="prop-stat-label">Total</span>
                </div>
                <div className="prop-stat prop-stat--teal">
                  <span className="prop-stat-val">{p.vacant_units}</span>
                  <span className="prop-stat-label">Vacant</span>
                </div>
                <div className="prop-stat prop-stat--gold">
                  <span className="prop-stat-val">{p.expiring_units}</span>
                  <span className="prop-stat-label">Expiring</span>
                </div>
              </div>

              <div className="property-footer">
                {p.ejari_applicable && (
                  <span className="badge badge-teal">EJARI</span>
                )}
                <StatusBadge status={p.status} />
              </div>
            </Card>
          ))
        }
      </div>
    </div>
  );
}

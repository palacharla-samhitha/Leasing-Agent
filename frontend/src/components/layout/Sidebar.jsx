import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, FileText, Building2,
  GitBranch, Boxes, ChevronRight
} from "lucide-react";
import "./Sidebar.css";

const NAV = [
  { to: "/",           icon: LayoutDashboard, label: "Dashboard"  },
  { to: "/inquiries",  icon: FileText,        label: "Inquiries"  },
  { to: "/workflows",  icon: GitBranch,       label: "Workflows"  },
  { to: "/units",      icon: Boxes,           label: "Units"      },
  { to: "/properties", icon: Building2,       label: "Properties" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-re">re</span>
        <span className="logo-knew">knew</span>
        <span className="logo-divider">×</span>
        <span className="logo-maf">MAF</span>
      </div>

      <p className="sidebar-subtitle">Leasing Agent</p>

      <div className="sidebar-divider" />

      <nav className="sidebar-nav">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "sidebar-link--active" : ""}`
            }
          >
            <Icon size={17} />
            <span>{label}</span>
            <ChevronRight size={13} className="sidebar-chevron" />
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-badge">POC Build · April 2026</div>
        <p className="sidebar-confidential">CONFIDENTIAL</p>
      </div>
    </aside>
  );
}
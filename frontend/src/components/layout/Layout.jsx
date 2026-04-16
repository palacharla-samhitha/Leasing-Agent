// src/components/layout/Layout.jsx
import "./Layout.css";
import Sidebar from "./Sidebar";


export default function Layout({ children }) {
  return (
    <div className="layout">
      <Sidebar />
      <main className="layout-main">
        {children}
      </main>
    </div>
  );
}

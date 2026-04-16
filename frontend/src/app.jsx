// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout         from "./components/layout/Layout";
import Dashboard      from "./pages/Dashboard";
import Inquiries      from "./pages/Inquiries";
import NewInquiry     from "./pages/NewInquiry";
import InquiryDetail  from "./pages/InquiryDetail";
import Workflows      from "./pages/Workflows";
import Units          from "./pages/Units";
import Properties     from "./pages/Properties";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"                    element={<Dashboard />}      />
          <Route path="/inquiries"           element={<Inquiries />}      />
          <Route path="/inquiries/new"       element={<NewInquiry />}     />
          <Route path="/inquiries/:id"       element={<InquiryDetail />}  />
          <Route path="/workflows"           element={<Workflows />}      />
          <Route path="/units"               element={<Units />}          />
          <Route path="/properties"          element={<Properties />}     />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
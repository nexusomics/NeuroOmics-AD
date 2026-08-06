import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./store/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import AnalysesPage from "./pages/AnalysesPage";
import AnalysisDetailPage from "./pages/AnalysisDetailPage";
import VisualizationPage from "./pages/VisualizationPage";
import MLPage from "./pages/MLPage";
import DrugsPage from "./pages/DrugsPage";
import ReportsPage from "./pages/ReportsPage";
import AssistantPage from "./pages/AssistantPage";
import AdminPage from "./pages/AdminPage";

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center text-slate-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id" element={<ProjectDetailPage />} />
        <Route path="projects/:id/upload" element={<ProjectDetailPage initialTab="upload" />} />
        <Route path="projects/:id/analyses" element={<AnalysesPage />} />
        <Route path="projects/:id/visualization" element={<VisualizationPage />} />
        <Route path="projects/:id/ml" element={<MLPage />} />
        <Route path="projects/:id/drugs" element={<DrugsPage />} />
        <Route path="projects/:id/reports" element={<ReportsPage />} />
        <Route path="projects/:id/assistant" element={<AssistantPage />} />
        <Route path="analyses/:analysisId" element={<AnalysisDetailPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
    </Routes>
  );
}

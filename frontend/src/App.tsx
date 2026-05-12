import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { canViewAdmin, canViewChat, canViewDocuments, canViewSystemHealth } from "./auth/roleAccess";
import { AdminPage } from "./pages/AdminPage";
import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { HealthStatusPage } from "./pages/HealthStatusPage";
import { RetrievalDiagnosticsPage } from "./pages/RetrievalDiagnosticsPage";
import { QueryFeedbackPage } from "./pages/QueryFeedbackPage";
import { FeedbackAnalyticsPage } from "./pages/FeedbackAnalyticsPage";
import { ImprovementTasksPage } from "./pages/ImprovementTasksPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { DemoReadinessPage } from "./pages/DemoReadinessPage";
import { DemoCommandCenterPage } from "./pages/DemoCommandCenterPage";
import { DemoScriptPage } from "./pages/DemoScriptPage";
import { DemoEvidencePackPage } from "./pages/DemoEvidencePackPage";
import { DemoRunbookPage } from "./pages/DemoRunbookPage";
import { LoginPage } from "./pages/LoginPage";
import { NotAuthorizedPage } from "./pages/NotAuthorizedPage";

function AppLayout() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatGate />} />
        <Route path="/documents" element={<DocumentsGate />} />
        <Route path="/admin" element={<AdminGate />} />
        <Route path="/admin/health" element={<HealthGate />} />
        <Route path="/admin/retrieval-diagnostics" element={<RetrievalDiagnosticsGate />} />
        <Route path="/admin/query-feedback" element={<QueryFeedbackGate />} />
        <Route path="/admin/feedback-analytics" element={<FeedbackAnalyticsGate />} />
        <Route path="/admin/improvement-tasks" element={<ImprovementTasksGate />} />
        <Route path="/admin/audit-logs" element={<AuditLogsGate />} />
        <Route path="/admin/demo-readiness" element={<DemoReadinessGate />} />
        <Route path="/admin/demo-script" element={<DemoScriptGate />} />
        <Route path="/admin/demo-command-center" element={<DemoCommandCenterGate />} />
        <Route path="/admin/demo-evidence-pack" element={<DemoEvidencePackGate />} />
        <Route path="/admin/demo-runbook" element={<DemoRunbookGate />} />
        <Route path="/not-authorized" element={<NotAuthorizedPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

function ChatGate() {
  const { user, accessibleKbs } = useAuth();
  return canViewChat(user, accessibleKbs) ? <ChatPage /> : <Navigate to="/not-authorized" replace />;
}

function DocumentsGate() {
  const { user, accessibleKbs } = useAuth();
  return canViewDocuments(user, accessibleKbs) ? <DocumentsPage /> : <Navigate to="/not-authorized" replace />;
}

function AdminGate() {
  const { user } = useAuth();
  return canViewAdmin(user) ? <AdminPage /> : <Navigate to="/not-authorized" replace />;
}

function HealthGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <HealthStatusPage /> : <Navigate to="/not-authorized" replace />;
}

function RetrievalDiagnosticsGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <RetrievalDiagnosticsPage /> : <Navigate to="/not-authorized" replace />;
}

function QueryFeedbackGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <QueryFeedbackPage /> : <Navigate to="/not-authorized" replace />;
}

function FeedbackAnalyticsGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <FeedbackAnalyticsPage /> : <Navigate to="/not-authorized" replace />;
}

function ImprovementTasksGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <ImprovementTasksPage /> : <Navigate to="/not-authorized" replace />;
}

function AuditLogsGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <AuditLogsPage /> : <Navigate to="/not-authorized" replace />;
}

function DemoReadinessGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <DemoReadinessPage /> : <Navigate to="/not-authorized" replace />;
}

function DemoScriptGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <DemoScriptPage /> : <Navigate to="/not-authorized" replace />;
}

function DemoCommandCenterGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <DemoCommandCenterPage /> : <Navigate to="/not-authorized" replace />;
}

function DemoEvidencePackGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <DemoEvidencePackPage /> : <Navigate to="/not-authorized" replace />;
}

function DemoRunbookGate() {
  const { user } = useAuth();
  return canViewSystemHealth(user) ? <DemoRunbookPage /> : <Navigate to="/not-authorized" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

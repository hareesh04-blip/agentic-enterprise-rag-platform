import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { canViewAdmin, canViewChat, canViewDocuments } from "./auth/roleAccess";
import { AdminPage } from "./pages/AdminPage";
import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
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

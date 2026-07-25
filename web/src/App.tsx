import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { SucursalesPage } from "./pages/SucursalesPage";
import { ClientesPage } from "./pages/ClientesPage";
import { VehiculosPage } from "./pages/VehiculosPage";
import { CitasPage } from "./pages/CitasPage";
import { UsuariosPage } from "./pages/UsuariosPage";
import { ChatPage } from "./pages/ChatPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { auth, loading } = useAuth();
  if (loading) return <p className="muted" style={{ padding: "2rem" }}>Cargando...</p>;
  if (!auth) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <PrivateRoute>
                <AppLayout />
              </PrivateRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="sucursales" element={<SucursalesPage />} />
            <Route path="clientes" element={<ClientesPage />} />
            <Route path="vehiculos" element={<VehiculosPage />} />
            <Route path="citas" element={<CitasPage />} />
            <Route path="usuarios" element={<UsuariosPage />} />
            <Route path="chat" element={<ChatPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

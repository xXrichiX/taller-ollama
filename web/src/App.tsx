import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { HomePage } from "./pages/HomePage";
import { ClientesPage } from "./pages/ClientesPage";
import { VehiculosPage } from "./pages/VehiculosPage";
import { CitasPage } from "./pages/CitasPage";
import { InventarioPage } from "./pages/InventarioPage";
import { ChatPage } from "./pages/ChatPage";
import { SucursalesPage } from "./pages/SucursalesPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { auth, loading } = useAuth();
  if (loading) return <p className="muted" style={{ padding: "2rem" }}>Cargando...</p>;
  if (!auth) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <ThemeProvider>
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
            <Route index element={<HomePage />} />
            <Route path="clientes" element={<ClientesPage />} />
            <Route path="vehiculos" element={<VehiculosPage />} />
            <Route path="citas" element={<CitasPage />} />
            <Route path="ordenes" element={<CitasPage />} />
            <Route path="inventario" element={<InventarioPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="sucursales" element={<SucursalesPage />} />
            <Route path="islas" element={<Navigate to="/sucursales" replace />} />
            <Route path="usuarios" element={<Navigate to="/" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
    </ThemeProvider>
  );
}

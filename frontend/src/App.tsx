import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Vault from "./pages/Vault";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Vault />
          </ProtectedRoute>
        }
      />
      {/* Unknown paths -> home, which itself redirects to /login if signed out. */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

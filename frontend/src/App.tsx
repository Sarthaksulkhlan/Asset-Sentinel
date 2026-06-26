import React, { useState, useEffect, useCallback } from "react";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import DashboardPage from "./components/DashboardPage";
import { AuthProvider, useAuth } from "./auth/AuthContext";

type ViewState = "landing" | "login" | "dashboard" | "demo";

const routeForView = (view: ViewState) => {
  if (view === "login") return "/login";
  if (view === "dashboard") return "/dashboard";
  if (view === "demo") return "/demo";
  return "/";
};

const viewForPath = (path: string): ViewState => {
  if (path === "/login") return "login";
  if (path === "/dashboard") return "dashboard";
  if (path === "/demo") return "demo";
  return "landing";
};

function AppShell() {
  const { user, isAuthenticated, isAuthLoading, logout } = useAuth();
  const [view, setView] = useState<ViewState>(() => viewForPath(window.location.pathname));

  const navigate = useCallback((targetView: ViewState, replace = false) => {
    const nextPath = routeForView(targetView);
    if (window.location.pathname !== nextPath) {
      const method = replace ? "replaceState" : "pushState";
      window.history[method]({}, "", nextPath);
    }
    setView(targetView);
  }, []);

  useEffect(() => {
    const handlePopState = () => setView(viewForPath(window.location.pathname));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (isAuthLoading) return;
    if (view === "dashboard" && !isAuthenticated) {
      navigate("login", true);
    }
  }, [isAuthenticated, isAuthLoading, navigate, view]);

  const handleLoginSuccess = () => {
    navigate("dashboard", true);
  };

  const handleSignOut = async () => {
    await logout();
    localStorage.removeItem("sentinel_dashboard_state");
    navigate("landing", true);
  };

  // Safe router mapper
  const renderActiveScreen = () => {
    switch (view) {
      case "landing":
        return (
          <LandingPage 
            onNavigate={(targetView) => {
              navigate(targetView === "dashboard" && !isAuthenticated ? "login" : targetView);
            }} 
          />
        );
      case "login":
        return (
          <LoginPage 
            onNavigate={(targetView) => navigate(targetView)} 
            onLoginSuccess={handleLoginSuccess}
          />
        );
      case "dashboard":
        if (!isAuthenticated) {
          return (
            <LoginPage 
              onNavigate={(targetView) => navigate(targetView)} 
              onLoginSuccess={handleLoginSuccess}
            />
          );
        }
        return (
          <DashboardPage 
            userEmail={user?.email || user?.username || "Authenticated User"} 
            onSignOut={handleSignOut}
            onNavigate={(targetView) => navigate(targetView)}
          />
        );
      case "demo":
        return (
          <DashboardPage 
            userEmail="Demo Admin" 
            onSignOut={handleSignOut}
            onNavigate={(targetView) => navigate(targetView)}
            isDemoMode={true}
          />
        );
      default:
        return <LandingPage onNavigate={(targetView) => navigate(targetView)} />;
    }
  };

  return (
    <div className="w-screen min-h-screen bg-[#0A0C10] selection:bg-[#00d1ff]/20 animate-fade-in relative">
      {isAuthLoading ? (
        <div className="flex min-h-screen items-center justify-center text-sm font-semibold text-[#00d1ff]">
          Restoring secure session...
        </div>
      ) : renderActiveScreen()}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

import React, { useState, useEffect } from "react";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import DashboardPage from "./components/DashboardPage";

type ViewState = "landing" | "login" | "dashboard" | "demo";

export default function App() {
  const [view, setView] = useState<ViewState>(() => {
    const cachedEmail = localStorage.getItem("sentinel_active_session");
    const cachedView = localStorage.getItem("sentinel_active_view") as ViewState | null;
    if (cachedEmail) return cachedView === "demo" ? "demo" : "dashboard";
    return cachedView === "login" ? "login" : "landing";
  });
  const [currentUserEmail, setCurrentUserEmail] = useState<string | null>(() => localStorage.getItem("sentinel_active_session"));
  const [redirectTarget, setRedirectTarget] = useState<ViewState>("dashboard");

  // Read session variables if they exist in localStorage for persistency
  useEffect(() => {
    const cachedEmail = localStorage.getItem("sentinel_active_session");
    if (cachedEmail) {
      setCurrentUserEmail(cachedEmail);
      setView((current) => current === "demo" ? "demo" : "dashboard");
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("sentinel_active_view", view);
  }, [view]);

  const handleLoginSuccess = (email: string) => {
    localStorage.setItem("sentinel_active_session", email);
    localStorage.setItem("sentinel_active_view", redirectTarget);
    setCurrentUserEmail(email);
    setView(redirectTarget);
    setRedirectTarget("dashboard"); // reset to default
  };

  const handleSignOut = () => {
    localStorage.removeItem("sentinel_active_session");
    localStorage.removeItem("sentinel_active_view");
    localStorage.removeItem("sentinel_dashboard_state");
    setCurrentUserEmail(null);
    setView("landing");
  };

  // Safe router mapper
  const renderActiveScreen = () => {
    switch (view) {
      case "landing":
        // Reset auth on landing page to ensure they must enter credentials if they came from landing
        return (
          <LandingPage 
            onNavigate={(targetView) => {
              if (targetView === "dashboard") {
                // Clicking "Launch Dashboard Gateway" redirects to the same Admin Sign In page
                setRedirectTarget("dashboard");
                setView("login");
              } else if (targetView === "login") {
                setRedirectTarget("dashboard");
                setView("login");
              } else {
                setView(targetView);
              }
            }} 
          />
        );
      case "login":
        return (
          <LoginPage 
            onNavigate={(targetView) => setView(targetView)} 
            onLoginSuccess={handleLoginSuccess}
          />
        );
      case "dashboard":
        if (!currentUserEmail) {
          // Double guard direct dashboard URL/state access
          return (
            <LoginPage 
              onNavigate={(targetView) => setView(targetView)} 
              onLoginSuccess={handleLoginSuccess}
            />
          );
        }
        return (
          <DashboardPage 
            userEmail={currentUserEmail} 
            onSignOut={handleSignOut}
            onNavigate={(targetView) => setView(targetView)}
          />
        );
      case "demo":
        return (
          <DashboardPage 
            userEmail="Demo Admin" 
            onSignOut={handleSignOut}
            onNavigate={(targetView) => setView(targetView)}
            isDemoMode={true}
          />
        );
      default:
        return <LandingPage onNavigate={setView} />;
    }
  };

  return (
    <div className="w-screen min-h-screen bg-[#0A0C10] selection:bg-[#00d1ff]/20 animate-fade-in relative">
      {renderActiveScreen()}
    </div>
  );
}

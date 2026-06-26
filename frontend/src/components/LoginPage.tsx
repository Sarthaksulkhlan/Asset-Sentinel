import React, { useState } from "react";
import { 
  Shield, 
  Mail, 
  Key, 
  Eye, 
  EyeOff, 
  LogIn, 
  Smartphone, 
  HelpCircle, 
  AlertTriangle 
} from "lucide-react";
import { SentinelLogo } from "./SentinelLogo";
import { useAuth } from "../auth/AuthContext";

interface LoginPageProps {
  onNavigate: (view: "landing" | "login" | "dashboard" | "demo") => void;
  onLoginSuccess: (email: string) => void;
}

export default function LoginPage({ onNavigate, onLoginSuccess }: LoginPageProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg("");

    try {
      const user = await login(email.trim(), password);
      setIsSuccess(true);
      setTimeout(() => {
        onLoginSuccess(user.email || user.username);
      }, 900);
    } catch (error) {
      setErrorMsg(error instanceof Error ? error.message : "ACCESS DENIED: Invalid command identity or security key token.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="text-[#dae3ee] antialiased min-h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden bg-[#0A0C10] font-sans">
        <div className="absolute inset-0 bg-grid z-0 opacity-40"></div>
        <div className="scanline"></div>
        <main className="relative z-10 w-full max-w-[440px] px-6 text-center">
          <div className="glass-panel rounded-xl p-8 bg-[#161B22]/85 border border-[#00d1ff]/50 backdrop-blur-xl shadow-[0_0_30px_rgba(0,209,255,0.15)] flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-[#00d1ff]/10 border border-[#00d1ff] flex items-center justify-center glow-active">
              <SentinelLogo className="w-9 h-9 animate-pulse" />
            </div>
            <h2 className="text-[#00d1ff] font-extrabold text-lg tracking-wider font-mono">
              AUTHENTICATION VERIFIED
            </h2>
            <p className="text-xs text-[#bbc9cf] font-mono leading-normal">
              Launching Sentinel Command Center...
            </p>
            <div className="w-full bg-[#0D1117] h-1.5 rounded-full overflow-hidden mt-2 border border-white/5">
              <div className="bg-[#00d1ff] h-full w-full animate-pulse"></div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="text-[#dae3ee] antialiased min-h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden bg-[#0A0C10] font-sans">
      
      {/* Background Cyber Mesh Grid */}
      <div className="absolute inset-0 bg-grid z-0 opacity-40"></div>
      <div className="scanline"></div>

      {/* Centered Login Container */}
      <main className="relative z-10 w-full max-w-[440px] px-6">
        
        {/* Branding Area with back to landing navigation */}
        <div 
          onClick={() => onNavigate("landing")}
          className="flex flex-col items-center mb-8 text-center select-none cursor-pointer group hover:opacity-90 transition-opacity"
          title="Return to Landing Page"
        >
          <div className="w-16 h-16 rounded-lg bg-[#222b33] border border-[#3c494e] flex items-center justify-center mb-4 glow-accent relative overflow-hidden group-hover:border-[#00d1ff]/80 transition-all group-hover:scale-105 active:scale-95">
            <SentinelLogo className="w-10 h-10 group-hover:scale-110 transition-transform" />
            <div className="absolute inset-0 bg-[#00d1ff]/5 mix-blend-overlay"></div>
          </div>
          <h1 className="text-2xl font-black text-[#00d1ff] tracking-tight group-hover:text-cyan-300 transition-colors">
            Sentinel Command Authentication
          </h1>
          <p className="text-[10px] text-[#bbc9cf] mt-1.5 uppercase tracking-[0.25em] font-medium font-mono">
            Secure Administrator Gateway
          </p>
        </div>

        {/* Glassmorphic Login Card */}
        <div className="glass-panel rounded-xl p-8 shadow-2xl relative bg-[#161B22]/85 border border-white/10 backdrop-blur-xl">
          
          {/* Top Right MFA Badge */}
          <div className="absolute top-4 right-4 flex items-center gap-1.5 bg-[#00d1ff]/10 border border-[#00d1ff]/20 px-3 py-1 rounded-full">
            <div className="w-1.5 h-1.5 rounded-full bg-[#00d1ff] animate-ping"></div>
            <span className="text-[9px] font-bold tracking-wider text-[#00d1ff] font-mono">
              MFA READY
            </span>
          </div>

          <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-5">
            
            {/* Username Field */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-[#bbc9cf] flex items-center gap-1.5 font-mono" htmlFor="email">
                <Shield className="w-3.5 h-3.5 text-[#bbc9cf]" />
                Corporate Username
              </label>
              <input 
                className="input-cyber w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#0D1117] border border-white/10 focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff] placeholder:text-[#3c494e] outline-none transition-all" 
                id="email" 
                name="email" 
                placeholder="Sentinelcommand" 
                required 
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
              />
            </div>

            {/* Password Field */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#bbc9cf] flex items-center gap-1.5 font-mono" htmlFor="password">
                  <Key className="w-3.5 h-3.5 text-[#bbc9cf]" />
                  Access Key
                </label>
                <button 
                  type="button"
                  onClick={() => alert("SUPPORT ENCRYPTION: Please check key credentials database folder or contact your cybersecurity supervisor.")}
                  className="text-[10px] font-semibold text-[#00d1ff] hover:text-[#a4e6ff] transition-colors font-mono"
                >
                  Forgot key?
                </button>
              </div>
              <div className="relative">
                <input 
                  className="input-cyber w-full rounded-lg px-4 py-3 pr-10 text-xs font-mono text-[#dae3ee] bg-[#0D1117] border border-white/10 focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff] placeholder:text-[#3c494e] outline-none transition-all" 
                  id="password" 
                  name="password" 
                  placeholder="assetsentinel.alert" 
                  required 
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
                <button 
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#bbc9cf] hover:text-[#00d1ff] transition-colors focus:outline-none" 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error Notification Alert */}
            {errorMsg && (
              <div className="p-3 bg-red-950/20 border border-red-500/40 rounded-lg flex items-start gap-2 text-red-300 font-mono text-[10px] leading-relaxed font-semibold">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* MFA Notification Warning Panel */}
            <div className="mt-1 p-3.5 bg-[#141c24] border border-[#3c494e]/40 rounded-lg flex items-start gap-3 select-none">
              <Smartphone className="w-5 h-5 text-[#00d1ff] mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-[#dae3ee]">Two-Factor Authentication Required</p>
                <p className="font-mono text-[#bbc9cf] text-[9px] leading-normal mt-1 text-left">
                  Have your authenticator hardware key ready for a sync signal immediately after verifying your primary admin credentials.
                </p>
              </div>
            </div>

            {/* Primary Action Button */}
            <button 
              className="cyber-button w-full rounded-lg py-3 mt-2 flex items-center justify-center gap-2 text-sm font-bold text-[#003543] bg-[#00d1ff] hover:bg-[#a4e6ff] transition-all transform hover:-translate-y-0.5 active:translate-y-0 active:scale-95 shadow-[0_0_15px_rgba(0,209,255,0.2)] cursor-pointer" 
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4 text-[#003543]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  VALIDATING KEY TOKEN...
                </span>
              ) : (
                <span className="flex items-center gap-2 uppercase tracking-wider font-bold">
                  Secure Sign In
                  <LogIn className="w-4 h-4 text-[#003543]" />
                </span>
              )}
            </button>
          </form>

          {/* Contact Administrator Dial-up Footer */}
          <div className="mt-6 pt-5 border-t border-[#3c494e]/30 text-center">
            <button 
              onClick={() => alert("SUPPORT DESK: Reach terminal security dispatch line internally at EXT-9021 or secure-auth@organization.com")}
              className="text-xs text-[#bbc9cf] hover:text-[#dae3ee] transition-colors inline-flex items-center gap-2 justify-center font-mono font-medium"
            >
              <HelpCircle className="w-4 h-4 text-[#00d1ff]" />
              Contact Administrator Support
            </button>
          </div>

        </div>

        {/* Footer / System Status */}
        <div className="mt-8 text-center flex items-center justify-center gap-2 selection:bg-none">
          <div className="w-1.5 h-1.5 rounded-full bg-[#00d1ff] animate-ping glow-active"></div>
          <p className="text-mono text-[10px] text-[#859399] tracking-[0.25em] uppercase font-mono selection:bg-none">
            All Systems Operational
          </p>
        </div>

      </main>
    </div>
  );
}

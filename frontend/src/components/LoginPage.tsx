import React, { useEffect, useMemo, useRef, useState } from "react";
import { 
  Shield, 
  Mail, 
  Key, 
  Eye, 
  EyeOff, 
  LogIn, 
  Smartphone, 
  HelpCircle, 
  AlertTriangle,
  Check,
  CheckCircle2,
  Loader2,
  LockKeyhole,
  RotateCw,
  X
} from "lucide-react";
import { SentinelLogo } from "./SentinelLogo";
import { useAuth } from "../auth/AuthContext";
import { authFetch } from "../lib/api";

interface LoginPageProps {
  onNavigate: (view: "landing" | "login" | "admin-signup" | "dashboard" | "super-admin" | "demo") => void;
  onLoginSuccess: (role?: string) => void;
}

export default function LoginPage({ onNavigate, onLoginSuccess }: LoginPageProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [forgotOpen, setForgotOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg("");

    try {
      const user = await login(email.trim(), password);
      setIsSuccess(true);
      setTimeout(() => {
        onLoginSuccess(user.role);
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
                Corporate Username or Email
              </label>
              <input 
                className="input-cyber w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#0D1117] border border-white/10 focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff] placeholder:text-[#3c494e] outline-none transition-all" 
                id="email" 
                name="email" 
                placeholder="admin@company.com or sentinelcommand"
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
                  onClick={() => {
                    if (!email.trim()) {
                      setErrorMsg("Enter your registered corporate username or email first, then use Forgot Password.");
                      return;
                    }
                    setErrorMsg("");
                    setForgotOpen(true);
                  }}
                  className="text-[10px] font-semibold text-[#00d1ff] hover:text-[#a4e6ff] transition-colors font-mono"
                >
                  Forgot Password?
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
      {forgotOpen && <ForgotPasswordModal accountIdentifier={email.trim()} onClose={() => setForgotOpen(false)} />}
    </div>
  );
}

type ResetStep = "email" | "verify" | "password" | "success";

const resetPasswordChecks = (password: string) => [
  { label: "8 characters", valid: password.length >= 8 },
  { label: "Uppercase", valid: /[A-Z]/.test(password) },
  { label: "Lowercase", valid: /[a-z]/.test(password) },
  { label: "Number", valid: /\d/.test(password) },
  { label: "Symbol", valid: /[^A-Za-z0-9]/.test(password) },
];

function ForgotPasswordModal({ accountIdentifier, onClose }: { accountIdentifier: string; onClose: () => void }) {
  const [step, setStep] = useState<ResetStep>("email");
  const [identifier] = useState(accountIdentifier.trim());
  const [otpDigits, setOtpDigits] = useState(["", "", "", ""]);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resendSeconds, setResendSeconds] = useState(0);
  const otpRefs = useRef<Array<HTMLInputElement | null>>([]);

  const otp = otpDigits.join("");
  const checks = useMemo(() => resetPasswordChecks(newPassword), [newPassword]);
  const passwordValid = checks.every((check) => check.valid);
  const strength = checks.filter((check) => check.valid).length;

  useEffect(() => {
    if (resendSeconds <= 0) return;
    const timer = window.setTimeout(() => setResendSeconds((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [resendSeconds]);

  const sendCode = async () => {
    const normalizedIdentifier = identifier.trim();
    if (!normalizedIdentifier) {
      setError("Enter your registered account on the login form first.");
      return;
    }
    setIsBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await authFetch("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ identifier: normalizedIdentifier }),
      });
      const payload = await response.json().catch(() => ({}));
      setMessage(payload.message || "If account exists, verification code has been sent.");
      setOtpDigits(["", "", "", ""]);
      setStep("verify");
      setResendSeconds(60);
      window.setTimeout(() => otpRefs.current[0]?.focus(), 80);
    } catch {
      setError("Unable to reach password recovery service.");
    } finally {
      setIsBusy(false);
    }
  };

  const verifyCode = async () => {
    if (otp.length !== 4) {
      setError("Enter the 4 digit verification code.");
      return;
    }
    setIsBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await authFetch("/api/auth/verify-reset-code", {
        method: "POST",
        body: JSON.stringify({ identifier, otp }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.reset_allowed) {
        setError(payload.error || "Invalid or expired verification code.");
        return;
      }
      setStep("password");
      setMessage("Verification complete. Create a new password.");
    } catch {
      setError("Unable to verify code right now.");
    } finally {
      setIsBusy(false);
    }
  };

  const updatePassword = async () => {
    if (!passwordValid) {
      setError("New password does not meet strength requirements.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords must match.");
      return;
    }
    setIsBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await authFetch("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ identifier, otp, new_password: newPassword }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(payload.error || "Password reset failed.");
        return;
      }
      setStep("success");
      setMessage("Password updated successfully.");
    } catch {
      setError("Unable to update password right now.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, "").slice(-1);
    setOtpDigits((current) => {
      const next = [...current];
      next[index] = digit;
      return next;
    });
    if (digit && index < 3) otpRefs.current[index + 1]?.focus();
  };

  const handleOtpKeyDown = (index: number, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
    if (event.key === "Enter") {
      verifyCode();
    }
  };

  const handleOtpPaste = (event: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 4);
    if (pasted.length < 2) return;
    event.preventDefault();
    const next = ["", "", "", ""];
    pasted.split("").forEach((digit, index) => {
      next[index] = digit;
    });
    setOtpDigits(next);
    otpRefs.current[Math.min(pasted.length, 4) - 1]?.focus();
  };

  const title = step === "email" ? "Reset Password" : step === "verify" ? "Verify Your Email" : step === "password" ? "Create New Password" : "Password Updated";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/70 px-4 py-6 backdrop-blur-sm">
      <section className="relative w-full max-w-[520px] rounded-xl border border-[#00d1ff]/25 bg-[#111821]/95 shadow-[0_24px_90px_rgba(0,0,0,0.55)] animate-[fadeIn_180ms_ease-out]">
        <div className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#00d1ff]/30 bg-[#00d1ff]/10 text-[#a4e6ff]">
              {step === "success" ? <CheckCircle2 className="h-5 w-5 text-emerald-300" /> : <LockKeyhole className="h-5 w-5" />}
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-[0.24em] text-[#00d1ff]">Account Recovery</p>
              <h2 className="mt-1 text-xl font-black text-white">{title}</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 p-2 text-[#8fa3ad] transition-colors hover:border-white/20 hover:text-white"
            aria-label="Close password reset"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-3 gap-2 px-5 pt-5">
          {["Email", "Code", "Password"].map((item, index) => (
            <div key={item} className={`h-1.5 rounded-full ${index <= stepIndex(step) ? "bg-[#00d1ff]" : "bg-white/10"}`} />
          ))}
        </div>

        <div className="px-5 py-5">
          {message && (
            <div className="mb-4 rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-xs text-emerald-200">
              {message}
            </div>
          )}
          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-400/35 bg-red-500/10 px-4 py-3 text-xs text-red-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {step === "email" && (
            <div className="grid gap-5">
              <p className="text-sm leading-6 text-[#bbc9cf]">
                The verification code will be sent to the registered email linked with this account.
              </p>
              <div className="grid gap-2">
                <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono">
                  <Mail className="h-3.5 w-3.5" />
                  Account From Login
                </span>
                <div className="rounded-lg border border-[#00d1ff]/20 bg-[#00d1ff]/10 px-4 py-3 font-mono text-sm text-[#a4e6ff]">
                  {identifier}
                </div>
              </div>
              <button
                type="button"
                onClick={sendCode}
                disabled={isBusy}
                className="cyber-button inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-4 py-3 text-sm font-black uppercase tracking-wider text-[#003543] disabled:opacity-60"
              >
                {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
                Send Code
              </button>
            </div>
          )}

          {step === "verify" && (
            <div className="grid gap-5">
              <p className="text-sm leading-6 text-[#bbc9cf]">
                Enter 4 digit verification code sent to:
                <span className="block pt-1 font-mono text-[#a4e6ff]">{identifier}</span>
              </p>
              <div className="flex justify-center gap-3">
                {otpDigits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(node) => {
                      otpRefs.current[index] = node;
                    }}
                    value={digit}
                    onChange={(event) => handleOtpChange(index, event.target.value)}
                    onKeyDown={(event) => handleOtpKeyDown(index, event)}
                    onPaste={handleOtpPaste}
                    inputMode="numeric"
                    maxLength={1}
                    className="h-14 w-14 rounded-lg border border-white/10 bg-[#0D1117] text-center font-mono text-2xl font-black text-white outline-none transition-all focus:border-[#00d1ff] focus:ring-2 focus:ring-[#00d1ff]/20"
                  />
                ))}
              </div>
              <button
                type="button"
                onClick={verifyCode}
                disabled={isBusy || otp.length !== 4}
                className="cyber-button inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-4 py-3 text-sm font-black uppercase tracking-wider text-[#003543] disabled:opacity-60"
              >
                {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                Verify Code
              </button>
              <button
                type="button"
                onClick={sendCode}
                disabled={isBusy || resendSeconds > 0}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-xs font-bold uppercase tracking-wider text-[#bbc9cf] transition-colors hover:border-[#00d1ff]/30 hover:text-[#00d1ff] disabled:opacity-45"
              >
                <RotateCw className="h-4 w-4" />
                {resendSeconds > 0 ? `Resend in ${resendSeconds}s` : "Resend OTP"}
              </button>
            </div>
          )}

          {step === "password" && (
            <div className="grid gap-5">
              <label className="grid gap-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono">New Password</span>
                <div className="relative">
                  <input
                    className="input-cyber w-full rounded-lg border border-white/10 bg-[#0D1117] px-4 py-3 pr-10 text-sm text-[#dae3ee] outline-none transition-all focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff]"
                    type={showNewPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword((value) => !value)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#bbc9cf] hover:text-[#00d1ff]"
                  >
                    {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>
              <label className="grid gap-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono">Confirm Password</span>
                <input
                  className="input-cyber w-full rounded-lg border border-white/10 bg-[#0D1117] px-4 py-3 text-sm text-[#dae3ee] outline-none transition-all focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff]"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </label>
              <div className="rounded-lg border border-white/10 bg-[#0D1117] p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-[#a4e6ff]">Password strength</span>
                  <span className="text-xs font-mono text-[#00d1ff]">{strength <= 2 ? "Weak" : strength <= 4 ? "Medium" : "Strong"}</span>
                </div>
                <div className="grid gap-2">
                  {checks.map((check) => (
                    <div key={check.label} className={`flex items-center gap-2 text-xs ${check.valid ? "text-emerald-300" : "text-[#8fa3ad]"}`}>
                      <span className={`flex h-5 w-5 items-center justify-center rounded-full border ${check.valid ? "border-emerald-400/40 bg-emerald-400/10" : "border-white/10"}`}>
                        {check.valid ? <Check className="h-3.5 w-3.5" /> : null}
                      </span>
                      {check.label}
                    </div>
                  ))}
                </div>
              </div>
              <button
                type="button"
                onClick={updatePassword}
                disabled={isBusy}
                className="cyber-button inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-4 py-3 text-sm font-black uppercase tracking-wider text-[#003543] disabled:opacity-60"
              >
                {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <LockKeyhole className="h-4 w-4" />}
                Update Password
              </button>
            </div>
          )}

          {step === "success" && (
            <div className="grid gap-5 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-400/10">
                <CheckCircle2 className="h-9 w-9 text-emerald-300" />
              </div>
              <p className="text-lg font-black text-white">Password updated successfully</p>
              <p className="text-sm leading-6 text-[#bbc9cf]">Your old sessions have been revoked. Sign in again with your new password.</p>
              <button
                type="button"
                onClick={onClose}
                className="cyber-button inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-4 py-3 text-sm font-black uppercase tracking-wider text-[#003543]"
              >
                Return to Login
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function stepIndex(step: ResetStep) {
  if (step === "email") return 0;
  if (step === "verify") return 1;
  return 2;
}

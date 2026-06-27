import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  LockKeyhole,
  Mail,
  Phone,
  ShieldCheck,
  UserPlus
} from "lucide-react";
import { authFetch } from "../lib/api";
import { SentinelLogo } from "./SentinelLogo";

interface AdminSignupPageProps {
  onNavigate: (view: "landing" | "login" | "admin-signup" | "dashboard" | "demo") => void;
}

type SignupForm = {
  companyName: string;
  companyWebsite: string;
  industry: string;
  companySize: string;
  country: string;
  fullName: string;
  workEmail: string;
  mobileNumber: string;
  jobTitle: string;
  department: string;
  username: string;
  password: string;
  confirmPassword: string;
  termsAccepted: boolean;
  privacyAccepted: boolean;
};

const initialForm: SignupForm = {
  companyName: "",
  companyWebsite: "",
  industry: "",
  companySize: "",
  country: "",
  fullName: "",
  workEmail: "",
  mobileNumber: "",
  jobTitle: "",
  department: "",
  username: "",
  password: "",
  confirmPassword: "",
  termsAccepted: false,
  privacyAccepted: false,
};

const industries = ["Cybersecurity", "Financial Services", "Healthcare", "Manufacturing", "Technology", "Government", "Education", "Retail", "Other"];
const companySizes = ["1-50", "51-200", "201-500", "501-1,000", "1,001-5,000", "5,001+"];
const countries = ["United States", "India", "United Kingdom", "Canada", "Australia", "Germany", "Singapore", "United Arab Emirates", "Other"];

const emailRegex = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;
const mobileRegex = /^\+[1-9]\d{7,14}$/;
const usernameRegex = /^[A-Za-z0-9._-]{4,64}$/;
const personalDomains = new Set(["gmail.com", "outlook.com", "yahoo.com", "icloud.com"]);
const blockedDomains = new Set(["example.com", "test.com", "invalid", "localhost"]);

const passwordChecks = (password: string) => [
  { label: "8+ characters", valid: password.length >= 8 },
  { label: "Uppercase", valid: /[A-Z]/.test(password) },
  { label: "Lowercase", valid: /[a-z]/.test(password) },
  { label: "Number", valid: /\d/.test(password) },
  { label: "Symbol", valid: /[^A-Za-z0-9]/.test(password) },
];

const emailValidationError = (value: string) => {
  const email = value.trim().toLowerCase();
  if (!emailRegex.test(email)) return "Enter a valid work email.";
  const [local, rawDomain] = email.split("@");
  const domain = rawDomain.replace(/\.$/, "");
  const labels = domain.split(".");
  const secondLevel = labels.length >= 2 ? labels[labels.length - 2] : "";
  if (blockedDomains.has(domain) || ["invalid", "localhost"].includes(labels[labels.length - 1])) return "Use a real personal or business email domain.";
  if (local.startsWith(".") || local.endsWith(".") || local.includes("..")) return "Enter a valid work email.";
  if (labels.some((label) => !label || label.startsWith("-") || label.endsWith("-"))) return "Enter a valid email domain.";
  if (labels.some((label) => /^\d+$/.test(label))) return "Email domain cannot contain numeric-only labels.";
  if (!personalDomains.has(domain) && (secondLevel.length < 4 || /^\d/.test(secondLevel))) return "Use a legitimate business email domain.";
  return "";
};

export default function AdminSignupPage({ onNavigate }: AdminSignupPageProps) {
  const [form, setForm] = useState<SignupForm>(initialForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [toast, setToast] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const checks = useMemo(() => passwordChecks(form.password), [form.password]);
  const passwordStrong = checks.every((check) => check.valid);

  const updateField = (field: keyof SignupForm, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const validate = () => {
    const next: Record<string, string> = {};
    const required: Array<keyof SignupForm> = [
      "companyName",
      "industry",
      "companySize",
      "country",
      "fullName",
      "workEmail",
      "mobileNumber",
      "jobTitle",
      "department",
      "username",
      "password",
      "confirmPassword",
    ];

    required.forEach((field) => {
      if (!String(form[field]).trim()) next[field] = "Required";
    });
    if (form.workEmail) {
      const emailError = emailValidationError(form.workEmail);
      if (emailError) next.workEmail = emailError;
    }
    if (form.mobileNumber && !mobileRegex.test(form.mobileNumber.trim())) next.mobileNumber = "Use country code, for example +14155552671.";
    if (form.username && !usernameRegex.test(form.username.trim())) next.username = "Use 4-64 letters, numbers, dots, underscores, or hyphens.";
    if (form.password && !passwordStrong) next.password = "Password does not meet enterprise strength policy.";
    if (form.confirmPassword && form.password !== form.confirmPassword) next.confirmPassword = "Passwords must match.";
    if (!form.termsAccepted) next.termsAccepted = "Required";
    if (!form.privacyAccepted) next.privacyAccepted = "Required";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setToast("");
    if (!validate()) {
      setToast("Resolve highlighted validation checks before submitting.");
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await authFetch("/api/admin-signup", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          username: form.username.trim(),
          workEmail: form.workEmail.trim(),
          mobileNumber: form.mobileNumber.trim(),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setToast(payload.error || "Registration failed.");
        if (payload.field) setErrors({ [payload.field]: payload.error || "Invalid value" });
        return;
      }
      if (payload.emailNotificationSent === false) {
        setToast(payload.message || "Registration saved, but email notification could not be sent.");
      }
      setIsSubmitted(true);
      if (payload.emailNotificationSent !== false) setToast("Enterprise registration transmitted.");
    } catch {
      setToast("Unable to reach the registration service.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass = "w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#070b10] border border-white/10 focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff] outline-none transition-all";
  const errorClass = "text-[10px] font-mono text-red-300 mt-1";

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-[#0A0C10] text-[#dae3ee] relative overflow-hidden flex items-center justify-center px-6">
        <div className="absolute inset-0 bg-grid opacity-40"></div>
        <div className="scanline"></div>
        <section className="relative z-10 max-w-xl w-full text-center glass-panel rounded-xl border border-emerald-400/40 bg-[#111821]/90 p-8 shadow-[0_0_40px_rgba(16,185,129,0.12)]">
          <div className="w-16 h-16 rounded-full border border-emerald-400/60 bg-emerald-400/10 flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="w-9 h-9 text-emerald-300" />
          </div>
          <h1 className="text-2xl font-black text-emerald-300 uppercase tracking-wider">Registration Received</h1>
          <p className="mt-4 text-sm text-[#bbc9cf] leading-relaxed">
            Your enterprise admin account has been created.
          </p>
          {toast && (
            <p className="mt-4 rounded-md border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-xs font-mono text-amber-200">
              {toast}
            </p>
          )}
          <button
            onClick={() => onNavigate("login")}
            className="mt-8 px-6 py-3 rounded-lg bg-[#00d1ff] text-[#003543] font-bold text-xs uppercase tracking-wider hover:bg-cyan-300 transition-all"
          >
            Continue to Admin Login
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0C10] text-[#dae3ee] relative overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-35"></div>
      <div className="scanline"></div>
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-8">
        <button
          onClick={() => onNavigate("landing")}
          className="inline-flex items-center gap-2 text-xs font-mono text-[#bbc9cf] hover:text-[#00d1ff] transition-colors mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Sentinel Command
        </button>

        <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-5 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-lg bg-[#182028] border border-[#00d1ff]/40 flex items-center justify-center">
                <SentinelLogo className="w-7 h-7" />
              </div>
              <span className="text-[#00d1ff] font-mono text-xs uppercase tracking-[0.28em]">Enterprise Enrollment</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight">Admin Sign Up</h1>
            <p className="mt-3 text-sm text-[#bbc9cf] max-w-2xl leading-relaxed">
              Register an authorized administrator for Asset Sentinel Enterprise asset integrity monitoring.
            </p>
          </div>
          <div className="rounded-lg border border-[#00d1ff]/25 bg-[#00d1ff]/5 px-4 py-3 text-xs font-mono text-[#00d1ff] flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" />
            Secure bcrypt credential provisioning
          </div>
        </header>

        {toast && (
          <div className="mb-5 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-xs font-mono text-amber-200 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 mt-0.5" />
            {toast}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="glass-panel rounded-xl border border-[#3c494e]/30 bg-[#111821]/88 p-6">
            <h2 className="text-sm font-black uppercase tracking-widest text-[#00d1ff] flex items-center gap-2 mb-5">
              <Building2 className="w-4 h-4" />
              Company Information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Company Name" error={errors.companyName}><input className={inputClass} value={form.companyName} onChange={(e) => updateField("companyName", e.target.value)} /></Field>
              <Field label="Company Website" optional><input className={inputClass} placeholder="https://company.com" value={form.companyWebsite} onChange={(e) => updateField("companyWebsite", e.target.value)} /></Field>
              <Field label="Industry" error={errors.industry}><Select value={form.industry} onChange={(value) => updateField("industry", value)} options={industries} /></Field>
              <Field label="Company Size" error={errors.companySize}><Select value={form.companySize} onChange={(value) => updateField("companySize", value)} options={companySizes} /></Field>
              <Field label="Country" error={errors.country}><Select value={form.country} onChange={(value) => updateField("country", value)} options={countries} /></Field>
            </div>
          </section>

          <section className="glass-panel rounded-xl border border-[#3c494e]/30 bg-[#111821]/88 p-6">
            <h2 className="text-sm font-black uppercase tracking-widest text-[#00d1ff] flex items-center gap-2 mb-5">
              <Mail className="w-4 h-4" />
              Administrator Information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Full Name" error={errors.fullName}><input className={inputClass} value={form.fullName} onChange={(e) => updateField("fullName", e.target.value)} /></Field>
              <Field label="Work Email" error={errors.workEmail}><input className={inputClass} value={form.workEmail} onChange={(e) => updateField("workEmail", e.target.value)} /></Field>
              <Field label="Mobile Number" error={errors.mobileNumber}><input className={inputClass} placeholder="+14155552671" value={form.mobileNumber} onChange={(e) => updateField("mobileNumber", e.target.value)} /></Field>
              <Field label="Job Title / Designation" error={errors.jobTitle}><input className={inputClass} value={form.jobTitle} onChange={(e) => updateField("jobTitle", e.target.value)} /></Field>
              <Field label="Department" error={errors.department}><input className={inputClass} value={form.department} onChange={(e) => updateField("department", e.target.value)} /></Field>
            </div>
          </section>

          <section className="glass-panel rounded-xl border border-[#00d1ff]/25 bg-[#111821]/88 p-6 lg:col-span-2">
            <h2 className="text-sm font-black uppercase tracking-widest text-[#00d1ff] flex items-center gap-2 mb-5">
              <LockKeyhole className="w-4 h-4" />
              Account
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field label="Username" error={errors.username}><input className={inputClass} value={form.username} onChange={(e) => updateField("username", e.target.value)} /></Field>
              <Field label="Password" error={errors.password}>
                <div className="relative">
                  <input className={`${inputClass} pr-10`} type={showPassword ? "text" : "password"} value={form.password} onChange={(e) => updateField("password", e.target.value)} />
                  <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#bbc9cf] hover:text-[#00d1ff]">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </Field>
              <Field label="Confirm Password" error={errors.confirmPassword}><input className={inputClass} type="password" value={form.confirmPassword} onChange={(e) => updateField("confirmPassword", e.target.value)} /></Field>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {checks.map((check) => (
                <span key={check.label} className={`text-[10px] font-mono px-2.5 py-1 rounded border ${check.valid ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300" : "border-[#3c494e]/40 bg-[#070b10] text-[#bbc9cf]"}`}>
                  {check.label}
                </span>
              ))}
            </div>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
              <Checkbox label="I agree to the Terms of Service" checked={form.termsAccepted} error={errors.termsAccepted} onChange={(checked) => updateField("termsAccepted", checked)} />
              <Checkbox label="I agree to the Privacy Policy" checked={form.privacyAccepted} error={errors.privacyAccepted} onChange={(checked) => updateField("privacyAccepted", checked)} />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-7 w-full md:w-auto px-7 py-3 rounded-lg bg-[#00d1ff] hover:bg-cyan-300 text-[#003543] font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 disabled:opacity-60 transition-all"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
              {isSubmitting ? "Creating Secure Account..." : "Create Admin Account"}
            </button>
          </section>
        </form>
      </main>
    </div>
  );
}

function Field({ label, children, error, optional }: { label: string; children: React.ReactNode; error?: string; optional?: boolean }) {
  return (
    <label className="flex flex-col gap-1.5 text-[9px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono">
      <span>{label}{optional ? <span className="text-[#65737c]"> optional</span> : null}</span>
      {children}
      {error ? <span className="text-[10px] font-mono text-red-300 normal-case tracking-normal">{error}</span> : null}
    </label>
  );
}

function Select({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <select
      className="w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#070b10] border border-white/10 focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff] outline-none transition-all"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">Select</option>
      {options.map((option) => <option key={option} value={option}>{option}</option>)}
    </select>
  );
}

function Checkbox({ label, checked, onChange, error }: { label: string; checked: boolean; onChange: (checked: boolean) => void; error?: string }) {
  return (
    <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-[#070b10] px-4 py-3 text-xs text-[#dae3ee]">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 h-4 w-4 accent-[#00d1ff]"
      />
      <span>
        {label}
        {error ? <span className="block text-[10px] font-mono text-red-300 mt-1">{error}</span> : null}
      </span>
    </label>
  );
}

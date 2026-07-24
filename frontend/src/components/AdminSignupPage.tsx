import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  LockKeyhole,
  Mail,
  Phone,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
} from "lucide-react";
import { authFetch } from "../lib/api";
import { SentinelLogo } from "./SentinelLogo";

interface AdminSignupPageProps {
  onNavigate: (view: "landing" | "login" | "admin-signup" | "dashboard" | "super-admin" | "demo") => void;
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

type StepId = "company" | "admin" | "security";

type PairingCode = {
  code: string;
  expiresAt: string;
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

const steps: Array<{ id: StepId; title: string; eyebrow: string }> = [
  { id: "company", title: "Company Setup", eyebrow: "Company Details" },
  { id: "admin", title: "Administrator Profile", eyebrow: "Admin Profile" },
  { id: "security", title: "Security Setup", eyebrow: "Security Setup" },
];

const industries = ["Cybersecurity", "Financial Services", "Healthcare", "Manufacturing", "Technology", "Government", "Education", "Retail", "Other"];
const companySizes = ["1-50", "51-200", "201-500", "501-1,000", "1,001-5,000", "5,001+"];
const countries = ["United States", "India", "United Kingdom", "Canada", "Australia", "Germany", "Singapore", "United Arab Emirates", "Other"];

const emailRegex = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;
const mobileRegex = /^\+[1-9]\d{7,14}$/;
const usernameRegex = /^[A-Za-z0-9._-]{4,64}$/;
const personalDomains = new Set(["gmail.com", "outlook.com", "yahoo.com", "icloud.com"]);
const blockedDomains = new Set(["example.com", "test.com", "invalid", "localhost"]);

const stepFields: Record<StepId, Array<keyof SignupForm>> = {
  company: ["companyName", "industry", "companySize", "country"],
  admin: ["fullName", "workEmail", "mobileNumber", "jobTitle", "department"],
  security: ["username", "password", "confirmPassword", "termsAccepted", "privacyAccepted"],
};

const passwordChecks = (password: string) => [
  { label: "Minimum 8 characters", valid: password.length >= 8 },
  { label: "Uppercase letter", valid: /[A-Z]/.test(password) },
  { label: "Lowercase letter", valid: /[a-z]/.test(password) },
  { label: "Number", valid: /\d/.test(password) },
  { label: "Special symbol", valid: /[^A-Za-z0-9]/.test(password) },
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

const websiteValidationError = (value: string) => {
  if (!value.trim()) return "";
  try {
    const url = new URL(value.trim());
    if (!["http:", "https:"].includes(url.protocol)) return "Use a valid http or https URL.";
    return "";
  } catch {
    return "Use a valid website URL, for example https://company.com.";
  }
};

const strengthLabel = (validCount: number) => {
  if (validCount <= 2) return "Weak";
  if (validCount <= 4) return "Medium";
  return "Strong";
};

export default function AdminSignupPage({ onNavigate }: AdminSignupPageProps) {
  const [form, setForm] = useState<SignupForm>(initialForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [activeStep, setActiveStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [toast, setToast] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);
  const [pairingCode, setPairingCode] = useState<PairingCode | null>(null);

  const checks = useMemo(() => passwordChecks(form.password), [form.password]);
  const validPasswordChecks = checks.filter((check) => check.valid).length;
  const passwordStrong = checks.every((check) => check.valid);
  const passwordStrength = strengthLabel(validPasswordChecks);
  const currentStep = steps[activeStep];
  const progressPercent = ((activeStep + 1) / steps.length) * 100;

  const updateField = (field: keyof SignupForm, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const validateFields = (fields: Array<keyof SignupForm>) => {
    const next: Record<string, string> = {};
    const checkedFields = new Set<string>(fields);
    fields.forEach((field) => {
      if (typeof form[field] === "boolean") {
        if (!form[field]) next[field] = "Required for enterprise enrollment.";
        return;
      }
      if (!String(form[field]).trim()) next[field] = "Required";
    });
    if (fields.includes("companyWebsite") && form.companyWebsite) {
      const websiteError = websiteValidationError(form.companyWebsite);
      if (websiteError) next.companyWebsite = websiteError;
    }
    if (fields.includes("workEmail") && form.workEmail) {
      const emailError = emailValidationError(form.workEmail);
      if (emailError) next.workEmail = emailError;
    }
    if (fields.includes("mobileNumber") && form.mobileNumber && !mobileRegex.test(form.mobileNumber.trim())) {
      next.mobileNumber = "Use country code, for example +14155552671.";
    }
    if (fields.includes("username") && form.username && !usernameRegex.test(form.username.trim())) {
      next.username = "Use 4-64 letters, numbers, dots, underscores, or hyphens.";
    }
    if (fields.includes("password") && form.password && !passwordStrong) {
      next.password = "Password does not meet enterprise strength policy.";
    }
    if (fields.includes("confirmPassword") && form.confirmPassword && form.password !== form.confirmPassword) {
      next.confirmPassword = "Passwords must match.";
    }
    setErrors((current) => {
      const merged = { ...current };
      checkedFields.forEach((field) => {
        delete merged[field];
      });
      return { ...merged, ...next };
    });
    return Object.keys(next).length === 0;
  };

  const validateAll = () => {
    const allFields = Array.from(new Set(Object.values(stepFields).flat()));
    const baseValid = validateFields(allFields);
    const websiteError = websiteValidationError(form.companyWebsite);
    if (websiteError) {
      setErrors((current) => ({ ...current, companyWebsite: websiteError }));
      return false;
    }
    setErrors((current) => {
      const next = { ...current };
      delete next.companyWebsite;
      return next;
    });
    return baseValid && !websiteError;
  };

  const goNext = () => {
    setToast("");
    if (!validateFields([...stepFields[currentStep.id], ...(currentStep.id === "company" ? ["companyWebsite" as keyof SignupForm] : [])])) {
      setToast("Resolve highlighted checks before continuing.");
      return;
    }
    setCompletedSteps((current) => new Set(current).add(currentStep.id));
    setActiveStep((value) => Math.min(value + 1, steps.length - 1));
  };

  const goBack = () => {
    setToast("");
    setActiveStep((value) => Math.max(value - 1, 0));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setToast("");
    if (!validateAll()) {
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
      setCompletedSteps(new Set(steps.map((step) => step.id)));
      setPairingCode(payload.pairingCode || null);
      setIsSubmitted(true);
      if (payload.emailNotificationSent === false) {
        setToast(payload.message || "Workspace created, but email notification could not be sent.");
      } else {
        setToast("Company workspace created.");
      }
    } catch {
      setToast("Unable to reach the registration service.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyEnrollmentToken = async () => {
    if (!pairingCode?.code) return;
    await navigator.clipboard?.writeText(pairingCode.code).catch(() => undefined);
    setCopiedToken(true);
    window.setTimeout(() => setCopiedToken(false), 1600);
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-[#070B10] text-[#dae3ee] relative overflow-hidden">
        <SignupBackdrop />
        <main className="relative z-10 min-h-screen flex items-center justify-center px-4 py-8">
          <section className="w-full max-w-3xl rounded-lg border border-emerald-400/35 bg-[#0F151D]/95 shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
            <div className="border-b border-white/10 px-6 py-5 sm:px-8">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-emerald-300/40 bg-emerald-400/10">
                  <CheckCircle2 className="h-6 w-6 text-emerald-300" />
                </div>
                <div>
                  <p className="text-[10px] font-mono uppercase tracking-[0.24em] text-emerald-300">Provisioning Complete</p>
                  <h1 className="mt-1 text-xl sm:text-2xl font-black text-white">Company Workspace Created Successfully</h1>
                </div>
              </div>
            </div>

            <div className="grid gap-4 p-6 sm:grid-cols-3 sm:p-8">
              <SuccessMetric label="Company Name" value={form.companyName} />
              <SuccessMetric label="Admin Email" value={form.workEmail} />
              <SuccessMetric label="Role" value="Company Administrator" />
            </div>

            <div className="mx-6 mb-6 rounded-lg border border-[#00d1ff]/25 bg-[#07131B] p-5 sm:mx-8 sm:mb-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#00d1ff]/30 bg-[#00d1ff]/10 text-[#a4e6ff]">
                    <KeyRound className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-[#00d1ff]">Your Device Pairing Code</p>
                    <p className="mt-2 font-mono text-3xl font-black tracking-[0.32em] text-white">{pairingCode?.code || "----"}</p>
                    <p className="mt-2 text-xs text-[#8fa3ad]">Valid for 20 hours. Use this code while running install_service.bat.</p>
                    {pairingCode?.expiresAt ? (
                      <p className="mt-1 text-[10px] font-mono text-[#6f8792]">Expires {new Date(pairingCode.expiresAt).toLocaleString()}</p>
                    ) : null}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={copyEnrollmentToken}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#00d1ff]/35 bg-[#00d1ff]/10 px-4 py-3 text-xs font-bold uppercase tracking-wider text-[#a4e6ff] transition-all hover:border-[#00d1ff] hover:bg-[#00d1ff]/15"
                >
                  <Clipboard className="h-4 w-4" />
                  {copiedToken ? "Copied" : "Copy Pairing Code"}
                </button>
              </div>
            </div>

            {toast && (
              <p className="mx-6 mb-6 rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-xs font-mono text-amber-200 sm:mx-8">
                {toast}
              </p>
            )}

            <div className="flex flex-col gap-3 border-t border-white/10 px-6 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-8">
              <p className="text-xs text-[#8fa3ad]">SUPER_ADMIN remains reserved for the Asset Sentinel owner.</p>
              <button
                onClick={() => onNavigate("login")}
                className="rounded-lg bg-[#00d1ff] px-5 py-3 text-xs font-black uppercase tracking-wider text-[#002936] transition-all hover:bg-[#a4e6ff]"
              >
                Continue to Admin Login
              </button>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070B10] text-[#dae3ee] relative overflow-hidden">
      <SignupBackdrop />
      <main className="relative z-10 mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
        <div className="mb-5 flex items-center justify-between gap-3">
          <button
            onClick={() => onNavigate("landing")}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs font-mono text-[#bbc9cf] transition-colors hover:border-[#00d1ff]/35 hover:text-[#00d1ff]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <button
            onClick={() => onNavigate("login")}
            className="rounded-lg border border-[#00d1ff]/25 bg-[#00d1ff]/10 px-3 py-2 text-xs font-bold uppercase tracking-wider text-[#a4e6ff] transition-all hover:border-[#00d1ff]/60"
          >
            Admin Login
          </button>
        </div>

        <section className="grid flex-1 gap-5 lg:grid-cols-[0.86fr_1.28fr]">
          <aside className="rounded-lg border border-white/10 bg-[#0D141C]/90 p-5 shadow-[0_18px_60px_rgba(0,0,0,0.30)] lg:sticky lg:top-5 lg:self-start">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#00d1ff]/35 bg-[#12202A]">
                <SentinelLogo className="h-7 w-7" />
              </div>
              <div>
                <p className="text-[10px] font-mono uppercase tracking-[0.28em] text-[#00d1ff]">Enterprise Enrollment</p>
                <h1 className="mt-1 text-2xl font-black tracking-tight text-white">Asset Sentinel SaaS</h1>
              </div>
            </div>

            <p className="mt-5 max-w-xl text-sm leading-6 text-[#9fb0b8]">
              Create a company administrator workspace with protected identity, tenant-ready controls, and endpoint enrollment readiness.
            </p>

            <div className="mt-6 rounded-lg border border-[#00d1ff]/18 bg-[#07131B] p-4">
              <div className="mb-4 flex items-center justify-between text-xs font-mono">
                <span className="uppercase tracking-widest text-[#8fa3ad]">Enrollment Progress</span>
                <span className="text-[#00d1ff]">{Math.round(progressPercent)}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-[#00d1ff] transition-all duration-500" style={{ width: `${progressPercent}%` }} />
              </div>
              <Stepper activeStep={activeStep} completedSteps={completedSteps} />
            </div>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              <AssuranceCard icon={<ShieldCheck className="h-4 w-4" />} title="Secure Monitoring" />
              <AssuranceCard icon={<LockKeyhole className="h-4 w-4" />} title="JWT Protected" />
              <AssuranceCard icon={<KeyRound className="h-4 w-4" />} title="Encrypted Credentials" />
              <AssuranceCard icon={<UsersRound className="h-4 w-4" />} title="Multi Tenant Ready" />
            </div>

            <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.03] p-4">
              <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-[#8fa3ad]">Role Model</p>
              <div className="mt-3 space-y-3 text-xs text-[#bbc9cf]">
                <RoleLine label="SUPER_ADMIN" value="Asset Sentinel owner across all companies" muted />
                <RoleLine label="COMPANY_ADMIN" value="Created by signup and scoped to one company" />
              </div>
            </div>
          </aside>

          <form onSubmit={handleSubmit} className="rounded-lg border border-white/10 bg-[#0F151D]/95 shadow-[0_22px_80px_rgba(0,0,0,0.38)]">
            <div className="border-b border-white/10 px-5 py-5 sm:px-7">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-[10px] font-mono uppercase tracking-[0.26em] text-[#00d1ff]">{currentStep.eyebrow}</p>
                  <h2 className="mt-2 text-xl font-black text-white sm:text-2xl">{currentStep.title}</h2>
                </div>
                <div className="inline-flex w-fit items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-emerald-300">
                  <Sparkles className="h-3.5 w-3.5" />
                  Production Enrollment
                </div>
              </div>
            </div>

            {toast && (
              <div className="mx-5 mt-5 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-xs font-mono text-amber-200 sm:mx-7">
                <span className="inline-flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  {toast}
                </span>
              </div>
            )}

            <div className="p-5 sm:p-7">
              {currentStep.id === "company" && (
                <StepPanel>
                  <Field label="Company Name" error={errors.companyName} icon={<Building2 className="h-4 w-4" />}>
                    <input className={inputClass(errors.companyName)} value={form.companyName} onChange={(e) => updateField("companyName", e.target.value)} autoComplete="organization" />
                  </Field>
                  <Field label="Website" error={errors.companyWebsite} optional>
                    <input className={inputClass(errors.companyWebsite)} placeholder="https://company.com" value={form.companyWebsite} onChange={(e) => updateField("companyWebsite", e.target.value)} autoComplete="url" />
                  </Field>
                  <Field label="Industry" error={errors.industry}>
                    <Select value={form.industry} onChange={(value) => updateField("industry", value)} options={industries} error={errors.industry} />
                  </Field>
                  <Field label="Company Size" error={errors.companySize}>
                    <Select value={form.companySize} onChange={(value) => updateField("companySize", value)} options={companySizes} error={errors.companySize} />
                  </Field>
                  <Field label="Country" error={errors.country}>
                    <Select value={form.country} onChange={(value) => updateField("country", value)} options={countries} error={errors.country} />
                  </Field>
                </StepPanel>
              )}

              {currentStep.id === "admin" && (
                <StepPanel>
                  <Field label="Full Name" error={errors.fullName} icon={<UserRound className="h-4 w-4" />}>
                    <input className={inputClass(errors.fullName)} value={form.fullName} onChange={(e) => updateField("fullName", e.target.value)} autoComplete="name" />
                  </Field>
                  <Field label="Work Email" error={errors.workEmail} icon={<Mail className="h-4 w-4" />}>
                    <input className={inputClass(errors.workEmail)} value={form.workEmail} onChange={(e) => updateField("workEmail", e.target.value)} autoComplete="email" />
                  </Field>
                  <Field label="Mobile Number" error={errors.mobileNumber} icon={<Phone className="h-4 w-4" />}>
                    <input className={inputClass(errors.mobileNumber)} placeholder="+14155552671" value={form.mobileNumber} onChange={(e) => updateField("mobileNumber", e.target.value)} autoComplete="tel" />
                  </Field>
                  <Field label="Job Title" error={errors.jobTitle}>
                    <input className={inputClass(errors.jobTitle)} value={form.jobTitle} onChange={(e) => updateField("jobTitle", e.target.value)} />
                  </Field>
                  <Field label="Department" error={errors.department}>
                    <input className={inputClass(errors.department)} value={form.department} onChange={(e) => updateField("department", e.target.value)} />
                  </Field>
                </StepPanel>
              )}

              {currentStep.id === "security" && (
                <div className="grid gap-5">
                  <StepPanel>
                    <Field label="Username" error={errors.username}>
                      <input className={inputClass(errors.username)} value={form.username} onChange={(e) => updateField("username", e.target.value)} autoComplete="username" />
                    </Field>
                    <Field label="Password" error={errors.password}>
                      <div className="relative">
                        <input
                          className={`${inputClass(errors.password)} pr-11`}
                          type={showPassword ? "text" : "password"}
                          value={form.password}
                          onChange={(e) => updateField("password", e.target.value)}
                          autoComplete="new-password"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword((value) => !value)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-[#8fa3ad] transition-colors hover:text-[#00d1ff]"
                          aria-label={showPassword ? "Hide password" : "Show password"}
                        >
                          {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </Field>
                    <Field label="Confirm Password" error={errors.confirmPassword}>
                      <input className={inputClass(errors.confirmPassword)} type="password" value={form.confirmPassword} onChange={(e) => updateField("confirmPassword", e.target.value)} autoComplete="new-password" />
                    </Field>
                  </StepPanel>

                  <div className="grid gap-4 rounded-lg border border-white/10 bg-[#07131B] p-4 lg:grid-cols-[1fr_0.7fr]">
                    <div>
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-bold uppercase tracking-widest text-[#a4e6ff]">Password Strength</p>
                        <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${strengthBadge(passwordStrength)}`}>{passwordStrength}</span>
                      </div>
                      <div className="mt-3 grid grid-cols-5 gap-1">
                        {checks.map((check, index) => (
                          <div key={check.label} className={`h-1.5 rounded-full transition-colors ${index < validPasswordChecks ? strengthBar(passwordStrength) : "bg-white/10"}`} />
                        ))}
                      </div>
                      <div className="mt-4 grid gap-2 sm:grid-cols-2">
                        {checks.map((check) => (
                          <div key={check.label} className={`flex items-center gap-2 text-xs ${check.valid ? "text-emerald-300" : "text-[#8fa3ad]"}`}>
                            <span className={`flex h-5 w-5 items-center justify-center rounded-full border ${check.valid ? "border-emerald-400/40 bg-emerald-400/10" : "border-white/10 bg-white/[0.03]"}`}>
                              {check.valid ? <Check className="h-3.5 w-3.5" /> : null}
                            </span>
                            {check.label}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-lg border border-[#00d1ff]/20 bg-[#00d1ff]/[0.06] p-4">
                      <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#00d1ff]">Security Scope</p>
                      <p className="mt-2 text-sm font-semibold text-white">Signup creates COMPANY_ADMIN only.</p>
                      <p className="mt-2 text-xs leading-5 text-[#8fa3ad]">SUPER_ADMIN access is reserved for the Asset Sentinel owner and cannot be selected here.</p>
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <Checkbox label="I agree to the Terms of Service" checked={form.termsAccepted} error={errors.termsAccepted} onChange={(checked) => updateField("termsAccepted", checked)} />
                    <Checkbox label="I agree to the Privacy Policy" checked={form.privacyAccepted} error={errors.privacyAccepted} onChange={(checked) => updateField("privacyAccepted", checked)} />
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col-reverse gap-3 border-t border-white/10 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
              <button
                type="button"
                onClick={goBack}
                disabled={activeStep === 0 || isSubmitting}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-xs font-bold uppercase tracking-wider text-[#bbc9cf] transition-all hover:border-white/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ArrowLeft className="h-4 w-4" />
                Previous
              </button>
              {activeStep < steps.length - 1 ? (
                <button
                  type="button"
                  onClick={goNext}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-5 py-3 text-xs font-black uppercase tracking-wider text-[#002936] transition-all hover:bg-[#a4e6ff]"
                >
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-5 py-3 text-xs font-black uppercase tracking-wider text-[#002936] transition-all hover:bg-[#a4e6ff] disabled:cursor-wait disabled:opacity-65"
                >
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                  {isSubmitting ? "Creating Workspace..." : "Create Company Workspace"}
                </button>
              )}
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}

const inputClass = (error?: string) =>
  `w-full rounded-lg px-4 py-3 text-sm text-[#e8f0f6] bg-[#070B10] border ${error ? "border-red-300/60" : "border-white/10"} focus:border-[#00d1ff] focus:ring-2 focus:ring-[#00d1ff]/15 outline-none transition-all placeholder:text-[#5e707a]`;

function SignupBackdrop() {
  return (
    <>
      <div className="absolute inset-0 bg-grid opacity-35" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(0,209,255,0.10),transparent_26%),radial-gradient(circle_at_84%_18%,rgba(16,185,129,0.08),transparent_24%),linear-gradient(145deg,rgba(0,209,255,0.06),transparent_38%,rgba(15,23,42,0.28))]" />
      <div className="scanline" />
    </>
  );
}

function Stepper({ activeStep, completedSteps }: { activeStep: number; completedSteps: Set<StepId> }) {
  return (
    <div className="mt-5 space-y-3">
      {steps.map((step, index) => {
        const complete = completedSteps.has(step.id);
        const active = index === activeStep;
        return (
          <div key={step.id} className={`flex items-center gap-3 rounded-lg border px-3 py-3 transition-all ${active ? "border-[#00d1ff]/45 bg-[#00d1ff]/10" : complete ? "border-emerald-400/30 bg-emerald-400/10" : "border-white/10 bg-white/[0.025]"}`}>
            <div className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-black ${complete ? "border-emerald-400/40 bg-emerald-400/15 text-emerald-300" : active ? "border-[#00d1ff]/50 bg-[#00d1ff]/15 text-[#a4e6ff]" : "border-white/10 text-[#8fa3ad]"}`}>
              {complete ? <Check className="h-4 w-4" /> : index + 1}
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-[#8fa3ad]">{step.eyebrow}</p>
              <p className="text-sm font-bold text-white">{step.title}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StepPanel({ children }: { children: React.ReactNode }) {
  return <div className="grid animate-[fadeIn_220ms_ease-out] gap-4 md:grid-cols-2">{children}</div>;
}

function Field({ label, children, error, optional, icon }: { label: string; children: React.ReactNode; error?: string; optional?: boolean; icon?: React.ReactNode }) {
  return (
    <label className="flex min-w-0 flex-col gap-2">
      <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#9fb0b8]">
        {icon ? <span className="text-[#00d1ff]">{icon}</span> : null}
        {label}
        {optional ? <span className="font-mono text-[#5e707a]">optional</span> : null}
      </span>
      {children}
      {error ? <span className="text-xs text-red-200">{error}</span> : null}
    </label>
  );
}

function Select({ value, onChange, options, error }: { value: string; onChange: (value: string) => void; options: string[]; error?: string }) {
  return (
    <div className="relative">
      <select
        className={`${inputClass(error)} appearance-none pr-10`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8fa3ad]" />
    </div>
  );
}

function Checkbox({ label, checked, onChange, error }: { label: string; checked: boolean; onChange: (checked: boolean) => void; error?: string }) {
  return (
    <label className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm transition-all ${error ? "border-red-300/50 bg-red-400/10" : "border-white/10 bg-[#07131B] hover:border-[#00d1ff]/30"}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 h-4 w-4 accent-[#00d1ff]"
      />
      <span className="text-[#dae3ee]">
        {label}
        {error ? <span className="block text-xs text-red-200 mt-1">{error}</span> : null}
      </span>
    </label>
  );
}

function AssuranceCard({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex min-h-[4.3rem] items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#00d1ff]/25 bg-[#00d1ff]/10 text-[#a4e6ff]">
        {icon}
      </div>
      <p className="text-xs font-bold text-white">{title}</p>
    </div>
  );
}

function RoleLine({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="grid gap-1">
      <span className={`font-mono text-[10px] uppercase tracking-[0.18em] ${muted ? "text-[#6e7e87]" : "text-[#00d1ff]"}`}>{label}</span>
      <span className={muted ? "text-[#7f9099]" : "text-[#dbe8ef]"}>{value}</span>
    </div>
  );
}

function SuccessMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
      <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#8fa3ad]">{label}</p>
      <p className="mt-2 break-words text-sm font-bold text-white">{value}</p>
    </div>
  );
}

function strengthBadge(label: string) {
  if (label === "Strong") return "bg-emerald-400/15 text-emerald-300 border border-emerald-400/30";
  if (label === "Medium") return "bg-amber-400/15 text-amber-200 border border-amber-400/30";
  return "bg-red-400/15 text-red-200 border border-red-400/30";
}

function strengthBar(label: string) {
  if (label === "Strong") return "bg-emerald-300";
  if (label === "Medium") return "bg-amber-300";
  return "bg-red-300";
}

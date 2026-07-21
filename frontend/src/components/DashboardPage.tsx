import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { 
  Shield, 
  Search, 
  Filter, 
  Download, 
  ChevronLeft, 
  ChevronRight, 
  HelpCircle, 
  LogOut, 
  AlertTriangle, 
  TrendingUp, 
  Menu, 
  Laptop, 
  Smartphone, 
  Server, 
  CheckCircle2, 
  Activity, 
  Clock, 
  Database,
  RefreshCw,
  Cpu,
  MapPin,
  X,
  FileSpreadsheet,
  Zap,
  Lock,
  RotateCcw,
  Sparkles,
  Sliders,
  HardDrive,
  Layers,
  Fingerprint,
  Globe,
  ShieldAlert,
  LogIn,
  User,
  Wifi,
  WifiOff,
  MemoryStick,
  Monitor,
  BarChart3,
  Info,
  AlertCircle,
  Gauge
} from "lucide-react";
import { Asset, AssetDetailPayload, SecurityFeedItem, KPIStats } from "../types";
import { INITIAL_ASSETS } from "../data";
import { SentinelLogo } from "./SentinelLogo";
import AssetHistory from "./AssetHistory";
import { apiFetch } from "../lib/api";

interface DashboardPageProps {
  userEmail: string;
  onSignOut: () => void;
  onNavigate: (view: "landing" | "login" | "admin-signup" | "dashboard" | "super-admin" | "demo") => void;
  isDemoMode?: boolean;
}

const formatTelemetryTimestamp = (value?: string | null) => {
  if (!value) return "No data";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], {
    timeZone: "Asia/Kolkata",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
};

const formatSessionDurationSince = (value?: string | null) => {
  if (!value) return "No duration";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "No duration";
  const seconds = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
};

const formatUsageDuration = (seconds?: number | null) => {
  const totalSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${totalSeconds}s`;
};

type UsagePeriod = "current_session" | "today" | "yesterday" | "last_2_days";
type TimelineHistoryPreset = "today" | "yesterday" | "last_2_days" | "custom";

const usagePeriodLabels: Record<UsagePeriod, string> = {
  current_session: "Current Session",
  today: "Today",
  yesterday: "Yesterday",
  last_2_days: "Last 2 Days",
};

const timelineHistoryLabels: Record<TimelineHistoryPreset, string> = {
  today: "Today",
  yesterday: "Yesterday",
  last_2_days: "Last 2 Days",
  custom: "Custom Range",
};
const LIVE_APPLICATION_TIMELINE_POLL_MS = 3000;

const appAccentClasses = [
  "from-[#38BDF8] to-[#2563EB] text-sky-100",
  "from-[#22C55E] to-[#15803D] text-emerald-100",
  "from-[#F59E0B] to-[#B45309] text-amber-50",
  "from-[#A78BFA] to-[#6D28D9] text-violet-50",
  "from-[#FB7185] to-[#BE123C] text-rose-50",
];

const telemetryTimeMs = (value?: string | null) => {
  if (!value) return 0;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
};

const newestTelemetryValue = (primary?: string | null, fallback?: string | null) => (
  telemetryTimeMs(primary) >= telemetryTimeMs(fallback) ? primary : fallback
);

const sortNewestTelemetry = <T extends { timestamp?: string | null }>(items: T[]) => (
  [...items].sort((a, b) => telemetryTimeMs(b.timestamp) - telemetryTimeMs(a.timestamp))
);

const resolveActivePath = (asset: Asset) => {
  const activePath = asset.currentWebsite?.trim();
  return activePath && activePath !== "-" ? activePath : "No Active File";
};

const getThreatLevel = (asset: Asset) => {
  if (typeof asset.threatScore === "number") return asset.threatScore;
  if (asset.alertStatus === "critical") return 92;
  if (asset.alertStatus === "warning") return 54;
  return 12;
};

const DetailField = ({ label, value, accent = false, compact = false }: { label: string; value?: React.ReactNode; accent?: boolean; compact?: boolean }) => (
  <div className={`group flex min-w-0 flex-col gap-1 rounded-lg border border-[#2B3752]/70 bg-[#0F1728]/70 ${compact ? "px-3 py-2" : "px-3.5 py-3"} transition-all duration-200 hover:border-[#38BDF8]/40 hover:bg-[#1B2338]`}>
    <span className={`${compact ? "text-[9px]" : "text-[10px]"} font-semibold uppercase tracking-[0.16em] text-[#8EA0B8]`}>{label}</span>
    <span className={`${accent ? "text-[#38BDF8]" : "text-[#F8FAFC]"} text-sm font-semibold leading-snug break-words`}>{value ?? "No data"}</span>
  </div>
);

const DetailSection = ({ title, icon, children, compact = false }: { title: string; icon: React.ReactNode; children: React.ReactNode; compact?: boolean }) => (
  <section className={`animate-[fadeIn_420ms_ease-out] rounded-2xl border border-[#2B3752] bg-[#141B2D] ${compact ? "p-3.5" : "p-5"} shadow-[0_18px_50px_rgba(0,0,0,0.26)] text-[12px]`}>
    <div className={`${compact ? "mb-3" : "mb-5"} flex items-center gap-3`}>
      <div className={`flex ${compact ? "h-8 w-8" : "h-10 w-10"} items-center justify-center rounded-xl border border-[#38BDF8]/25 bg-[#38BDF8]/10`}>
        {icon}
      </div>
      <h3 className={`${compact ? "text-lg sm:text-xl" : "text-xl sm:text-2xl"} font-bold tracking-tight text-white`}>{title}</h3>
    </div>
    {children}
  </section>
);

const formatPercent = (value?: string | number | null) => {
  if (value === undefined || value === null || value === "") return "No data";
  const numeric = Number(String(value).replace("%", ""));
  return Number.isFinite(numeric) ? `${numeric.toFixed(numeric % 1 === 0 ? 0 : 1)}%` : String(value);
};

const formatGb = (value?: string | number | null) => {
  if (value === undefined || value === null || value === "") return "No data";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)} GB` : String(value);
};

const severityStyles: Record<string, string> = {
  LOW: "bg-blue-500/10 text-sky-300 border-sky-500/30",
  MEDIUM: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  HIGH: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  CRITICAL: "bg-red-500/10 text-red-300 border-red-500/30",
};

const statusStyles: Record<string, string> = {
  Online: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  Offline: "bg-red-500/10 text-red-300 border-red-500/30",
  Idle: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  Overload: "bg-red-500/10 text-red-300 border-red-500/30",
};

const StatusChip = ({ status }: { status: Asset["status"] }) => (
  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyles[status] || statusStyles.Offline}`}>
    {status === "Online" ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
    {status}
  </span>
);

const assetIdentity = (asset?: Asset | null) => asset?.deviceId || asset?.hostname || "";

const MiniLineChart = ({ title, icon, data, color = "#38bdf8" }: { title: string; icon: React.ReactNode; data: Array<{ timestamp?: string; value?: string | number }>; color?: string }) => {
  const points = data
    .map((item) => Number(item.value))
    .filter((value) => Number.isFinite(value));
  const path = points.length > 1
    ? points.map((value, index) => {
        const x = (index / Math.max(points.length - 1, 1)) * 220;
        const y = 76 - (Math.min(100, Math.max(0, value)) / 100) * 64;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      }).join(" ")
    : "";
  const latest = points.length ? points[points.length - 1] : null;

  return (
    <div className="min-h-[156px] rounded-xl border border-[#2B3752] bg-[#0F1728] p-4 transition-all duration-200 hover:bg-[#1B2338]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[#d6e3ec] text-xs font-semibold">{icon}{title}</div>
        <span className="text-[11px] text-[#9fb0bd]">{latest === null ? "No data" : `${latest.toFixed(1)}%`}</span>
      </div>
      {points.length > 1 ? (
        <svg viewBox="0 0 220 84" className="h-20 w-full overflow-visible">
          <path d="M 0 76 L 220 76" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <path d={path} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ) : (
        <div className="flex h-20 items-center justify-center rounded-lg border border-dashed border-[#2B3752] text-[11px] text-[#8EA0B8]">No database samples</div>
      )}
    </div>
  );
};

const MiniBarChart = ({ title, icon, data, colorClass = "bg-sky-400" }: { title: string; icon: React.ReactNode; data: Array<{ label: string; value: number }>; colorClass?: string }) => {
  const max = Math.max(...data.map((item) => item.value), 1);
  return (
    <div className="min-h-[156px] rounded-xl border border-[#2B3752] bg-[#0F1728] p-4 transition-all duration-200 hover:bg-[#1B2338]">
      <div className="mb-3 flex items-center gap-2 text-[#d6e3ec] text-xs font-semibold">{icon}{title}</div>
      {data.length ? (
        <div className="space-y-2">
          {data.slice(0, 5).map((item) => (
            <div key={`${title}-${item.label}`} className="grid grid-cols-[96px_1fr_28px] items-center gap-2 text-[11px]">
              <span className="truncate text-[#9fb0bd]">{item.label}</span>
              <div className="h-2 rounded-full bg-white/5">
                <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${Math.max(6, (item.value / max) * 100)}%` }} />
              </div>
              <span className="text-right text-[#d6e3ec]">{item.value}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex h-20 items-center justify-center rounded-lg border border-dashed border-[#2B3752] text-[11px] text-[#8EA0B8]">No database events</div>
      )}
    </div>
  );
};

const ApplicationUsageAnalytics = ({
  detail,
  selectedPeriod,
  onPeriodChange,
}: {
  detail: AssetDetailPayload | null;
  selectedPeriod: UsagePeriod;
  onPeriodChange: (period: UsagePeriod) => void;
}) => {
  const periodPayload = detail?.charts.application_usage_periods?.[selectedPeriod];
  const usage = periodPayload?.items || detail?.charts.application_usage || [];
  const summary = periodPayload?.summary || detail?.charts.application_usage_summary || {};
  const totalSeconds = summary.total_session_duration_seconds || Math.max(...usage.map((item) => item.total_duration_seconds || item.value || 0), 0);
  const maxSeconds = Math.max(...usage.map((item) => item.total_duration_seconds || item.value || 0), 1);

  return (
    <section className="animate-[fadeIn_520ms_ease-out] rounded-2xl border border-[#2B3752] bg-[#141B2D] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.26)]">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#38BDF8]/25 bg-[#38BDF8]/10">
            <BarChart3 className="h-5 w-5 text-sky-300" />
          </div>
          <div>
            <h3 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Application Usage</h3>
            <p className="text-sm text-[#A8B3C7]">{usagePeriodLabels[selectedPeriod]} foreground, productive, and idle application time.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:min-w-[520px]">
          <DetailField label="Total Session" value={formatUsageDuration(totalSeconds)} accent compact />
          <DetailField label="Login Start" value={formatTelemetryTimestamp(summary.session_started_at)} compact />
          <DetailField label="Last Updated" value={formatTelemetryTimestamp(summary.last_updated_at)} compact />
        </div>
      </div>
      <div className="mb-5 flex flex-wrap gap-2">
        {(Object.keys(usagePeriodLabels) as UsagePeriod[]).map((period) => (
          <button
            key={period}
            onClick={() => onPeriodChange(period)}
            className={`rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${
              selectedPeriod === period
                ? "border-[#38BDF8]/55 bg-[#38BDF8]/15 text-[#7DD3FC]"
                : "border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] hover:border-[#38BDF8]/35 hover:text-white"
            }`}
          >
            {usagePeriodLabels[period]}
          </button>
        ))}
      </div>

      {usage.length ? (
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          {usage.slice(0, 8).map((item, index) => {
            const seconds = item.total_duration_seconds || item.value || 0;
            const percent = Number.isFinite(item.percentage_of_session)
              ? Math.max(0, Math.min(100, item.percentage_of_session || 0))
              : Math.max(0, Math.min(100, (seconds / maxSeconds) * 100));
            const width = Math.max(5, percent);
            const appName = item.application_name || item.label || "Unknown";
            return (
              <div key={`${appName}-${index}`} className="rounded-2xl border border-[#2B3752] bg-[linear-gradient(145deg,#0F1728_0%,#101827_58%,#0B1220_100%)] p-4 shadow-[0_16px_44px_rgba(2,8,23,0.22)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[#38BDF8]/40 hover:shadow-[0_18px_54px_rgba(56,189,248,0.12)]">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${appAccentClasses[index % appAccentClasses.length]} text-sm font-black shadow-[0_0_20px_rgba(56,189,248,0.16)]`}>
                      {appName.slice(0, 1).toUpperCase()}
                    </span>
                    <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-white">{appName}</p>
                    <p className="mt-1 truncate text-[11px] text-[#8EA0B8]">{item.window_title || item.process_path || "Foreground window activity"}</p>
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full border border-[#38BDF8]/30 bg-[#38BDF8]/10 px-2.5 py-1 text-xs font-bold text-[#7DD3FC]">
                    {formatUsageDuration(seconds)}
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-[#243044]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#38BDF8] via-[#22C55E] to-[#FACC15] shadow-[0_0_18px_rgba(56,189,248,0.28)]"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
                  <span className="rounded-lg bg-white/[0.03] px-2 py-1 text-[#A8B3C7]">Open <b className="text-white">{formatUsageDuration(seconds)}</b></span>
                  <span className="rounded-lg bg-emerald-500/10 px-2 py-1 text-emerald-200">Active <b>{formatUsageDuration(item.active_duration_seconds || item.productive_duration_seconds || 0)}</b></span>
                  <span className="rounded-lg bg-amber-500/10 px-2 py-1 text-amber-200">Idle <b>{formatUsageDuration(item.idle_duration_seconds || 0)}</b></span>
                </div>
                <div className="mt-2 flex justify-end text-[11px] text-[#8EA0B8]">
                  <span>{percent.toFixed(percent >= 10 ? 0 : 1)}% of session</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-[#2B3752] bg-[#0F1728]/70 p-5 text-sm text-[#8EA0B8]">
          No application duration data is available yet. Usage appears after foreground application changes are recorded.
        </div>
      )}
    </section>
  );
};

const ProductivityInsights = ({ detail, selectedPeriod }: { detail: AssetDetailPayload | null; selectedPeriod: UsagePeriod }) => {
  const periodPayload = detail?.charts.application_usage_periods?.[selectedPeriod];
  const summary = periodPayload?.summary || detail?.charts.application_usage_summary || {};
  const totalSeconds = summary.total_session_duration_seconds || 0;
  const activeSeconds = summary.active_working_seconds || 0;
  const idleSeconds = summary.idle_seconds || 0;
  const lockedSeconds = summary.locked_seconds || 0;
  const productivity = Math.max(0, Math.min(100, summary.productivity_percentage || 0));

  return (
    <section id="productivity-insights-section" className="animate-[fadeIn_520ms_ease-out] rounded-3xl border border-violet-300/30 bg-[radial-gradient(circle_at_top_right,rgba(167,139,250,0.18),transparent_34%),linear-gradient(135deg,#151126_0%,#111827_52%,#071B16_100%)] p-5 shadow-[0_0_0_1px_rgba(167,139,250,0.08),0_24px_70px_rgba(20,184,166,0.12),0_0_46px_rgba(167,139,250,0.14)]">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-violet-300/45 bg-violet-400/12 shadow-[0_0_28px_rgba(167,139,250,0.26)]">
          <Zap className="h-5 w-5 text-violet-200" />
        </div>
        <div>
          <h3 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Productivity Insights</h3>
          <p className="text-sm text-violet-100/70">{usagePeriodLabels[selectedPeriod]} active work versus idle and locked time.</p>
        </div>
        </div>
        <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-full border border-emerald-300/40 bg-emerald-300/10 shadow-[inset_0_0_24px_rgba(52,211,153,0.12),0_0_34px_rgba(167,139,250,0.22)]">
          <div className="text-center">
            <div className="text-3xl font-black text-emerald-100">{productivity.toFixed(productivity >= 10 ? 0 : 1)}%</div>
            <div className="mt-1 text-[10px] font-bold uppercase tracking-[0.18em] text-violet-200/70">Score</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[0.85fr_1.15fr]">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-violet-300/20 bg-white/[0.04] p-4 backdrop-blur">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-violet-200/60">Total Device Time</div>
            <div className="mt-2 text-2xl font-black text-violet-100">{formatUsageDuration(totalSeconds)}</div>
          </div>
          <div className="rounded-xl border border-emerald-300/20 bg-white/[0.04] p-4 backdrop-blur">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-200/60">Productivity</div>
            <div className="mt-2 text-2xl font-black text-emerald-100">{productivity.toFixed(productivity >= 10 ? 0 : 1)}%</div>
          </div>
          <div className="rounded-xl border border-violet-300/20 bg-white/[0.04] p-4 backdrop-blur">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-violet-200/60">Idle</div>
            <div className="mt-2 text-2xl font-black text-violet-100">{formatUsageDuration(idleSeconds)}</div>
          </div>
          <div className="rounded-xl border border-slate-300/20 bg-white/[0.04] p-4 backdrop-blur">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-200/60">Locked</div>
            <div className="mt-2 text-2xl font-black text-slate-100">{formatUsageDuration(lockedSeconds)}</div>
          </div>
        </div>
        <div className="rounded-xl border border-violet-300/20 bg-white/[0.04] p-4 backdrop-blur">
          <div className="mb-4 flex items-center justify-between text-xs font-semibold text-violet-100/75">
            <span>Active vs Idle</span>
            <span>{formatUsageDuration(activeSeconds)} active / {formatUsageDuration(idleSeconds)} idle / {formatUsageDuration(lockedSeconds)} locked</span>
          </div>
          <div className="space-y-3">
            <div>
              <div className="mb-1 flex justify-between text-[11px] text-emerald-100/75"><span>Active Work</span><span>{formatUsageDuration(activeSeconds)}</span></div>
              <div className="h-3 overflow-hidden rounded-full bg-emerald-950/40">
                <div className="h-full rounded-full bg-gradient-to-r from-emerald-300 via-teal-300 to-violet-300 shadow-[0_0_18px_rgba(52,211,153,0.34)]" style={{ width: `${Math.max(3, productivity)}%` }} />
              </div>
            </div>
            <div>
              <div className="mb-1 flex justify-between text-[11px] text-violet-100/70"><span>Idle</span><span>{formatUsageDuration(idleSeconds)}</span></div>
              <div className="h-3 overflow-hidden rounded-full bg-violet-950/40">
                <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-slate-500" style={{ width: `${Math.max(3, Math.min(100, (idleSeconds / Math.max(totalSeconds, 1)) * 100))}%` }} />
              </div>
            </div>
            <div>
              <div className="mb-1 flex justify-between text-[11px] text-slate-100/70"><span>Locked</span><span>{formatUsageDuration(lockedSeconds)}</span></div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-900/60">
                <div className="h-full rounded-full bg-gradient-to-r from-slate-400 to-slate-600" style={{ width: `${Math.max(3, Math.min(100, (lockedSeconds / Math.max(totalSeconds, 1)) * 100))}%` }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

type BackendAlertRecord = {
  id: string;
  alertType: string;
  deviceName: string;
  employee: string;
  severity: string;
  time: string;
  description: string;
  previousValue: string;
  currentValue: string;
  alertStatus: string;
  raw: any;
};

type PersistedDashboardState = {
  selectedHostname?: string | null;
  selectedDeviceId?: string | null;
  searchQuery?: string;
  currentPage?: number;
  workspaceScrollTop?: number;
  detailScrollTop?: number;
};

const DASHBOARD_STATE_KEY = "sentinel_dashboard_state";

const readDashboardState = (): PersistedDashboardState => {
  try {
    return JSON.parse(localStorage.getItem(DASHBOARD_STATE_KEY) || "{}");
  } catch {
    return {};
  }
};

const writeDashboardState = (patch: PersistedDashboardState) => {
  const current = readDashboardState();
  localStorage.setItem(DASHBOARD_STATE_KEY, JSON.stringify({ ...current, ...patch }));
};

const newestApplicationEntry = (entries: Array<Record<string, any>>) => {
  return sortNewestTelemetry(entries).find((entry) => entry && entry.timestamp);
};

type TimelineEntry = {
  timestamp?: string | null;
  application?: string | null;
  application_name?: string | null;
  window_title?: string | null;
  process_path?: string | null;
};

type TimelineInterval = TimelineEntry & {
  endTimestamp?: string | null;
  durationSeconds?: number | null;
};

const appTimelineTitle = (entry: TimelineEntry) => (
  entry.application || entry.application_name || entry.window_title || entry.process_path || "Application changed"
);

const appTimelineDetail = (entry: TimelineEntry) => (
  entry.window_title || entry.process_path || "Foreground application event"
);

const timeOnlyLabel = (value?: string | null) => {
  if (!value) return "Now";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Now";
  return parsed.toLocaleTimeString([], { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" });
};

const timeInputLabel = (value: string) => {
  const [hoursRaw, minutesRaw] = value.split(":").map(Number);
  if (!Number.isFinite(hoursRaw) || !Number.isFinite(minutesRaw)) return value;
  const suffix = hoursRaw >= 12 ? "PM" : "AM";
  const hours = hoursRaw % 12 || 12;
  return `${String(hours).padStart(2, "0")}:${String(minutesRaw).padStart(2, "0")} ${suffix}`;
};

const toDateTimeInputValue = (date: Date) => {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const datePartFromDateTimeValue = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return toDateTimeInputValue(new Date()).slice(0, 10);
  return toDateTimeInputValue(parsed).slice(0, 10);
};

const timePartFromDateTimeValue = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "00:00";
  return toDateTimeInputValue(parsed).slice(11, 16);
};

const withDatePart = (value: string, dateValue: string) => {
  const timeValue = timePartFromDateTimeValue(value);
  return `${dateValue}T${timeValue}`;
};

const withTimePart = (value: string, timeValue: string) => {
  const dateValue = datePartFromDateTimeValue(value);
  return `${dateValue}T${timeValue}`;
};

const historyRangeLabel = (startValue: string, endValue: string) => {
  const start = new Date(startValue);
  const end = new Date(endValue);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "Selected range";
  return `${formatTelemetryTimestamp(start.toISOString())} - ${formatTelemetryTimestamp(end.toISOString())}`;
};

const localDayBounds = (offsetDays: number) => {
  const start = new Date();
  start.setDate(start.getDate() - offsetDays);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return { startMs: start.getTime(), endMs: end.getTime() };
};

const timelineHistoryBounds = (preset: TimelineHistoryPreset, customStart: string, customEnd: string) => {
  if (preset === "custom") {
    const start = new Date(customStart);
    const end = new Date(customEnd);
    return {
      startMs: Number.isNaN(start.getTime()) ? 0 : start.getTime(),
      endMs: Number.isNaN(end.getTime()) ? 0 : end.getTime(),
      label: historyRangeLabel(customStart, customEnd),
    };
  }
  if (preset === "yesterday") {
    const bounds = localDayBounds(1);
    return { ...bounds, label: "Yesterday" };
  }
  if (preset === "last_2_days") {
    const yesterday = localDayBounds(1);
    return { startMs: yesterday.startMs, endMs: Date.now(), label: "Last 2 Days" };
  }
  const bounds = localDayBounds(0);
  return { startMs: bounds.startMs, endMs: Date.now(), label: "Today" };
};

const filterTimelineByHistoryRange = (
  entries: TimelineEntry[],
  preset: TimelineHistoryPreset,
  customStart: string,
  customEnd: string,
) => {
  const { startMs, endMs } = timelineHistoryBounds(preset, customStart, customEnd);
  if (!startMs || !endMs || endMs < startMs) return [];
  return entries.filter((entry) => {
    const stamp = telemetryTimeMs(entry.timestamp);
    return stamp >= startMs && stamp <= endMs;
  });
};

const timelineAccentClasses = [
  "border-sky-400/35 bg-sky-400/10 text-sky-200 shadow-[0_10px_30px_rgba(56,189,248,0.12)]",
  "border-emerald-400/30 bg-emerald-400/10 text-emerald-200 shadow-[0_10px_30px_rgba(52,211,153,0.1)]",
  "border-amber-300/30 bg-amber-300/10 text-amber-100 shadow-[0_10px_30px_rgba(245,158,11,0.1)]",
  "border-violet-300/30 bg-violet-300/10 text-violet-100 shadow-[0_10px_30px_rgba(167,139,250,0.1)]",
  "border-rose-300/30 bg-rose-300/10 text-rose-100 shadow-[0_10px_30px_rgba(251,113,133,0.1)]",
];

const hashText = (value: string) => (
  value.split("").reduce((total, char) => total + char.charCodeAt(0), 0)
);

const timelineAccentFor = (appName: string) => timelineAccentClasses[hashText(appName) % timelineAccentClasses.length];

const timelineIconFor = (appName: string) => {
  const lowered = appName.toLowerCase();
  if (lowered.includes("chrome") || lowered.includes("edge") || lowered.includes("firefox") || lowered.includes("browser")) return <Globe className="h-4 w-4" />;
  if (lowered.includes("code") || lowered.includes("studio")) return <Monitor className="h-4 w-4" />;
  if (lowered.includes("excel") || lowered.includes("sheet")) return <FileSpreadsheet className="h-4 w-4" />;
  if (lowered.includes("explorer") || lowered.includes("folder")) return <Database className="h-4 w-4" />;
  return <Activity className="h-4 w-4" />;
};

const buildTimelineIntervals = (entries: TimelineEntry[], fallbackEndMs: number): TimelineInterval[] => {
  const sorted = [...entries].sort((a, b) => telemetryTimeMs(a.timestamp) - telemetryTimeMs(b.timestamp));
  return sorted.map((entry, index) => {
    const startMs = telemetryTimeMs(entry.timestamp);
    const nextMs = telemetryTimeMs(sorted[index + 1]?.timestamp);
    const endMs = nextMs || fallbackEndMs || 0;
    const durationSeconds = startMs && endMs && endMs > startMs ? Math.floor((endMs - startMs) / 1000) : null;
    return {
      ...entry,
      endTimestamp: endMs ? new Date(endMs).toISOString() : null,
      durationSeconds,
    };
  });
};

const parseTimeValue = (value: string) => {
  const [hoursRaw, minutesRaw] = value.split(":").map(Number);
  const hours = Number.isFinite(hoursRaw) ? Math.max(0, Math.min(23, hoursRaw)) : 0;
  const minutes = Number.isFinite(minutesRaw) ? Math.max(0, Math.min(59, minutesRaw)) : 0;
  return { hours, minutes };
};

const toTimeValue = (hours: number, minutes: number) => (
  `${String((hours + 24) % 24).padStart(2, "0")}:${String(Math.max(0, Math.min(59, minutes))).padStart(2, "0")}`
);

const ClockTimePicker = React.memo(function ClockTimePicker({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [mode, setMode] = useState<"hour" | "minute">("hour");
  const { hours, minutes } = parseTimeValue(value);
  const isPm = hours >= 12;
  const displayHour = hours % 12 || 12;
  const minuteOptions = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

  const setHour = (hour12: number) => {
    const nextHour = (isPm ? 12 : 0) + (hour12 % 12);
    onChange(toTimeValue(nextHour, minutes));
    setMode("minute");
  };

  const setMinute = (minute: number) => {
    onChange(toTimeValue(hours, minute));
  };

  const setPeriod = (period: "AM" | "PM") => {
    const hour12 = hours % 12;
    onChange(toTimeValue((period === "PM" ? 12 : 0) + hour12, minutes));
  };

  const dialValues = mode === "hour"
    ? Array.from({ length: 12 }, (_, index) => index + 1)
    : minuteOptions;

  return (
    <div className="rounded-2xl border border-[#2B3752] bg-[#0B1220]/72 p-4 shadow-[inset_0_0_28px_rgba(56,189,248,0.05)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#8EA0B8]">{label}</span>
        <div className="inline-flex rounded-lg border border-[#2B3752] bg-[#101827] p-1">
          {(["AM", "PM"] as const).map((period) => (
            <button
              key={period}
              onClick={() => setPeriod(period)}
              className={`h-7 rounded-md px-2.5 text-[10px] font-black transition-colors ${
                (period === "PM") === isPm
                  ? "bg-emerald-300/18 text-emerald-100"
                  : "text-[#8EA0B8] hover:text-white"
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4 grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-xl border border-[#38BDF8]/25 bg-[#07111F]/85 px-3 py-3 text-center">
        <button
          onClick={() => setMode("hour")}
          className={`rounded-lg px-3 py-2 text-3xl font-black tabular-nums transition-colors ${mode === "hour" ? "bg-[#38BDF8]/16 text-[#BAE6FD]" : "text-white hover:bg-white/[0.04]"}`}
        >
          {String(displayHour).padStart(2, "0")}
        </button>
        <span className="text-3xl font-black text-[#64748B]">:</span>
        <button
          onClick={() => setMode("minute")}
          className={`rounded-lg px-3 py-2 text-3xl font-black tabular-nums transition-colors ${mode === "minute" ? "bg-amber-300/16 text-amber-100" : "text-white hover:bg-white/[0.04]"}`}
        >
          {String(minutes).padStart(2, "0")}
        </button>
      </div>

      <div className="relative mx-auto h-56 w-56 rounded-full border border-[#38BDF8]/20 bg-[radial-gradient(circle,#111827_0%,#0B1220_58%,#07111F_100%)] shadow-[inset_0_0_34px_rgba(15,23,42,0.9),0_0_30px_rgba(56,189,248,0.08)]">
        <span className="absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#38BDF8]" />
        {dialValues.map((dialValue, index) => {
          const total = dialValues.length;
          const angle = ((index / total) * 360) - 90;
          const radius = 88;
          const x = Math.cos((angle * Math.PI) / 180) * radius;
          const y = Math.sin((angle * Math.PI) / 180) * radius;
          const selected = mode === "hour" ? dialValue === displayHour : dialValue === minutes;
          return (
            <button
              key={`${mode}-${dialValue}`}
              onClick={() => mode === "hour" ? setHour(dialValue) : setMinute(dialValue)}
              className={`absolute flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full text-sm font-black tabular-nums transition-colors ${
                selected
                  ? "bg-[#38BDF8] text-[#03121F] shadow-[0_0_18px_rgba(56,189,248,0.42)]"
                  : "text-[#CBD5E1] hover:bg-white/[0.07] hover:text-white"
              }`}
              style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)` }}
            >
              {mode === "minute" ? String(dialValue).padStart(2, "0") : dialValue}
            </button>
          );
        })}
      </div>
    </div>
  );
});

const SUPPORT_CATEGORIES = [
  "Agent Issue",
  "Device Offline",
  "Login Tracking Issue",
  "Application Monitoring Issue",
  "Performance Issue",
  "Account Issue",
  "Other",
];

const SUPPORT_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function DashboardPage({ userEmail, onSignOut, onNavigate, isDemoMode = false }: DashboardPageProps) {
  // Master fleet list held in state for fully reactive user experiences
  const [assets, setAssets] = useState<Asset[]>(() => isDemoMode ? INITIAL_ASSETS : []);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [selectedAssetDetail, setSelectedAssetDetail] = useState<AssetDetailPayload | null>(null);
  const [selectedUsagePeriod, setSelectedUsagePeriod] = useState<UsagePeriod>("current_session");
  const [assetDetailLoading, setAssetDetailLoading] = useState(false);
  const [isCriticalAlertsOpen, setIsCriticalAlertsOpen] = useState(false);
  const [selectedCriticalAlert, setSelectedCriticalAlert] = useState<BackendAlertRecord | null>(null);
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Record<string, boolean>>({});
  const [isMonitoringOpen, setIsMonitoringOpen] = useState(false);
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const defaultHistoryEnd = useMemo(() => new Date(), []);
  const defaultHistoryStart = useMemo(() => {
    const value = new Date(defaultHistoryEnd);
    value.setHours(Math.max(0, value.getHours() - 2), value.getMinutes(), 0, 0);
    return value;
  }, [defaultHistoryEnd]);
  const [timelineHistoryPreset, setTimelineHistoryPreset] = useState<TimelineHistoryPreset>("today");
  const [pendingTimelineHistoryPreset, setPendingTimelineHistoryPreset] = useState<TimelineHistoryPreset>("today");
  const [customHistoryStart, setCustomHistoryStart] = useState(() => toDateTimeInputValue(defaultHistoryStart));
  const [customHistoryEnd, setCustomHistoryEnd] = useState(() => toDateTimeInputValue(defaultHistoryEnd));
  const [pendingCustomHistoryStart, setPendingCustomHistoryStart] = useState(() => toDateTimeInputValue(defaultHistoryStart));
  const [pendingCustomHistoryEnd, setPendingCustomHistoryEnd] = useState(() => toDateTimeInputValue(defaultHistoryEnd));
  const [isTimelineSelectorOpen, setIsTimelineSelectorOpen] = useState(false);
  const [isTimelineHistoryOpen, setIsTimelineHistoryOpen] = useState(false);
  const [isSupportCenterOpen, setIsSupportCenterOpen] = useState(false);
  const [isRaiseTicketOpen, setIsRaiseTicketOpen] = useState(false);
  const [isEmailSupportOpen, setIsEmailSupportOpen] = useState(false);
  const [supportMessage, setSupportMessage] = useState("");
  const [supportError, setSupportError] = useState("");
  const [supportBusy, setSupportBusy] = useState(false);
  const [ticketForm, setTicketForm] = useState({
    title: "",
    category: "Agent Issue",
    priority: "MEDIUM",
    relatedDevice: "",
    description: "",
  });
  const [emailSupportForm, setEmailSupportForm] = useState({
    subject: "",
    priority: "MEDIUM",
    message: "",
  });
  const persistedDashboardState = useMemo(() => readDashboardState(), []);
  const [searchQuery, setSearchQuery] = useState(() => isDemoMode ? "" : (persistedDashboardState.searchQuery || ""));
  const [currentPage, setCurrentPage] = useState(() => isDemoMode ? 1 : (persistedDashboardState.currentPage || 1));
  const [liveLogs, setLiveLogs] = useState<SecurityFeedItem[]>(() => {
    // Starting logs pool
    return [
      ...(isDemoMode ? [{ timestamp: "08:15:02", node: "SYSTEM", message: "Demo telemetry stream ready.", type: "info" as const }] : [])
    ];
  });
  const [alertRecords, setAlertRecords] = useState<BackendAlertRecord[]>([]);

  // Local state to track tactical operation overrides and custom user-generated logs
  const [localLogs, setLocalLogs] = useState<SecurityFeedItem[]>([]);
  const [localOverrides, setLocalOverrides] = useState<Record<string, Partial<Asset>>>({});

  // Unified list of active log lines combined together
  const displayedLogs = useMemo(() => {
    return [...localLogs, ...liveLogs];
  }, [localLogs, liveLogs]);

  const applicationTimelineEntries = useMemo<TimelineEntry[]>(() => {
    const entries = selectedAssetDetail?.application_timeline || selectedAsset?.applicationHistory || [];
    return sortNewestTelemetry(entries as TimelineEntry[]);
  }, [selectedAssetDetail, selectedAsset]);

  const liveApplicationTimeline = useMemo(() => (
    applicationTimelineEntries.slice(0, 60)
  ), [applicationTimelineEntries]);

  const selectedTimelineHistoryBounds = useMemo(() => (
    timelineHistoryBounds(timelineHistoryPreset, customHistoryStart, customHistoryEnd)
  ), [timelineHistoryPreset, customHistoryStart, customHistoryEnd]);

  const filteredApplicationTimeline = useMemo(() => (
    filterTimelineByHistoryRange(applicationTimelineEntries, timelineHistoryPreset, customHistoryStart, customHistoryEnd)
  ), [applicationTimelineEntries, timelineHistoryPreset, customHistoryStart, customHistoryEnd]);

  const filteredTimelineIntervals = useMemo(() => (
    buildTimelineIntervals(filteredApplicationTimeline, selectedTimelineHistoryBounds.endMs)
  ), [filteredApplicationTimeline, selectedTimelineHistoryBounds.endMs]);

  useEffect(() => {
    if (isDemoMode) return;
    writeDashboardState({ searchQuery, currentPage });
  }, [searchQuery, currentPage, isDemoMode]);

  useEffect(() => () => {
    window.clearTimeout(workspaceScrollWriteRef.current);
    window.clearTimeout(detailScrollWriteRef.current);
  }, []);

  useEffect(() => {
    if (isDemoMode || restoredWorkspaceScrollRef.current || !workspaceRef.current) return;
    const scrollTop = readDashboardState().workspaceScrollTop;
    if (typeof scrollTop === "number") {
      requestAnimationFrame(() => {
        if (workspaceRef.current) {
          workspaceRef.current.scrollTop = scrollTop;
          restoredWorkspaceScrollRef.current = true;
        }
      });
    } else {
      restoredWorkspaceScrollRef.current = true;
    }
  }, [assets.length, isDemoMode]);

  useEffect(() => {
    if (isDemoMode || !selectedAsset || restoredDetailScrollRef.current || !assetDetailDrawerRef.current) return;
    const scrollTop = readDashboardState().detailScrollTop;
    if (typeof scrollTop === "number") {
      requestAnimationFrame(() => {
        if (assetDetailDrawerRef.current) {
          assetDetailDrawerRef.current.scrollTop = scrollTop;
          restoredDetailScrollRef.current = true;
        }
      });
    } else {
      restoredDetailScrollRef.current = true;
    }
  }, [selectedAsset?.hostname, selectedAssetDetail, isDemoMode]);

  // Dynamic simulation dials state for the active asset details window (fluctuates in real-time)
  const [telemetryCPU, setTelemetryCPU] = useState(34);
  const [telemetryRAM, setTelemetryRAM] = useState(58);
  const [telemetryNET, setTelemetryNET] = useState(120);

  // States specifically for the Demo mode graphs and active hardware cards
  const [ramValue, setRamValue] = useState(72);
  const [biosHash, setBiosHash] = useState("0x0F3C99B2");
  const [chartWavePath, setChartWavePath] = useState("");
  const [chartGridCells, setChartGridCells] = useState<string[]>([]);

  // AI Forensics audit states
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditReport, setAuditReport] = useState<string | null>(null);
  const [auditRiskScore, setAuditRiskScore] = useState<number | null>(null);
  const [auditSeverity, setAuditSeverity] = useState<string | null>(null);
  const assetsTableRef = useRef<HTMLDivElement | null>(null);
  const workspaceRef = useRef<HTMLDivElement | null>(null);
  const assetDetailDrawerRef = useRef<HTMLDivElement | null>(null);
  const restoredWorkspaceScrollRef = useRef(false);
  const restoredDetailScrollRef = useRef(false);
  const workspaceScrollWriteRef = useRef(0);
  const detailScrollWriteRef = useRef(0);

  const persistScrollPosition = useCallback((key: "workspaceScrollTop" | "detailScrollTop", value: number) => {
    if (isDemoMode) return;
    const ref = key === "workspaceScrollTop" ? workspaceScrollWriteRef : detailScrollWriteRef;
    window.clearTimeout(ref.current);
    ref.current = window.setTimeout(() => {
      writeDashboardState({ [key]: value });
    }, 180);
  }, [isDemoMode]);

  const handleShowDevices = () => {
    setSearchQuery("");
    setCurrentPage(1);
    if (!isDemoMode) writeDashboardState({ selectedHostname: null, selectedDeviceId: null, searchQuery: "", currentPage: 1 });
    setSelectedAsset(null);
    assetsTableRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleCloseAssetDetail = () => {
    if (!isDemoMode) writeDashboardState({ selectedHostname: null, selectedDeviceId: null, detailScrollTop: 0 });
    setSelectedAsset(null);
    setSelectedAssetDetail(null);
  };

  const handleSidebarAction = (action: () => void) => {
    action();
    setIsMobileSidebarOpen(false);
  };

  const scrollToSection = (sectionId: string) => {
    const section = document.getElementById(sectionId);
    if (section) {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const handleOpenMonitoringPanel = () => {
    setIsMonitoringOpen(true);
  };

  const handleCloseMonitoringPanel = () => {
    setIsMonitoringOpen(false);
  };

  const handleOpenAnalyticsPanel = () => {
    setIsAnalyticsOpen(true);
  };

  const handleViewProductivity = () => {
    if (selectedAsset) {
      scrollToSection("productivity-insights-section");
      return;
    }
    setIsAnalyticsOpen(true);
  };

  const handleCloseAnalyticsPanel = () => {
    setIsAnalyticsOpen(false);
  };

  const handleOpenCriticalAlertsPanel = () => {
    setSelectedCriticalAlert(null);
    setIsCriticalAlertsOpen(true);
  };

  const handleCloseCriticalAlertsPanel = () => {
    setIsCriticalAlertsOpen(false);
    setSelectedCriticalAlert(null);
  };

  const monitoringTarget = useMemo<Asset | null>(() => {
    return assets.length > 0 ? assets[0] : null;
  }, [assets]);

  const monitoringMetrics = useMemo(() => {
    const totalAlerts = liveLogs.length;
    const criticalCount = liveLogs.filter((log: SecurityFeedItem) => log.type === "critical").length;
    const warningCount = liveLogs.filter((log: SecurityFeedItem) => log.type === "warning").length;
    const ramChanges = liveLogs.filter((log: SecurityFeedItem) => /ram[_ ]change/i.test(log.message)).slice(-5);
    const motherboardChanges = liveLogs.filter((log: SecurityFeedItem) => /motherboard[_ ]change/i.test(log.message)).slice(-5);
    const lastScanTime = liveLogs.length > 0 ? liveLogs[liveLogs.length - 1].timestamp : monitoringTarget?.lastLogin || "N/A";

    return {
      totalAlerts,
      criticalCount,
      warningCount,
      ramChanges,
      motherboardChanges,
      lastScanTime,
    };
  }, [liveLogs, monitoringTarget]);

  const [isAssetHistoryOpen, setIsAssetHistoryOpen] = useState(false);

  const handleOpenAssetHistory = () => setIsAssetHistoryOpen(true);
  const handleCloseAssetHistory = () => setIsAssetHistoryOpen(false);

  const analyticsTarget = useMemo<Asset | null>(() => {
    return assets.find((asset: Asset) => asset.alertStatus === "critical") || assets[0] || null;
  }, [assets]);

  const analyticsMetrics = useMemo(() => {
    const totalAlerts = liveLogs.length;
    const criticalCount = liveLogs.filter((log: SecurityFeedItem) => log.type === "critical").length;
    const warningCount = liveLogs.filter((log: SecurityFeedItem) => log.type === "warning").length;
    const infoCount = liveLogs.filter((log: SecurityFeedItem) => log.type === "info").length;
    const recentRamChanges = liveLogs.filter((log: SecurityFeedItem) => /ram[_ ]change/i.test(log.message)).slice(-5);
    const recentMotherboardChanges = liveLogs.filter((log: SecurityFeedItem) => /motherboard[_ ]change/i.test(log.message)).slice(-5);
    const lastScanTime = liveLogs.length > 0 ? liveLogs[liveLogs.length - 1].timestamp : analyticsTarget?.lastLogin || "N/A";
    const uniqueDevicesMonitored = new Set(liveLogs.map((log: SecurityFeedItem) => log.node)).size;

    const alertCountsByNode = liveLogs.reduce<Record<string, number>>((acc, log) => {
      acc[log.node] = (acc[log.node] || 0) + 1;
      return acc;
    }, {});
    const mostAlertedNode = Object.entries(alertCountsByNode).sort((a, b) => b[1] - a[1])[0]?.[0] || analyticsTarget?.hostname || "None";
    const mostRecentDevice = liveLogs.length > 0 ? liveLogs[liveLogs.length - 1].node : analyticsTarget?.hostname || "None";
    const highestRiskDevice = assets.find((asset: Asset) => asset.status === "Overload" || asset.alertStatus === "critical")?.hostname || analyticsTarget?.hostname || "None";
    const deviceIntegrityScore = Math.max(46, 100 - criticalCount * 12 - warningCount * 6);
    const securityPostureSummary = criticalCount > 0
      ? "Elevated risk posture requires immediate SOC intervention."
      : warningCount > 0
      ? "Cautionary posture; continue monitoring and validate controls."
      : "Strong posture; environment operating within expected security thresholds.";
    const alertTimeline = [...liveLogs].slice(-8).reverse();

    return {
      totalAlerts,
      criticalCount,
      warningCount,
      infoCount,
      recentRamChanges,
      recentMotherboardChanges,
      lastScanTime,
      uniqueDevicesMonitored,
      mostAlertedNode,
      mostRecentDevice,
      highestRiskDevice,
      deviceIntegrityScore,
      securityPostureSummary,
      alertTimeline,
    };
  }, [liveLogs, analyticsTarget, assets]);

  const handleNavigateAnalytics = () => {
    scrollToSection("demo-sentinel-core");
  };

  const handleNavigateReports = () => {
    scrollToSection("fleet-telemetry-panel");
  };

  const handleNavigateCriticalState = () => {
    handleOpenCriticalAlertsPanel();
  };
  // Initialize grid cells of green/amber states on mount
  useEffect(() => {
    const initialCells = Array.from({ length: 64 }, (_, i) => 
      i === 42 ? "alert" : Math.random() > 0.85 ? "warning" : "nominal"
    );
    setChartGridCells(initialCells);
  }, []);

  // Continuous simulations loops for demo content
  useEffect(() => {
    if (!isDemoMode) return;
    const ramTimer = setInterval(() => {
      setRamValue((prev: number) => Math.min(98, Math.max(45, prev + Math.floor(Math.random() * 7) - 3)));
    }, 2200);

    const biosTimer = setInterval(() => {
      const chars = "0123456789ABCDEF";
      setBiosHash((prev: string) => prev.slice(0, 8) + chars[Math.floor(Math.random() * 16)]);
    }, 2400);

    const gridTimer = setInterval(() => {
      setChartGridCells((prev: string[]) => 
        prev.map((state: string, idx: number) => {
          if (idx === 42) return "alert";
          if (Math.random() > 0.94) {
            return Math.random() > 0.65 ? "warning" : "nominal";
          }
          return state;
        })
      );
    }, 4200);

    let tick = 0;
    const waveTimer = setInterval(() => {
      tick += 0.15;
      const points = [];
      for (let i = 0; i <= 24; i++) {
        const x = (i / 24) * 350;
        const y = 90 + Math.sin(i * 0.45 + tick) * 22 + Math.cos(i * 0.2 + tick * 1.5) * 10;
        points.push(`${x},${y}`);
      }
      setChartWavePath(`M ${points.join(" L ")}`);
    }, 240);

    return () => {
      clearInterval(ramTimer);
      clearInterval(biosTimer);
      clearInterval(gridTimer);
      clearInterval(waveTimer);
    };
  }, [isDemoMode]);

  // Demo-only telemetry animation. Production values come from PostgreSQL/psutil.
  useEffect(() => {
    if (!isDemoMode) return;
    const interval = setInterval(() => {
      setTelemetryCPU((prev: number) => Math.min(100, Math.max(5, prev + Math.floor(Math.random() * 15) - 7)));
      setTelemetryRAM((prev: number) => Math.min(100, Math.max(10, prev + Math.floor(Math.random() * 7) - 3)));
      setTelemetryNET((prev: number) => Math.max(10, prev + Math.floor(Math.random() * 40) - 20));
    }, 1500);
    return () => clearInterval(interval);
  }, [isDemoMode]);

  // Adapter mapping functions for robust integration with external Python backend schemas
  const mapBackendAsset = (item: any): Asset => {
    const statusRaw = String(item.status || item.device_status || 'Offline').toLowerCase();
    let status: 'Online' | 'Idle' | 'Overload' | 'Offline' = 'Offline';
    if (statusRaw.includes('idle')) status = 'Idle';
    else if (statusRaw.includes('overload') || statusRaw.includes('critical')) status = 'Overload';
    else if (statusRaw.includes('offline')) status = 'Offline';
    else status = 'Online';

    const alertRaw = String(item.alertStatus || item.alert_status || item.severity || 'nominal').toLowerCase();
    let alertStatus: 'nominal' | 'warning' | 'critical' = 'nominal';
    if (alertRaw.includes('critical') || alertRaw.includes('error') || alertRaw.includes('danger') || alertRaw.includes('high')) alertStatus = 'critical';
    else if (alertRaw.includes('warning') || alertRaw.includes('warn') || alertRaw.includes('medium')) alertStatus = 'warning';

    const ipAddressValue = item.ip_address || item.ipAddress || item.ip || "No IP";
    const ramValue = item.ram_total_gb !== undefined && item.ram_total_gb !== null ? `${item.ram_total_gb}GB` : "No RAM data";
    const biosSerialValue = item.bios_serial || item.biosSerial || item.serial || item.bios || "No BIOS serial";
    const baseboardSerial = item.baseboard_serial || item.baseboardSerial || "No baseboard serial";
    const activePathValue = item.current_active_path || item.current_path || item.currentWebsite || item.current_website || item.website || "No active application";
    const alertList = Array.isArray(item.alerts) ? item.alerts : [];

    const detailHistory = Array.isArray(item.history) ? item.history.slice() : [];
    if (baseboardSerial !== "No baseboard serial") {
      detailHistory.push(`Baseboard Serial: ${baseboardSerial}`);
    }
    if (item.baseboard_manufacturer) {
      detailHistory.push(`Baseboard Manufacturer: ${item.baseboard_manufacturer}`);
    }
    if (item.mac_address) {
      detailHistory.push(`MAC Address: ${item.mac_address}`);
    }

    return {
      hostname: item.hostname || item.host || item.name || "Unknown Host",
      status: status,
      employee: item.current_user || item.username || item.employee || item.owner || item.user || "No user",
      department: item.department || item.dept || "No department",
      deviceId: item.device_uid || item.device_id || item.deviceId || item.uuid || item.bios_serial || item.baseboard_serial || item.composite_id || "No device id",
      assetId: item.asset_id || item.assetId || item.uuid || item.bios_serial || item.biosSerial || "No asset id",
      ipAddress: ipAddressValue,
      os: item.windows_version || item.os || item.operating_system || item.platform || "No OS data",
      ram: ramValue,
      ramUsage: item.ram_usage_label || item.ram_usage || item.ramUsage || "No RAM usage",
      diskUsage: item.disk_usage || item.diskUsage || "No disk data",
      networkUsage: item.network_usage || item.networkUsage || "No network data",
      uptime: item.uptime || item.system_uptime || "No uptime data",
      biosSerial: biosSerialValue,
      biosVersion: item.bios_version || item.biosVersion || item.bios_version_string || "No BIOS version",
      motherboardSerial: baseboardSerial,
      uuid: item.uuid || item.system_uuid || "No UUID",
      macAddress: item.mac_address || item.macAddress || "No MAC",
      lastLogin: item.current_login_time || item.lastLogin || item.last_login || item.login_timestamp || "No login data",
      lastLogout: item.lastLogout || item.last_logout || item.logout_timestamp || (status === "Online" ? "Currently Active" : "No logout data"),
      loginDuration: item.login_duration || item.session_duration || item.loginDuration || "No duration",
      loginsToday: Number(item.logins_today || item.loginsToday || 0),
      currentUser: item.current_user || item.currentUser || item.username || item.employee || "No user",
      currentWebsite: activePathValue,
      activeApplication: item.active_application || item.activeApplication || item.current_application || "No active application",
      activeWindow: item.active_window || item.activeWindow || item.current_window || "No active window",
      lastActiveTime: item.last_active_time || item.lastActiveTime || item.active_timestamp || "No activity",
      lastExecutedProcess: item.last_executed_process || item.lastExecutedProcess || "No process data",
      threatScore: Number(item.threat_score || item.threatScore || (alertStatus === "critical" ? 92 : alertStatus === "warning" ? 54 : 12)),
      alerts: alertList,
      hardwareChanges: Array.isArray(item.hardware_changes) ? item.hardware_changes : [],
      unauthorizedSoftware: Array.isArray(item.unauthorized_software) ? item.unauthorized_software : [],
      usbActivity: Array.isArray(item.usb_activity) ? item.usb_activity : [],
      failedLoginAttempts: Number(item.failed_login_attempts || item.failedLoginAttempts || 0),
      alertStatus: alertStatus,
      location: item.location || item.loc || ipAddressValue || "No location",
      lastReflash: item.lastReflash || item.last_reflash || item.reflash || "No reflash data",
      cpuModel: item.cpu_name || item.cpuModel || item.cpu_model || item.cpu || "No CPU data",
      cpuUsage: item.cpu_usage_label || item.cpu_usage || item.cpuUsage || "No CPU data",
      lastSeen: item.last_seen || item.lastSeen,
      lastSeenHuman: item.last_seen_human || item.lastSeenHuman || item.last_seen || "No heartbeat",
      memoryUsedGb: item.memory_used_gb,
      memoryAvailableGb: item.memory_available_gb,
      loginsThisWeek: Number(item.logins_this_week || item.loginsThisWeek || 0),
      lastSuccessfulLogin: item.last_successful_login || item.lastSuccessfulLogin,
      lastFailedLogin: item.last_failed_login || item.lastFailedLogin,
      applicationHistory: Array.isArray(item.application_history) ? item.application_history : [],
      complianceStatus: item.complianceStatus !== undefined ? !!item.complianceStatus : (item.compliance_status !== undefined ? !!item.compliance_status : (alertStatus === 'nominal')),
      history: detailHistory.length > 0 ? detailHistory : alertList,
      timeline: Array.isArray(item.timeline) ? item.timeline : []
    };
  };

  const mapBackendAlert = (item: any): SecurityFeedItem => {
    const severityRaw = String(item.severity || item.alert_type || '').toUpperCase();
    let type: 'info' | 'warning' | 'critical' = 'info';
    if (severityRaw === 'CRITICAL') type = 'critical';
    else if (severityRaw === 'HIGH') type = 'warning';

    return {
      timestamp: item.timestamp || item.time || new Date().toLocaleTimeString(),
      node: item.hostname || item.host || item.node || "SYSTEM",
      message: item.alert_type || item.details || item.message || item.msg || item.text || "Anomaly signature detected.",
      type: type
    };
  };

  const formatAlertValue = (value: any) => {
    if (value === undefined || value === null || value === "") return "N/A";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };

  const resolvePreviousValue = (details: Record<string, any>) => {
    const previousKeys = Object.keys(details).filter((key) =>
      /^prev/i.test(key) || /^previous/i.test(key)
    );
    if (previousKeys.length === 0) return "N/A";
    return previousKeys
      .map((key) => `${key.replace(/_/g, " ")}: ${formatAlertValue(details[key])}`)
      .join(" | ");
  };

  const resolveCurrentValue = (details: Record<string, any>) => {
    const currentKeys = Object.keys(details).filter((key) =>
      /^curr/i.test(key) || /^current/i.test(key)
    );
    if (currentKeys.length === 0) return "N/A";
    return currentKeys
      .map((key) => `${key.replace(/_/g, " ")}: ${formatAlertValue(details[key])}`)
      .join(" | ");
  };

  const mapBackendAlertRecord = (item: any, index: number): BackendAlertRecord => {
    const details = item && typeof item.details === "object" && item.details !== null ? item.details : {};
    const hostname = item.hostname || item.host || item.node || "SYSTEM";
    const timestamp = item.timestamp || item.time || new Date().toLocaleTimeString();
    const alertType = item.alert_type || item.alertType || item.type || "SECURITY_ALERT";
    const severity = String(item.severity || "INFO").toUpperCase();
    const id = `${hostname}-${alertType}-${timestamp}-${index}`;

    return {
      id,
      alertType,
      deviceName: hostname,
      employee: details.username || item.username || "System Account",
      severity,
      time: timestamp,
      description: formatAlertValue(item.message || item.details_text || item.description || `${alertType} detected on ${hostname}`),
      previousValue: resolvePreviousValue(details),
      currentValue: resolveCurrentValue(details),
      alertStatus: "Active",
      raw: item,
    };
  };

  const criticalAlertRecords = useMemo(() => {
    return alertRecords.filter((alertRecord) => alertRecord.severity === "CRITICAL");
  }, [alertRecords]);

  const handleViewCriticalAlertDevice = (alertRecord: BackendAlertRecord) => {
    const details = alertRecord.raw?.details && typeof alertRecord.raw.details === "object" ? alertRecord.raw.details : {};
    const matchedAsset = assets.find((asset: Asset) =>
      asset.hostname === alertRecord.deviceName ||
      asset.ipAddress === details.ip_address ||
      asset.employee === alertRecord.employee
    );

    if (matchedAsset) {
      handleCloseCriticalAlertsPanel();
      handleSelectAsset(matchedAsset);
    }
  };

  const handleAcknowledgeCriticalAlert = (alertRecord: BackendAlertRecord) => {
    setAcknowledgedAlerts((prev) => ({
      ...prev,
      [alertRecord.id]: true,
    }));
    setSelectedCriticalAlert((prev) => prev && prev.id === alertRecord.id ? { ...prev, alertStatus: "Acknowledged" } : prev);
  };

  const resolveAlertEmployee = (alertRecord: BackendAlertRecord) => {
    const details = alertRecord.raw?.details && typeof alertRecord.raw.details === "object" ? alertRecord.raw.details : {};
    const matchedAsset = assets.find((asset: Asset) =>
      asset.hostname === alertRecord.deviceName ||
      asset.ipAddress === details.ip_address
    );
    return matchedAsset?.employee || alertRecord.employee;
  };

  const resolveAlertStatus = (alertRecord: BackendAlertRecord) => {
    return acknowledgedAlerts[alertRecord.id] ? "Acknowledged" : alertRecord.alertStatus;
  };

  // Connected real-time polling effect to coordinate with the Python monitoring service
  useEffect(() => {
    if (isDemoMode) return;

    let active = true;

    const fetchFleetData = async () => {
      try {
        const response = await apiFetch("/api/assets");
        if (!response.ok) throw new Error("Assets endpoint error");
        const data = await response.json();

        if (active && Array.isArray(data)) {
          const mapped = data.map(mapBackendAsset).map(asset => {
            if (isDemoMode && localOverrides[asset.hostname]) {
              return { ...asset, ...localOverrides[asset.hostname] };
            }
            return asset;
          });
          setAssets(mapped);
          setSelectedAsset((current) => {
            const persisted = readDashboardState();
            const targetDeviceId = current?.deviceId || persisted.selectedDeviceId;
            const targetHostname = current?.hostname || persisted.selectedHostname;
            if (!targetDeviceId && !targetHostname) return current;
            const refreshed = mapped.find((asset) =>
              (targetDeviceId && asset.deviceId === targetDeviceId) ||
              (!targetDeviceId && targetHostname && asset.hostname === targetHostname)
            );
            return refreshed ? { ...(current || refreshed), ...refreshed } : current;
          });
        }
      } catch (err) {
        console.warn("[SENTINEL COMPLIANCE] Assets background integration offline. Using secure in-memory cache.");
      }
    };

    const fetchAlertData = async () => {
      try {
        const response = await apiFetch("/api/alerts");
        if (!response.ok) throw new Error("Alerts endpoint error");
        const data = await response.json();
        if (active && Array.isArray(data)) {
          const mapped = data.map(mapBackendAlert);
          const records = data.map(mapBackendAlertRecord);
          setLiveLogs(mapped);
          setAlertRecords(records);
        }
      } catch (err) {
        console.warn("[SENTINEL COMPLIANCE] Alerts background integration offline. Using secure in-memory cache.");
      }
    };

    fetchFleetData();
    fetchAlertData();

    const assetsTimer = setInterval(fetchFleetData, 10000);
    const alertsTimer = setInterval(fetchAlertData, 5000);

    return () => {
      active = false;
      clearInterval(assetsTimer);
      clearInterval(alertsTimer);
    };
  }, [localOverrides, isDemoMode]);

  // Handle opening of individual asset detail card drawer
  const handleSelectAsset = (asset: Asset) => {
    if (!isDemoMode) {
      writeDashboardState({ selectedHostname: asset.hostname, selectedDeviceId: asset.deviceId || null });
      restoredDetailScrollRef.current = false;
    }
    setSelectedAsset(asset);
    setSelectedAssetDetail(null);
    setAuditReport(null);
    setAuditRiskScore(null);
    setAuditSeverity(null);
    setTelemetryCPU(Number(String(asset.cpuUsage || "0").replace("%", "")) || 0);
    setTelemetryRAM(Number(String(asset.ramUsage || "0").replace("%", "")) || 0);
  };

  useEffect(() => {
    if (isDemoMode || selectedAsset || assets.length === 0) return;
    const persisted = readDashboardState();
    if (!persisted.selectedDeviceId && !persisted.selectedHostname) return;
    const restoredAsset = assets.find((asset) =>
      (persisted.selectedDeviceId && asset.deviceId === persisted.selectedDeviceId) ||
      (!persisted.selectedDeviceId && persisted.selectedHostname && asset.hostname === persisted.selectedHostname)
    );
    if (restoredAsset) {
      handleSelectAsset(restoredAsset);
    }
  }, [assets, selectedAsset, isDemoMode]);

  useEffect(() => {
    if (!selectedAsset || isDemoMode) return;

    let active = true;
    let loadedOnce = false;
    const fetchAssetDetail = async () => {
      if (isTimelineSelectorOpen || isTimelineHistoryOpen) return;
      if (!loadedOnce) setAssetDetailLoading(true);
      try {
        const response = await apiFetch(`/api/assets/${encodeURIComponent(selectedAsset.deviceId || selectedAsset.hostname)}/details`);
        if (!response.ok) throw new Error("Asset detail endpoint error");
        const payload = await response.json();
        const mappedAsset = mapBackendAsset(payload.asset || {});
        const normalized: AssetDetailPayload = {
          ...payload,
          asset: mappedAsset,
          timeline: Array.isArray(payload.timeline) ? payload.timeline : [],
          application_timeline: sortNewestTelemetry(Array.isArray(payload.application_timeline) ? payload.application_timeline : []),
          alerts: Array.isArray(payload.alerts) ? payload.alerts : [],
          sessions: Array.isArray(payload.sessions) ? payload.sessions : [],
          hardware_changes: Array.isArray(payload.hardware_changes) ? payload.hardware_changes : [],
          charts: {
            cpu_usage_history: payload.charts?.cpu_usage_history || [],
            ram_usage_history: payload.charts?.ram_usage_history || [],
            login_frequency: payload.charts?.login_frequency || [],
            application_usage: payload.charts?.application_usage || [],
            application_usage_summary: payload.charts?.application_usage_summary || {},
            application_usage_periods: payload.charts?.application_usage_periods || {},
            alert_trend: payload.charts?.alert_trend || [],
          }
        };
        if (active) {
          const latestApplicationEntry = newestApplicationEntry(normalized.application_timeline as Array<Record<string, any>>);
          setSelectedAssetDetail(normalized);
          setSelectedAsset((current) => {
            if (assetIdentity(current) !== assetIdentity(selectedAsset)) return current;
            const activeApplicationPatch = latestApplicationEntry ? {
              activeApplication: latestApplicationEntry.application || latestApplicationEntry.application_name || mappedAsset.activeApplication,
              activeWindow: latestApplicationEntry.window_title || mappedAsset.activeWindow,
              currentWebsite: latestApplicationEntry.process_path || mappedAsset.currentWebsite,
              lastActiveTime: latestApplicationEntry.timestamp || mappedAsset.lastActiveTime,
              applicationHistory: normalized.application_timeline,
            } : {};
            return { ...current, ...mappedAsset, ...activeApplicationPatch };
          });
          setTelemetryCPU(Number(String(mappedAsset.cpuUsage || "0").replace("%", "")) || 0);
          setTelemetryRAM(Number(String(mappedAsset.ramUsage || "0").replace("%", "")) || 0);
          loadedOnce = true;
        }
      } catch (err) {
        console.warn("[SENTINEL COMPLIANCE] Asset detail integration offline.", err);
      } finally {
        if (active) setAssetDetailLoading(false);
      }
    };

    fetchAssetDetail();
    const timer = setInterval(fetchAssetDetail, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [selectedAsset?.deviceId, selectedAsset?.hostname, isDemoMode, isTimelineSelectorOpen, isTimelineHistoryOpen]);

  useEffect(() => {
    if (!selectedAsset || isDemoMode) return;

    let active = true;
    const fetchLiveApplicationTimeline = async () => {
      if (isTimelineSelectorOpen || isTimelineHistoryOpen) return;
      try {
        const identifier = selectedAsset.deviceId || selectedAsset.hostname;
        const response = await apiFetch(`/api/active-application-history/${encodeURIComponent(identifier)}?limit=100`);
        if (!response.ok) throw new Error("Active application history endpoint error");
        const payload = await response.json();
        const timeline = sortNewestTelemetry(
          Array.isArray(payload.application_timeline) ? payload.application_timeline : []
        );
        if (!active || timeline.length === 0) return;

        const latestApplicationEntry = newestApplicationEntry(timeline as Array<Record<string, any>>);
        setSelectedAssetDetail((current) => current ? {
          ...current,
          application_timeline: timeline,
        } : current);
        setSelectedAsset((current) => {
          if (assetIdentity(current) !== assetIdentity(selectedAsset)) return current;
          const activeApplicationPatch = latestApplicationEntry ? {
            activeApplication: latestApplicationEntry.application || latestApplicationEntry.application_name || current?.activeApplication,
            activeWindow: latestApplicationEntry.window_title || current?.activeWindow,
            currentWebsite: latestApplicationEntry.process_path || current?.currentWebsite,
            lastActiveTime: latestApplicationEntry.timestamp || current?.lastActiveTime,
            applicationHistory: timeline,
          } : {};
          return current ? { ...current, ...activeApplicationPatch } : current;
        });
      } catch (err) {
        console.warn("[SENTINEL COMPLIANCE] Live application timeline integration offline.", err);
      }
    };

    fetchLiveApplicationTimeline();
    const timer = setInterval(fetchLiveApplicationTimeline, LIVE_APPLICATION_TIMELINE_POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [selectedAsset?.deviceId, selectedAsset?.hostname, isDemoMode, isTimelineSelectorOpen, isTimelineHistoryOpen]);

  // Search filter computes
  const filteredAssets = useMemo(() => {
    const query = searchQuery.toLowerCase().trim();
    const statusRank: Record<string, number> = { Online: 0, Idle: 1, Overload: 2, Offline: 3 };
    const matches = !query
      ? assets
      : assets.filter((asset: Asset) => 
          asset.hostname.toLowerCase().includes(query) ||
          asset.employee.toLowerCase().includes(query) ||
          asset.ipAddress.toLowerCase().includes(query) ||
          asset.os.toLowerCase().includes(query) ||
          asset.ram.toLowerCase().includes(query)
        );
    return [...matches].sort((a, b) => {
      const rankDelta = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
      if (rankDelta !== 0) return rankDelta;
      return telemetryTimeMs(b.lastSeen || b.lastActiveTime) - telemetryTimeMs(a.lastSeen || a.lastActiveTime);
    });
  }, [assets, searchQuery]);

  // Pagination bounds (5 per page)
  const itemsPerPage = 5;
  const totalPages = Math.ceil(filteredAssets.length / itemsPerPage) || 1;
  const currentAssets = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredAssets.slice(start, start + itemsPerPage);
  }, [filteredAssets, currentPage]);

  // Adjust pagination page if query shifts bounds
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [searchQuery, totalPages, currentPage]);

  // Compute stats dynamically from live backend state
  const kpiStats = useMemo<KPIStats>(() => {
    const online = assets.filter((a: Asset) => a.status === "Online").length;
    const idle = assets.filter((a: Asset) => a.status === "Idle").length;
    const overload = assets.filter((a: Asset) => a.status === "Overload").length;
    const offline = assets.filter((a: Asset) => a.status === "Offline").length;

    const uniqueUsers = new Set(
      assets.map((asset: Asset) => (asset.employee || "System Account").trim() || "System Account")
    ).size;

    const criticalAlertCount = liveLogs.filter((log: SecurityFeedItem) => log.type === "critical").length;

    return {
      totalAssets: assets.length,
      onlineDevices: online,
      offlineDevices: offline,
      activeUsers: uniqueUsers,
      criticalAlerts: criticalAlertCount,
      securityIncidents: overload + (idle > 1 ? 1 : 0),
    };
  }, [assets, liveLogs]);

  // AI Compliance Audit request using full-stack Gemini API endpoint
  const handleAICorporateAudit = async (asset: Asset) => {
    setAuditLoading(true);
    setAuditReport(null);
    setAuditRiskScore(null);
    setAuditSeverity(null);

    const padZero = (n: number) => n.toString().padStart(2, '0');
    const now = new Date();
    const timeStr = `${padZero(now.getHours())}:${padZero(now.getMinutes())}:${padZero(now.getSeconds())}`;

    // Append trigger statement in logs console
    setLocalLogs((prev: SecurityFeedItem[]) => [
      { timestamp: timeStr, node: "AI-FORENSIC-CORE", message: `Initiating deep digital compliance scan on endpoint ${asset.hostname}...`, type: "info" },
      ...prev
    ]);

    try {
      const response = await apiFetch("/api/audit-asset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(asset)
      });
      
      if (!response.ok) {
        throw new Error("Terminal link refused or timed out during compliance query.");
      }

      const reportData = await response.json();
      
      // Update states with beautiful AI forensic results
      setAuditReport(reportData.analysis);
      setAuditRiskScore(reportData.riskScore);
      setAuditSeverity(reportData.severity);

      // Append result log
      setLocalLogs((prev: SecurityFeedItem[]) => [
        { 
          timestamp: timeStr, 
          node: "AI-FORENSIC-CORE", 
          message: `Audit completed on ${asset.hostname}. Severity: ${reportData.severity.toUpperCase()}. Risk Factor: ${reportData.riskScore}/100.`, 
          type: reportData.severity === "critical" ? "critical" : reportData.severity === "warning" ? "warning" : "info" 
        },
        ...prev
      ]);
    } catch (err: any) {
      console.error(err);
      setAuditReport(`### CONNECTION ERROR\n\nFailed to establish diagnostic telemetry handshake with Sentinel AI Forensics Server. Ensure your Gemini API service key is bound in settings correctly.\n\n*Error details: ${err.message || "Endpoint error - Host refused connect"}`);
    } finally {
      setAuditLoading(false);
    }
  };

  // Tactical Operations Handler: Trigger Simulated Alert Swap
  const handleTriggerTelemetryAlert = (asset: Asset) => {
    const overrideVal = {
      status: "Overload" as const,
      alertStatus: "critical" as const,
      complianceStatus: false,
      history: [
        `CRITICAL Telemetry Event: Unauthorized hardware modification signature detected [${new Date().toLocaleTimeString()}].`,
        "Active memory controller module reporting capacity mismatch mismatch.",
        ...asset.history
      ]
    };

    setLocalOverrides((prev: Record<string, Partial<Asset>>) => ({
      ...prev,
      [asset.hostname]: overrideVal
    }));

    // Instantly apply locally
    setAssets((prev: Asset[]) => prev.map((a: Asset) => a.hostname === asset.hostname ? { ...a, ...overrideVal } : a));
    
    // Update active drawer context in real-time
    setSelectedAsset((prev: Asset | null) => prev && prev.hostname === asset.hostname ? { ...prev, ...overrideVal } : prev);
    setTelemetryCPU(94);
    setTelemetryRAM(89);

    const padZero = (n: number) => n.toString().padStart(2, '0');
    const now = new Date();
    const timeStr = `${padZero(now.getHours())}:${padZero(now.getMinutes())}:${padZero(now.getSeconds())}`;

    // Inject alert to marquee logs
    setLocalLogs((prev: SecurityFeedItem[]) => [
      { timestamp: timeStr, node: asset.hostname, message: "CRITICAL COMPONENT TAMPER: RAM capacity altered dynamically without certificate authorization!", type: "critical" },
      ...prev
    ]);
  };

  // Tactical Operations Handler: Quarantine Endpoint
  const handleTacticalQuarantine = (asset: Asset) => {
    const overrideVal = {
      status: "Offline" as const,
      alertStatus: "warning" as const,
      complianceStatus: false,
      ipAddress: "QUARANTINED",
      currentWebsite: "-",
      history: [
        `ADMIN QUARANTINE PROTOCOL: Local server severed dynamic IP access pathways [${new Date().toLocaleTimeString()}].`,
        "Endpoint designated as hazardous. Subnet whitelisting revoked.",
        ...asset.history
      ]
    };

    setLocalOverrides((prev: Record<string, Partial<Asset>>) => ({
      ...prev,
      [asset.hostname]: overrideVal
    }));

    // Instantly apply locally
    setAssets((prev: Asset[]) => prev.map((a: Asset) => a.hostname === asset.hostname ? { ...a, ...overrideVal } : a));

    // Update active drawer context in real-time
    setSelectedAsset((prev: Asset | null) => prev && prev.hostname === asset.hostname ? { ...prev, ...overrideVal } : prev);
    setTelemetryCPU(0);
    setTelemetryRAM(5);

    const padZero = (n: number) => n.toString().padStart(2, '0');
    const now = new Date();
    const timeStr = `${padZero(now.getHours())}:${padZero(now.getMinutes())}:${padZero(now.getSeconds())}`;

    // Inject quarantine log
    setLocalLogs((prev: SecurityFeedItem[]) => [
      { timestamp: timeStr, node: "COMMAND-GATE", message: `TACTICAL OPERATION SUCCESSFUL: Severed communication channels to node ${asset.hostname}.`, type: "warning" },
      ...prev
    ]);
  };

  // Tactical Operations Handler: Re-flash BIOS Reset
  const handleReflashBIOSReset = (asset: Asset) => {
    const overrideVal = {
      status: "Online" as const,
      alertStatus: "nominal" as const,
      complianceStatus: true,
      ipAddress: asset.hostname === "MOB-MKT-004" ? "Unassigned" : `10.14.22.${Math.floor(Math.random() * 200) + 12}`,
      history: [
        `SENTINEL CERTIFICATION HANDSHAKE: BIOS re-flashed. Cryprographic root baseline verified. [${new Date().toLocaleTimeString()}].`,
        "Integrity restored. Active alarms wiped cleanly.",
        ...asset.history
      ]
    };

    setLocalOverrides((prev: Record<string, Partial<Asset>>) => ({
      ...prev,
      [asset.hostname]: overrideVal
    }));

    // Instantly apply locally
    setAssets((prev: Asset[]) => prev.map((a: Asset) => a.hostname === asset.hostname ? { ...a, ...overrideVal } : a));

    // Update active drawer context in real-time
    setSelectedAsset((prev: Asset | null) => prev && prev.hostname === asset.hostname ? { ...prev, ...overrideVal } : prev);
    setTelemetryCPU(24);
    setTelemetryRAM(42);
    setAuditReport(null);
    setAuditRiskScore(null);
    setAuditSeverity(null);

    const padZero = (n: number) => n.toString().padStart(2, '0');
    const now = new Date();
    const timeStr = `${padZero(now.getHours())}:${padZero(now.getMinutes())}:${padZero(now.getSeconds())}`;

    // Inject reflash log
    setLocalLogs((prev: SecurityFeedItem[]) => [
      { timestamp: timeStr, node: asset.hostname, message: "RE-FLASH BIOS VERIFICATION: Re-established secure state. Root keys match signature profile securely.", type: "info" },
      ...prev
    ]);
  };

  // Client-side CSV generator report function
  const handleExportCSVReport = async () => {
    const quote = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const rows: string[][] = [["Section", "Hostname", "Field", "Value", "Extra"]];
    const detailResults = await Promise.all(assets.map(async (asset) => {
      try {
        const response = await apiFetch(`/api/assets/${encodeURIComponent(asset.deviceId || asset.hostname)}/details`);
        if (!response.ok) throw new Error("detail unavailable");
        return { asset, detail: await response.json() };
      } catch {
        return { asset, detail: null };
      }
    }));

    detailResults.forEach(({ asset, detail }) => {
      const analytics = detail?.charts?.application_usage_periods?.today || {
        items: detail?.charts?.application_usage || [],
        summary: detail?.charts?.application_usage_summary || {},
      };
      const summary = analytics.summary || {};
      const sessions = Array.isArray(detail?.sessions) ? detail.sessions : [];
      const alerts = Array.isArray(detail?.alerts) ? detail.alerts : [];
      const hardwareChanges = Array.isArray(detail?.hardware_changes) ? detail.hardware_changes : [];

      [
        ["Device Information", "hostname", asset.hostname],
        ["Device Information", "employee id", asset.employee],
        ["Device Information", "IP", asset.ipAddress],
        ["Device Information", "OS", asset.os],
        ["Device Information", "RAM", asset.ram],
        ["Device Information", "CPU", asset.cpuModel],
        ["Device Information", "BIOS serial", asset.biosSerial],
        ["Device Information", "motherboard serial", asset.motherboardSerial],
        ["Device Information", "UUID", asset.uuid],
        ["Device Information", "MAC address", asset.macAddress],
      ].forEach(([section, field, value]) => rows.push([section, asset.hostname, field, value || "No data", ""]));

      const loginEvents = sessions.filter((session: any) => session.event_type === "LOGIN");
      rows.push(["Login Analytics", asset.hostname, "first login", loginEvents.at(-1)?.login_timestamp || asset.lastLogin || "No data", ""]);
      rows.push(["Login Analytics", asset.hostname, "last login", loginEvents[0]?.login_timestamp || asset.lastLogin || "No data", ""]);
      sessions.slice(0, 20).forEach((session: any) => {
        rows.push(["Login Analytics", asset.hostname, "login history", session.event_type || "SESSION", `${session.username || ""} ${session.login_timestamp || session.recorded_at || ""}`]);
      });

      (analytics.items || []).slice(0, 20).forEach((item: any) => {
        rows.push([
          "Application Analytics",
          asset.hostname,
          item.application_name || item.label || "Unknown",
          `foreground=${formatUsageDuration(item.total_duration_seconds || item.value || 0)}`,
          `productive=${formatUsageDuration(item.active_duration_seconds || item.productive_duration_seconds || 0)} idle=${formatUsageDuration(item.idle_duration_seconds || 0)} locked=${formatUsageDuration(item.locked_duration_seconds || 0)}`,
        ]);
      });

      rows.push(["Productivity", asset.hostname, "total online time", formatUsageDuration(summary.total_session_duration_seconds || 0), "Today"]);
      rows.push(["Productivity", asset.hostname, "active time", formatUsageDuration(summary.active_working_seconds || 0), "Today"]);
      rows.push(["Productivity", asset.hostname, "idle time", formatUsageDuration(summary.idle_seconds || 0), "Today"]);
      rows.push(["Productivity", asset.hostname, "locked time", formatUsageDuration(summary.locked_seconds || 0), "Today"]);
      rows.push(["Productivity", asset.hostname, "productivity percentage", `${Number(summary.productivity_percentage || 0).toFixed(2)}%`, "Today"]);

      hardwareChanges.slice(0, 20).forEach((change: any) => {
        rows.push(["Security", asset.hostname, "hardware change alert", change.change_type || "Hardware Change", change.detected_at || ""]);
      });
      alerts.filter((alert: any) => String(alert.severity || "").toUpperCase() === "CRITICAL").slice(0, 20).forEach((alert: any) => {
        rows.push(["Security", asset.hostname, "critical alert", alert.alert_type || "Alert", alert.timestamp || ""]);
      });
    });

    const csvBody = rows.map((row) => row.map(quote).join(",")).join("\n");
    const blob = new Blob([csvBody], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `Asset_Sentinel_Fleet_Report_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    const padZero = (n: number) => n.toString().padStart(2, '0');
    const now = new Date();
    const timeStr = `${padZero(now.getHours())}:${padZero(now.getMinutes())}:${padZero(now.getSeconds())}`;

    setLiveLogs((prev: SecurityFeedItem[]) => [
      { timestamp: timeStr, node: "COMMAND-GATE", message: "LOCAL CSV EXPORT TRIGGERED: Generated spreadsheet report covering all node assets.", type: "info" },
      ...prev
    ]);
  };

  const submitSupportTicket = async () => {
    setSupportBusy(true);
    setSupportError("");
    setSupportMessage("");
    try {
      const response = await apiFetch("/api/support/tickets", {
        method: "POST",
        body: JSON.stringify({
          ...ticketForm,
          relatedDevice: ticketForm.relatedDevice || selectedAsset?.hostname || "",
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setSupportError(payload.error || "Unable to create support ticket.");
        return;
      }
      setSupportMessage(`Ticket ${payload.ticket?.ticketNumber || ""} created successfully.`);
      setTicketForm({ title: "", category: "Agent Issue", priority: "MEDIUM", relatedDevice: "", description: "" });
    } catch {
      setSupportError("Support ticket service is unavailable.");
    } finally {
      setSupportBusy(false);
    }
  };

  const submitSupportEmail = async () => {
    setSupportBusy(true);
    setSupportError("");
    setSupportMessage("");
    try {
      const response = await apiFetch("/api/support/email", {
        method: "POST",
        body: JSON.stringify(emailSupportForm),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setSupportError(payload.error || "Unable to send support email.");
        return;
      }
      setSupportMessage(payload.message || "Support email sent.");
      setEmailSupportForm({ subject: "", priority: "MEDIUM", message: "" });
    } catch {
      setSupportError("Support email service is unavailable.");
    } finally {
      setSupportBusy(false);
    }
  };

  if (isDemoMode) {
    return (
      <div id="command-dashboard-screen" className="flex flex-col h-screen overflow-hidden antialiased bg-[#0A0C10] text-[#dae3ee] font-sans selection:bg-[#00d1ff]/20">
        
        {/* Top Demode Banner / Header */}
        <header className="h-16 bg-[#141c24] border-b border-[#3c494e]/30 flex items-center justify-between px-6 select-none shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#222b33] border border-[#3c494e] flex items-center justify-center glow-accent">
              <SentinelLogo className="w-5.5 h-5.5" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-black text-[#00d1ff] tracking-wider uppercase leading-none">
                Asset Sentinel Command Center
              </span>
              <span className="text-[9px] text-[#bbc9cf] font-mono tracking-widest mt-0.5 font-bold uppercase">
                Demo Mode – Read Only Preview
              </span>
            </div>
          </div>
          <button 
            onClick={() => onNavigate("landing")}
            className="flex items-center gap-1.5 text-xs text-[#00d1ff] border border-[#00d1ff]/30 rounded-lg px-4 py-2 hover:bg-[#00d1ff]/10 transition-all font-bold uppercase tracking-wider active:scale-95 cursor-pointer shadow-[0_0_12px_rgba(0,209,255,0.15)]"
          >
            <LogOut className="w-3.5 h-3.5" />
            Exit Demo
          </button>
        </header>

        {/* Restricted content wrapper - NOT scrollable horizontally, perfectly designed for maximum density */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 flex flex-col gap-6 pb-28">
          
          {/* Section 1: System Overview (KPI Scorecard Cards) */}
          <section id="demo-system-overview">
            <h2 className="text-xs font-black uppercase tracking-widest text-[#bbc9cf] mb-3 flex items-center gap-2 select-none">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00d1ff]"></span>
              System Overview
            </h2>
            
            <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
              {/* Card 1 */}
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 bg-[#161B22]/80 border border-white/5 select-none relative overflow-hidden group">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Total Assets</span>
                  <Server className="w-3.5 h-3.5 text-[#859399]" />
                </div>
                <div className="text-2xl font-black text-[#dae3ee] mt-1">
                  {kpiStats.totalAssets.toLocaleString()}
                </div>
                <div className="flex items-center gap-1 text-[#00d1ff] text-[10px] mt-2 font-mono">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>{kpiStats.totalAssets > 0 ? `${((kpiStats.onlineDevices / kpiStats.totalAssets) * 100).toFixed(1)}% Online` : "Loading..."}</span>
                </div>
              </div>

              {/* Card 2 */}
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 bg-[#161B22]/80 border border-white/5 select-none relative overflow-hidden group">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Online Devices</span>
                  <div className="w-2 h-2 rounded-full bg-[#00d1ff] glow-active"></div>
                </div>
                <div className="text-2xl font-black text-[#dae3ee] mt-1">
                  {kpiStats.onlineDevices.toLocaleString()}
                </div>
                <div className="w-full h-6 mt-2 relative">
                  <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 24">
                    <path fill="none" stroke="#00d1ff" strokeWidth="2" d="M 0 18 Q 15 12 30 15 T 60 8 T 80 14 T 100 3" />
                  </svg>
                </div>
              </div>

              {/* Card 3 */}
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 bg-[#161B22]/80 border border-white/5 select-none relative overflow-hidden group">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Offline Devices</span>
                  <div className="w-2 h-2 rounded-full bg-[#859399]"></div>
                </div>
                <div className="text-2xl font-black text-[#dae3ee] mt-1">
                  {kpiStats.offlineDevices.toLocaleString()}
                </div>
                <div className="text-[10px] text-[#bbc9cf] mt-auto pb-1 font-mono">
                  {kpiStats.totalAssets > 0 ? `${((kpiStats.offlineDevices / kpiStats.totalAssets) * 100).toFixed(1)}% of total fleet` : "Loading..."}
                </div>
              </div>

              {/* Card 4 */}
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 bg-[#161B22]/80 border border-white/5 select-none relative overflow-hidden group">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Active Users</span>
                  <Smartphone className="w-3.5 h-3.5 text-[#859399]" />
                </div>
                <div className="text-2xl font-black text-[#dae3ee] mt-1">
                  {kpiStats.activeUsers.toLocaleString()}
                </div>
                <div className="text-[10px] text-[#00d1ff] mt-auto pb-1 font-mono">
                  Verified Identity Posture
                </div>
              </div>

              {/* Card 5 */}
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 bg-red-950/10 border border-red-500/25 select-none relative overflow-hidden group">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-red-400">Critical Alerts</span>
                  <div className="w-2 h-2 rounded-full bg-red-400 glow-critical animate-ping"></div>
                </div>
                <div className="text-2xl font-black text-red-400 mt-1">
                  {kpiStats.criticalAlerts.toLocaleString()}
                </div>
                <div className="w-full h-6 mt-2 relative">
                  <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 24">
                    <path fill="none" stroke="#f87171" strokeWidth="2" d="M 0 18 L 15 18 L 22 2 L 31 22 L 40 18 Z M 40 18 L 100 18" />
                  </svg>
                </div>
              </div>

              {/* Card 6 */}
              <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 bg-[#161B22]/80 border border-white/5 select-none relative overflow-hidden group">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-amber-500">Sec Incidents</span>
                  <div className="w-2 h-2 rounded-full bg-amber-500 glow-warning"></div>
                </div>
                <div className="text-2xl font-black text-amber-500 mt-1">
                  {kpiStats.securityIncidents.toLocaleString()}
                </div>
                <div className="flex items-center gap-1 text-amber-500 text-[10px] mt-auto pb-1 font-mono">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                  <span>Requires review</span>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Command Fleet Preview (RAM Integrity Trend) & Subnet Node Grid in two-column */}
          <section id="demo-live-monitoring">
            <h2 className="text-xs font-black uppercase tracking-widest text-[#bbc9cf] mb-3 flex items-center gap-2 select-none">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00d1ff]"></span>
              Live Monitoring Center
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* RAM Integrity Trend Left Panel */}
              <div className="glass-panel p-6 rounded-xl border border-[#3c494e]/30 bg-[#161B22]/80 flex flex-col justify-between min-h-[300px]">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-[10px] font-mono tracking-widest font-bold text-[#00d1ff] uppercase">RAM Integrity Trend</span>
                  <span className="bg-[#00d1ff]/10 text-[#00d1ff] border border-[#00d1ff]/20 text-[9px] font-mono font-semibold px-2 py-0.5 rounded flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00d1ff] animate-ping"></span>
                    INTEGRITY MONITORING STREAM
                  </span>
                </div>

                <div className="h-32 w-full bg-[#070b10] border border-white/5 rounded-lg relative overflow-hidden flex items-end mb-4">
                  <div className="absolute inset-0 bg-grid opacity-20 pointer-events-none"></div>
                  <svg className="w-full h-full" viewBox="0 0 350 180" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="waveGradDemo" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00d1ff" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#00d1ff" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    <path d={`${chartWavePath} L 350,180 L 0,180 Z`} fill="url(#waveGradDemo)" />
                    <path d={chartWavePath} fill="none" stroke="#00d1ff" strokeWidth="2.5" className="drop-shadow-[0_0_6px_#00d1ff]" />
                  </svg>
                  <div className="absolute bottom-2 left-2 flex items-center gap-1.5 font-mono text-[8px] text-[#bbc9cf] bg-[#141a22]/80 px-2 py-0.5 rounded border border-white/5 uppercase">
                    <span>RAM Verification Activity: ACTIVE</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono mb-4">
                  <div className="p-2.5 bg-[#070b10] border border-white/5 rounded-lg flex flex-col justify-between">
                    <span className="text-[9px] text-[#bbc9cf]/70 uppercase">RAM Change Detection Events</span>
                    <span className="text-[#00d1ff] font-bold text-sm tracking-wide">0 (NOMINAL)</span>
                  </div>
                  <div className="p-2.5 bg-[#070b10] border border-white/5 rounded-lg flex flex-col justify-between">
                    <span className="text-[9px] text-[#bbc9cf]/70 uppercase">Hardware Validation Activity</span>
                    <span className="text-emerald-400 font-bold text-sm tracking-wide">99.98% SECURE</span>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5 font-mono text-[9px]">
                  <div className="flex items-center justify-between p-2 bg-[#070b10] border border-white/5 rounded">
                    <span className="text-[#bbc9cf]/80">INTEGRITY TREND ANALYSIS</span>
                    <span className="text-emerald-400 font-semibold uppercase">100% SECURE MEMORY BASELINE</span>
                  </div>
                </div>
              </div>

              {/* Subnet Node Grid Right Panel */}
              <div className="glass-panel p-6 rounded-xl border border-[#3c494e]/30 bg-[#161B22]/80 flex flex-col justify-between min-h-[300px]">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-[10px] font-mono tracking-widest font-bold text-[#bbc9cf] uppercase">Subnet Node Grid Array</span>
                  <span className="text-[9px] font-mono text-[#00d1ff] font-bold">64 ACTIVE ENDPOINTS</span>
                </div>

                <div className="grid grid-cols-8 gap-1.5 bg-[#070b10] p-3 border border-white/5 rounded-lg h-32 items-center justify-center mb-4">
                  {chartGridCells.map((state: string, idx: number) => {
                    let cellColor = "bg-[#2d363e]/40 border-white/5";
                    if (state === "nominal") cellColor = "bg-emerald-500/10 border-emerald-400/20 shadow-[0_0_2px_rgba(16,185,129,0.1)]";
                    if (state === "warning") cellColor = "bg-amber-500/30 border-amber-400/40 shadow-[0_0_3px_rgba(245,158,11,0.2)]";
                    if (state === "alert") cellColor = "bg-red-500 border-red-400 shadow-[0_0_8px_#ef4444] animate-ping";

                    return (
                      <div 
                        key={idx} 
                        className={`w-full aspect-square rounded-sm border ${cellColor} transition-all duration-300`} 
                      />
                    );
                  })}
                </div>

                <div className="flex justify-between items-center text-[9px] font-mono text-[#bbc9cf] bg-[#070b10] p-2 rounded border border-white/5 font-semibold">
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                    <span>Verified</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block"></span>
                    <span>Review Required</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block"></span>
                    <span>Alert Detected</span>
                  </div>
                </div>
              </div>

            </div>
          </section>

          {/* Section 3: Sentinel Core Hardware Cards */}
          <section id="demo-sentinel-core" className="mb-8">
            <h2 className="text-xs font-black uppercase tracking-widest text-[#bbc9cf] mb-3 flex items-center gap-2 select-none">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00d1ff]"></span>
              Sentinel Core
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Card 1: RAM Verified */}
              <div className="glass-panel p-4 rounded-lg bg-[#141c24]/75 border border-[#3c494e]/30 select-none animate-float-1">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[9px] text-[#00d1ff] tracking-wider font-semibold">NODE-4912</span>
                  <Cpu className="w-4 h-4 text-[#00d1ff] animate-spin" />
                </div>
                <h4 className="text-xs font-semibold text-[#dae3ee]">RAM Verified (32GB)</h4>
                <div className="w-full bg-[#2d363e]/50 h-2 mt-4 rounded-full overflow-hidden border border-white/5">
                  <div style={{ width: `${ramValue}%` }} className="bg-gradient-to-r from-cyan-500 to-[#00d1ff] h-full shadow-[0_0_8px_rgba(0,209,255,0.7)] transition-all duration-500"></div>
                </div>
                <div className="flex justify-between items-center text-[8px] font-mono mt-2 text-[#bbc9cf]/80">
                  <span>CAPACITY NOMINAL</span>
                  <span className="text-[#00d1ff] font-bold">{ramValue}% LOAD</span>
                </div>
              </div>

              {/* Card 2: BIOS Identity Intact */}
              <div className="glass-panel p-4 rounded-lg bg-[#141c24]/75 border border-[#3c494e]/30 select-none animate-float-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[9px] text-[#00d1ff] tracking-wider font-semibold">SERVER-DELTA</span>
                  <Sliders className="w-4 h-4 text-[#00d1ff] animate-pulse" />
                </div>
                <h4 className="text-xs font-semibold text-[#dae3ee]">BIOS Identity Intact</h4>
                <div className="flex flex-col gap-2 mt-4">
                  <div className="flex gap-1">
                    <div className="h-1.5 flex-1 bg-[#00d1ff] rounded-full shadow-[0_0_8px_#00d1ff] animate-pulse"></div>
                    <div className="h-1.5 flex-1 bg-[#00d1ff] rounded-full shadow-[0_0_8px_#00d1ff] animate-pulse" style={{ animationDelay: "0.2s" }}></div>
                  </div>
                </div>
                <div className="font-mono text-[8.5px] mt-2 text-[#bbc9cf]/80 flex justify-between items-center">
                  <span>UEFI KEYHASH:</span>
                  <span className="text-cyan-400 font-bold">{biosHash}</span>
                </div>
              </div>

              {/* Card 3: RAM Change Detected */}
              <div className="glass-panel p-4 rounded-lg bg-red-950/10 border border-red-500/30 animate-float-1 animate-warning-border select-none">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[9px] text-red-400 tracking-wider font-extrabold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span>
                    THREAT WARNING
                  </span>
                  <HardDrive className="w-4 h-4 text-red-400 animate-pulse" />
                </div>
                <h4 className="text-xs font-semibold text-[#dae3ee]">RAM Change Detected</h4>
                <div className="mt-3 p-1 rounded bg-red-900/20 border border-red-500/20 text-center font-mono text-[9px] text-red-300 animate-pulse">
                  HW CONFIG MISMATCH
                </div>
                <span className="font-mono text-[8.5px] text-red-400/90 mt-2 block font-semibold">EXPECT: 64GB | ACTIVE: 32GB</span>
              </div>

              {/* Card 4: Motherboard ID Certified */}
              <div className="glass-panel p-4 rounded-lg bg-[#141c24]/75 border border-[#3c494e]/30 select-none animate-float-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[9px] text-[#00d1ff] tracking-wider font-semibold">SRV-GAMMA-02</span>
                  <Layers className="w-4 h-4 text-[#00d1ff] animate-pulse" />
                </div>
                <h4 className="text-xs font-semibold text-[#dae3ee]">Motherboard Certified</h4>
                <div className="mt-4 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded bg-emerald-500/10 border border-emerald-400/20 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="font-mono text-[9px] text-emerald-400 uppercase font-extrabold">MB-994 MATCH</span>
                </div>
                <span className="font-mono text-[8px] text-[#bbc9cf] mt-2 block text-center uppercase font-light">TPM Security Chip verified</span>
              </div>

              {/* Card 6: Restricted Site Blocked */}
              <div className="glass-panel p-4 rounded-lg bg-red-950/10 border border-red-500/20 select-none animate-float-1">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[9px] text-red-400 tracking-wider font-bold">NET-MONITOR</span>
                  <Globe className="w-4 h-4 text-red-500 animate-pulse" />
                </div>
                <h4 className="text-xs font-semibold text-[#dae3ee]">Restricted Site Blocked</h4>
                <div className="mt-3.5 py-1 px-1.5 bg-red-950/30 rounded border border-red-500/10 text-center font-mono text-[8px] text-red-300">
                  EDGE FIREWALL BLOCKED
                </div>
                <span className="font-mono text-[8.5px] text-[#bbc9cf] mt-1.5 block text-center truncate">IP: 185.199.110.153</span>
              </div>
            </div>
          </section>

        </div>

        {/* Pinned Demo Mode Footer Panel */}
        <footer className="fixed bottom-0 inset-x-0 bg-[#161B21]/95 border-t border-amber-500/30 backdrop-blur-md px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4 z-50 shadow-2xl">
          <div className="text-center md:text-left select-none">
            <span className="text-[#00d1ff] font-extrabold text-sm uppercase font-mono tracking-wider">DEMO MODE</span>
            <p className="text-[#bbc9cf] text-xs font-light mt-0.5">
              View-only access. Sign in for complete monitoring, asset management, analytics, audit logs, and security controls.
            </p>
          </div>
          <button 
            onClick={() => onNavigate("login")}
            className="flex items-center gap-2 px-6 py-2.5 bg-[#00d1ff] text-[#003543] font-bold rounded-lg hover:bg-cyan-300 tracking-wider text-xs uppercase shadow-[0_0_15px_rgba(0,209,255,0.45)] transition-all active:scale-95 cursor-pointer max-w-max"
          >
            <LogIn className="w-4 h-4" />
            Admin Sign In
          </button>
        </footer>

      </div>
    );
  }

  return (
    <div id="command-dashboard-screen" className="flex h-dvh min-h-screen overflow-hidden antialiased bg-[#0A0C10] text-[#dae3ee] font-sans">
      
      {/* Side Navigation Bar (exactly styled as left panel of 3rd screenshot) */}
      {isMobileSidebarOpen && (
        <button
          aria-label="Close navigation menu"
          className="fixed inset-0 bg-[#060f16]/70 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      <nav id="sidebar-navigation" className={`bg-[#141c24] text-[#a4e6ff] h-screen w-72 max-w-[86vw] md:w-64 fixed left-0 top-0 border-r border-[#3c494e]/30 flex flex-col py-6 px-4 z-50 md:z-40 select-none transition-transform duration-300 ease-out ${isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        
        {/* Brand Header with navigation back to Landing Page */}
        <div 
          onClick={() => handleSidebarAction(() => onNavigate("landing"))}
          className="flex items-center gap-3 mb-8 px-2 cursor-pointer hover:opacity-80 active:scale-95 transition-all"
          title="Return to Landing Page"
        >
          <div className="w-10 h-10 rounded-lg bg-[#2d363e] flex items-center justify-center overflow-hidden border border-[#3c494e] glow-accent">
            <SentinelLogo className="w-6.5 h-6.5" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold text-[#00d1ff] leading-none uppercase tracking-wide">
              Asset Sentinel
            </span>
            <span className="text-[#bbc9cf] text-[9px] uppercase tracking-[0.2em] mt-1 font-semibold">
              Enterprise Tier
            </span>
          </div>
        </div>

        {/* Navigation links section */}
        <ul className="flex-1 flex flex-col gap-1.5 overflow-y-auto">
          <li>
            <button 
              onClick={() => setIsMobileSidebarOpen(false)}
              className="w-full bg-[#00d1ff]/10 text-[#00d1ff] border-r-4 border-[#00d1ff] flex items-center gap-3 px-3 py-2.5 rounded-l-lg hover:bg-[#00d1ff]/15 transition-all text-xs font-bold uppercase tracking-wider text-left"
            >
              <Activity className="w-4.5 h-4.5" />
              Dashboard
            </button>
          </li>
          <li>
            <button 
              onClick={() => handleSidebarAction(handleOpenMonitoringPanel)}
              className="w-full text-[#bbc9cf] hover:text-[#0a0] hover:bg-[#2d363e]/40 transition-all flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider text-left"
            >
              <Cpu className="w-4.5 h-4.5 text-[#bbc9cf]" />
              Monitoring
            </button>
          </li>
          <li>
            <button 
              onClick={() => handleSidebarAction(handleOpenAnalyticsPanel)}
              className="w-full text-[#bbc9cf] hover:text-[#00d1ff] hover:bg-[#2d363e]/40 transition-all flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider text-left"
            >
              <Zap className="w-4.5 h-4.5 text-[#bbc9cf]" />
              Analytics
            </button>
          </li>
          <li>
            <button 
              onClick={() => handleSidebarAction(handleOpenAssetHistory)}
              className="w-full text-[#bbc9cf] hover:text-[#60a5fa] hover:bg-[#2d363e]/30 transition-all flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider text-left"
            >
              <Layers className="w-4.5 h-4.5 text-[#bbc9cf]" />
              Asset History
            </button>
          </li>
          <li>
            <button 
              className="w-full text-[#bbc9cf] hover:text-[#00d1ff] hover:bg-[#2d363e]/40 transition-all flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider text-left"
              onClick={() => handleSidebarAction(handleShowDevices)}
            >
              <Database className="w-4.5 h-4.5 text-[#bbc9cf]" />
              Devices ({assets.length})
            </button>
          </li>
          {!isDemoMode && (
            <li>
              <button 
                onClick={() => handleSidebarAction(handleNavigateReports)}
                className="w-full text-[#bbc9cf] hover:text-[#00d1ff] hover:bg-[#2d363e]/40 transition-all flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider text-left"
              >
                <FileSpreadsheet className="w-4.5 h-4.5 text-[#bbc9cf]" />
                Reports
              </button>
            </li>
          )}
        </ul>

        {/* Critical Alerts Center CTA */}
        <div className="mt-4 mb-4">
          <button 
            onClick={() => handleSidebarAction(handleNavigateCriticalState)}
            className="w-full flex items-center justify-between bg-red-950/20 border border-red-500/30 hover:bg-red-950/45 transition-colors rounded-lg px-3 py-2.5 group cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-red-400 text-[10px] font-bold uppercase tracking-wider">
                Critical State
              </span>
            </div>
            <span className="bg-red-500 text-[#001f28] text-xs font-bold px-2 py-0.5 rounded-full animate-pulse indicator-pulse shadow-[0_0_8px_#ef4444]">
              {kpiStats.criticalAlerts}
            </span>
          </button>
        </div>

        {/* Navigation Sidebar Footer Links */}
        <div className="border-t border-[#3c494e]/30 pt-4 mt-auto">
          <ul className="flex flex-col gap-1.5 text-xs">
            <li>
              <button 
                onClick={() => handleSidebarAction(() => setIsSupportCenterOpen(true))}
                className="w-full text-[#bbc9cf] hover:text-[#00d1ff] hover:bg-[#2d363e]/40 transition-all flex items-center gap-3 px-3 py-2 rounded-lg text-left"
              >
                <HelpCircle className="w-4.5 h-4.5 text-[#bbc9cf]" />
                <span>Support Status</span>
              </button>
            </li>
            <li>
              <button 
                id="sidebar-signout-btn"
                onClick={() => handleSidebarAction(isDemoMode ? () => onNavigate("landing") : onSignOut)}
                className="w-full text-[#bbc9cf] hover:text-red-400 hover:bg-[#2d363e]/40 transition-all flex items-center gap-3 px-3 py-2 rounded-lg text-left pointer-events-auto"
              >
                <LogOut className="w-4.5 h-4.5 text-[#bbc9cf]" />
                <span>{isDemoMode ? "Exit Demo" : "Sign Out"}</span>
              </button>
            </li>
          </ul>
        </div>

      </nav>

      {/* Main Content Dashboard Frame */}
      <main id="dashboard-main-canvas" className="flex-1 ml-0 md:ml-64 flex min-h-0 flex-col h-full bg-[#0b141c] relative overflow-hidden">
        
        {/* Demo Mode Banner */}
        {isDemoMode && (
          <div id="demo-badge-banner" className="bg-amber-950/40 border-b border-amber-500/20 text-amber-300 px-6 py-2.5 flex items-center justify-between text-xs font-mono select-none">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></div>
              <span className="font-extrabold uppercase tracking-widest">Demo Mode – Read Only Preview</span>
            </div>
            <button 
              onClick={() => onNavigate("landing")}
              className="text-[10px] uppercase font-bold tracking-widest px-2.5 py-1 rounded bg-amber-600/20 border border-amber-500/30 hover:bg-amber-600/30 transition-all active:scale-95 cursor-pointer text-amber-200"
            >
              Exit Demo
            </button>
          </div>
        )}

        {/* Mobile Top Navigation Bar */}
        <header className="md:hidden h-16 bg-[#182028] border-b border-[#3c494e]/30 flex items-center justify-between px-4 sticky top-0 z-30 select-none">
          <div className="flex items-center gap-2">
            <button
              aria-label="Open navigation menu"
              onClick={() => setIsMobileSidebarOpen(true)}
              className="min-h-10 min-w-10 -ml-2 rounded-lg flex items-center justify-center text-[#00d1ff] hover:bg-[#2d363e]/60 active:scale-95 transition-all"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="font-extrabold text-[#dae3ee] tracking-tight">System Overview</span>
          </div>
          <button 
            onClick={isDemoMode ? () => onNavigate("landing") : onSignOut}
            className="flex items-center gap-1.5 text-xs text-[#bbc9cf] border border-[#3c494e]/50 rounded px-2.5 py-1"
          >
            <LogOut className="w-3.5 h-3.5" />
            {isDemoMode ? "Exit Demo" : "Exit"}
          </button>
        </header>

        {/* Scrollable command workspace content */}
        <div
          id="scrolling-command-workspace"
          ref={workspaceRef}
          onScroll={(event) => {
            persistScrollPosition("workspaceScrollTop", event.currentTarget.scrollTop);
          }}
          className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4 md:p-8 pb-10 md:pb-12 flex flex-col gap-6 select-text selection:bg-[#00d1ff]/20"
        >
          
          {/* Desktop Heading Segment */}
          <div className="hidden md:flex justify-between items-end mb-2">
            <div>
              <h1 className="text-3xl font-black text-[#dae3ee] tracking-tight">System Overview</h1>
              <p className="text-[#bbc9cf] text-sm mt-1">
                Real-time asset telemetry and compliance posture check.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#bbc9cf] flex items-center gap-2 bg-[#182028] px-3.5 py-1.5 rounded-full border border-[#00d1ff]/20">
                <span className="w-2 h-2 rounded-full bg-[#00d1ff] inline-block animate-ping"></span>
                Secure Live Connection
              </span>
            </div>
          </div>

          {/* KPI Dashboard stats row (Grid of 6 matching the exact KPI metrics in 3rd screenshot) */}
          <section id="kpi-scorecard-row" className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            
            {/* KPI 1 */}
            <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden group hover:border-[#00d1ff]/30 transition-all duration-300 bg-[#161B22]/80 border border-white/5 select-none">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Total Assets</span>
                <Server className="w-3.5 h-3.5 text-[#859399]" />
              </div>
              <div className="text-2xl font-black text-[#dae3ee] mt-1">
                {kpiStats.totalAssets.toLocaleString()}
              </div>
              <div className="flex items-center gap-1 text-[#00d1ff] text-[10px] mt-2">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>+2.4% vs last week</span>
              </div>
              <div className="absolute -bottom-8 -right-8 w-20 h-20 bg-[#00d1ff]/5 rounded-full blur-xl group-hover:bg-[#00d1ff]/12 transition-all"></div>
            </div>

            {/* KPI 2 */}
            <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden group hover:border-[#00d1ff]/30 transition-all duration-300 bg-[#161B22]/80 border border-white/5 select-none">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Online Devices</span>
                <div id="kpi-online-glow" className="w-2 h-2 rounded-full bg-[#00d1ff] glow-active"></div>
              </div>
              <div className="text-2xl font-black text-[#dae3ee] mt-1">
                {kpiStats.onlineDevices.toLocaleString()}
              </div>
              <div className="w-full h-6 mt-2 relative">
                {/* Embedded dynamic SVG sparkline */}
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 24">
                  <path 
                    fill="none" 
                    stroke="#00d1ff" 
                    strokeWidth="2" 
                    d="M 0 18 Q 15 12 30 15 T 60 8 T 80 14 T 100 3" 
                    className="sparkline-path"
                  />
                </svg>
              </div>
            </div>

            {/* KPI 3 */}
            <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden group hover:border-[#859399]/40 transition-all duration-300 bg-[#161B22]/80 border border-white/5 select-none">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Offline Devices</span>
                <div className="w-2 h-2 rounded-full bg-[#859399]"></div>
              </div>
              <div className="text-2xl font-black text-[#dae3ee] mt-1">
                {kpiStats.offlineDevices.toLocaleString()}
              </div>
              <div className="text-[10px] text-[#bbc9cf] mt-auto pb-1 block">
                14.8% of total fleet
              </div>
            </div>

            {/* KPI 4 with tiny micro-avatars */}
            <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden group hover:border-[#00d1ff]/30 transition-all duration-300 bg-[#161B22]/80 border border-white/5 select-none">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#bbc9cf]">Active Users</span>
                <Smartphone className="w-3.5 h-3.5 text-[#859399]" />
              </div>
              <div className="text-2xl font-black text-[#dae3ee] mt-1">
                {kpiStats.activeUsers}
              </div>
              <div className="flex items-center -space-x-1.5 mt-auto pb-1">
                <div className="w-4 h-4 rounded-full bg-slate-700 border border-[#0A0C10] overflow-hidden">
                  <div className="w-full h-full bg-[#3c494e] text-[6px] text-white flex items-center justify-center font-bold">SJ</div>
                </div>
                <div className="w-4 h-4 rounded-full bg-slate-600 border border-[#0A0C10] overflow-hidden">
                  <div className="w-full h-full bg-[#00566a] text-[6px] text-[#00d1ff] flex items-center justify-center font-bold">MR</div>
                </div>
                <div className="w-4 h-4 rounded-full bg-slate-500 border border-[#0A0C10] overflow-hidden">
                  <div className="w-full h-full bg-orange-900 text-[6px] text-orange-200 flex items-center justify-center font-bold">DK</div>
                </div>
                <div className="w-4 h-4 rounded-full bg-[#182028] border border-[#0A0C10] flex items-center justify-center text-[7px] text-[#dae3ee] font-mono font-bold">
                  +8k
                </div>
              </div>
            </div>

            {/* KPI 5 Critical alert heart-beat sparkline */}
            <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden bg-red-950/10 border border-red-500/25 select-none">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold uppercase tracking-wider text-red-400">Critical Alerts</span>
                <div className="w-2 h-2 rounded-full bg-red-400 glow-critical animate-ping"></div>
              </div>
              <div className="text-2xl font-black text-red-400 mt-1">
                {kpiStats.criticalAlerts}
              </div>
              <div className="w-full h-6 mt-2 relative">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 24">
                  <path 
                    fill="none" 
                    stroke="#f87171" 
                    strokeWidth="2" 
                    d="M 0 18 L 15 18 L 22 2 L 31 22 L 40 18 Z M 40 18 L 100 18" 
                    className="sparkline-path"
                  />
                </svg>
              </div>
            </div>

            {/* KPI 6 */}
            <div className="glass-panel rounded-xl p-4 flex flex-col gap-2 relative overflow-hidden group hover:border-amber-500/40 transition-all duration-300 bg-[#161B22]/80 border border-white/5 select-none">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold uppercase tracking-wider text-amber-500">Sec Incidents</span>
                <div className="w-2 h-2 rounded-full bg-amber-500 glow-warning"></div>
              </div>
              <div className="text-2xl font-black text-amber-500 mt-1 col-span-2">
                {kpiStats.securityIncidents}
              </div>
              <div className="flex items-center gap-1 text-amber-500 text-[10px] mt-auto pb-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                <span>Requires review</span>
              </div>
            </div>

          </section>

          {/* Main command data list console block */}
          <section id="fleet-telemetry-panel" className="flex-none xl:flex-1 rounded-2xl flex flex-col overflow-hidden min-h-[320px] md:min-h-[500px] bg-[linear-gradient(145deg,#121A27_0%,#101827_55%,#07111F_100%)] border border-[#334155]/80 shadow-[0_22px_70px_rgba(2,8,23,0.36)]">
            
            {/* Table Toolbar Section */}
            <div className="p-4 border-b border-[#334155]/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[linear-gradient(90deg,rgba(56,189,248,0.08),rgba(52,211,153,0.05),rgba(245,158,11,0.04))]">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-bold text-[#F8FAFC]">Real-Time Fleet Telemetry</h2>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300/30 bg-emerald-300/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-emerald-200">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" />
                    Online First
                  </span>
                </div>
                <p className="text-xs text-[#bbc9cf] font-light mt-0.5">Live endpoints are promoted first. Offline devices remain visible for audit history.</p>
              </div>
              <div className="flex w-full sm:w-auto items-center gap-2">
                <button
                  onClick={handleViewProductivity}
                  title="Open productivity analytics"
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-violet-400/35 bg-violet-500/10 px-3 py-2 text-xs font-bold text-violet-100 shadow-[0_0_18px_rgba(167,139,250,0.12)] transition-all hover:-translate-y-0.5 hover:border-emerald-300/40 hover:bg-emerald-500/10 hover:text-emerald-100"
                >
                  <Zap className="h-4 w-4 text-emerald-300" />
                  <span className="hidden lg:inline">Productivity Insights</span>
                </button>
                
                {/* Functional search block */}
                <div className="relative w-full sm:w-64">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#bbc9cf]" />
                  <input 
                    className="w-full bg-[#0D1117] border border-[#3c494e]/60 text-xs font-mono text-[#dae3ee] rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-[#00d1ff] focus:ring-1 focus:ring-[#00d1ff] placeholder-[#859399]/70 transition-all font-light" 
                    placeholder="Search query (hostname, IP, owner)..." 
                    type="text"
                    value={searchQuery}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button 
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#bbc9cf] hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Filter indicators */}
                <button 
                  onClick={() => alert("WHETSTONE SYSTEM: Dynamic whitelists filters initialized on subnet routing cards.")}
                  title="Initialize local subnet Whitelists filter"
                  className="bg-[#2d363e]/70 hover:bg-[#313a43] border border-[#3c494e] text-[#dae3ee] p-2 rounded-lg flex items-center justify-center transition-colors cursor-pointer"
                >
                  <Filter className="w-4 h-4 text-[#bbc9cf]" />
                </button>

                {/* CSV Export Action Button */}
                {!isDemoMode && (
                  <button 
                    id="excel-export-btn"
                    onClick={handleExportCSVReport}
                    title="Generate dynamic corporate CSV spreadsheets report"
                    className="bg-[#00d1ff]/10 hover:bg-[#00d1ff]/20 border border-[#00d1ff]/30 text-[#00d1ff] p-2 rounded-lg flex items-center justify-center transition-colors cursor-pointer"
                  >
                    <Download className="w-4 h-4 text-[#00d1ff]" />
                  </button>
                )}

              </div>
            </div>

            {/* Dynamic Fleet Telemetry Grid Table */}
            <div ref={assetsTableRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain">
              <table className="w-full table-fixed text-left border-collapse">
                <thead className="bg-[#060f16]/90 backdrop-blur-md sticky top-0 z-10 text-[10px] font-bold uppercase tracking-wider text-[#bbc9cf] border-b border-[#3c494e]/50">
                  <tr>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[18%]">Hostname</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[15%] hidden sm:table-cell">Employee Owner</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[13%]">Device Status</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[13%] hidden md:table-cell">IP Address</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[10%] hidden lg:table-cell">RAM</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[12%] hidden xl:table-cell">CPU Usage</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[11%]">Threat Level</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[13%] hidden lg:table-cell">Last Seen</th>
                    <th className="py-3.5 px-3 sm:px-4 font-semibold w-[8%] text-center">Quick</th>
                  </tr>
                </thead>
                <tbody className="text-xs font-mono tracking-wide text-[#dae3ee] divide-y divide-[#3c494e]/10">
                  {currentAssets.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="text-center py-12 text-[#bbc9cf] font-mono">
                        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2 animate-bounce" />
                        NO MATCHING CORE ASSETS SIGNATURES RESOLVED IN THIS MEMORY SECTOR.
                      </td>
                    </tr>
                  ) : (
                    currentAssets.map((asset: Asset, i: number) => {
                      // Status styling
                      const getStatusBadge = (status: Asset["status"]) => {
                        switch(status) {
                          case "Online":
                            return (
                              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-400/12 text-emerald-200 border border-emerald-300/35 shadow-[0_0_16px_rgba(52,211,153,0.12)]">
                                <span className="relative flex h-2 w-2">
                                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-60"></span>
                                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-300"></span>
                                </span>
                                <span className="text-[10px] font-black">LIVE</span>
                              </div>
                            );
                          case "Idle":
                            return (
                              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/25">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                                <span className="text-[10px] font-semibold">Idle</span>
                              </div>
                            );
                          case "Overload":
                            return (
                              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/25 animate-pulse">
                                <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                                <span className="text-[10px] font-semibold">Overload</span>
                              </div>
                            );
                          case "Offline":
                            return (
                              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-gray-500/15 text-gray-400 border border-gray-500/25">
                                <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                                <span className="text-[10px] font-semibold">Offline</span>
                              </div>
                            );
                        }
                      };

                      const getAlertIcon = (alertStatus: Asset["alertStatus"]) => {
                        if (alertStatus === "critical") {
                          return <AlertTriangle className="w-4 h-4 text-red-500 drop-shadow-[0_0_4px_#ef4444]" />;
                        } else if (alertStatus === "warning") {
                          return <AlertTriangle className="w-4 h-4 text-amber-400" />;
                        }
                        return <CheckCircle2 className="w-4 h-4 text-[#00d1ff]" />;
                      };
                      const threatLevel = getThreatLevel(asset);
                      const lastSeen = asset.lastSeenHuman || asset.lastSeen || asset.lastActiveTime || "No heartbeat";
                      const cpuPercent = parseInt(asset.cpuUsage || "0", 10) || 0;

                      return (
                        <tr 
                          key={assetIdentity(asset)} 
                          onClick={() => handleSelectAsset(asset)}
                          className={`group cursor-pointer transition-colors duration-150 ${
                            asset.status === "Online"
                              ? "bg-emerald-300/[0.035] hover:bg-emerald-300/[0.075] shadow-[inset_3px_0_0_rgba(52,211,153,0.8)]"
                              : "hover:bg-[#1B2338]/70 opacity-80 hover:opacity-100"
                          } ${assetIdentity(selectedAsset) === assetIdentity(asset) ? "bg-[#00d1ff]/10" : ""}`}
                          title={`Open complete asset profile for ${asset.hostname}`}
                        >
                          <td className="py-3 px-3 sm:px-4 font-bold text-white">
                            <div className="flex items-center gap-2 min-w-0">
                              <Laptop className={`w-3.5 h-3.5 shrink-0 ${asset.status === "Online" ? "text-emerald-300 drop-shadow-[0_0_8px_rgba(52,211,153,0.45)]" : "text-[#859399]"}`} />
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 truncate">
                                  <span className="truncate">{asset.hostname}</span>
                                  {asset.status === "Online" ? <span className="rounded border border-emerald-300/30 bg-emerald-300/10 px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wider text-emerald-200">Live</span> : null}
                                </div>
                                <div className="sm:hidden text-[10px] text-[#bbc9cf] font-normal truncate">{asset.employee}</div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-3 sm:px-4 text-[#bbc9cf] font-sans font-medium hidden sm:table-cell truncate">{asset.employee}</td>
                          <td className="py-3 px-3 sm:px-4">
                            {getStatusBadge(asset.status)}
                          </td>
                          <td className="py-3 px-3 sm:px-4 text-[#a4e6ff] hidden md:table-cell truncate">{asset.ipAddress}</td>
                          <td className="py-3 px-3 sm:px-4 font-semibold text-white hidden lg:table-cell truncate">{asset.ram}</td>
                          <td className="py-3 px-3 sm:px-4 hidden xl:table-cell">
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 flex-1 rounded-full bg-[#0D1117] border border-[#3c494e]/40 overflow-hidden">
                                <div
                                  className="h-full bg-[#00d1ff] transition-all duration-500"
                                  style={{ width: `${Math.min(100, cpuPercent)}%` }}
                                />
                              </div>
                              <span className="text-[#dae3ee] font-semibold w-16 text-right">{asset.cpuUsage}</span>
                            </div>
                          </td>
                          <td className="py-3 px-3 sm:px-4">
                            <span className={`inline-flex items-center justify-center min-w-12 rounded-full px-2 py-0.5 border text-[10px] font-bold ${
                              threatLevel >= 80 ? "bg-red-500/10 text-red-400 border-red-500/30" :
                              threatLevel >= 40 ? "bg-amber-500/10 text-amber-400 border-amber-500/30" :
                              "bg-[#00d1ff]/10 text-[#00d1ff] border-[#00d1ff]/25"
                            }`}>
                              {threatLevel}
                            </span>
                          </td>
                          <td className={`py-3 px-3 sm:px-4 font-sans text-[11px] hidden lg:table-cell truncate ${asset.status === "Online" ? "text-emerald-100" : "text-[#bbc9cf]"}`}>{lastSeen}</td>
                          <td className="py-3 px-3 sm:px-4 text-center">
                            <div className="flex justify-center select-none group-hover:scale-110 transition-transform">
                              {getAlertIcon(asset.alertStatus)}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Table Footer with reactive paging controls */}
            <div className="p-4 border-t border-[#3c494e]/30 flex flex-col sm:flex-row justify-between sm:items-center gap-3 bg-[#060f16]/85 text-[11px] text-[#bbc9cf] select-none">
              <span className="leading-relaxed">
                Showing {filteredAssets.length ? (currentPage - 1) * itemsPerPage + 1 : 0} - {Math.min(currentPage * itemsPerPage, filteredAssets.length)} of {filteredAssets.length} filtered assets (Total fleet scaled at 14,209)
              </span>
              <div className="flex items-center gap-3 self-end sm:self-auto">
                <button 
                  onClick={() => setCurrentPage((prev: number) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="min-h-10 min-w-10 p-2 hover:bg-[#2d363e]/50 rounded border border-[#3c494e] disabled:opacity-40 transition-colors cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 font-mono font-semibold">
                  Page {currentPage} of {totalPages}
                </span>
                <button 
                  onClick={() => setCurrentPage((prev: number) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="min-h-10 min-w-10 p-2 hover:bg-[#2d363e]/50 rounded border border-[#3c494e] disabled:opacity-40 transition-colors cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

          </section>

          {/* Scrolling Command Terminal Live Event Logs footer panel */}
          <section id="streaming-events-feed" className="shrink-0 bg-[#141c24] border border-[#3c494e]/40 rounded-xl p-4 md:p-5 overflow-hidden">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#bbc9cf] select-none mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00d1ff] animate-pulse"></span>
              Live Commands & Anomaly Log Stream
            </h3>
            <div id="logs-stream-container" className="h-48 sm:h-40 md:h-32 xl:h-28 overflow-y-auto overscroll-contain touch-pan-y flex flex-col gap-1.5 font-mono text-[11px] select-text pr-1">
              {displayedLogs.map((log: SecurityFeedItem, index: number) => {
                const getLogColor = (type: string) => {
                  if (type === "critical") return "text-red-400 font-semibold";
                  if (type === "warning") return "text-amber-400";
                  return "text-[#bbc9cf]";
                };

                return (
                  <div key={index} className={`flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4 hover:bg-white/5 p-2 sm:p-1 rounded transition-colors ${getLogColor(log.type)}`}>
                    <span className="text-[#00d1ff]/50 shrink-0 select-none">[{log.timestamp}]</span>
                    <span className="bg-[#182028] px-1.5 py-0.1 select-none border border-white/5 rounded shrink-0 leading-none text-[9px] text-[#00d1ff]">{log.node}</span>
                    <span className="leading-snug">{log.message}</span>
                  </div>
                );
              })}
            </div>
          </section>

        </div>

        {/* Global Glassmorphic Sliding Drawer Sheet (slides from the right side) */}
{isMonitoringOpen && (
          <div 
            id="monitoring-modal-scaffolding"
            className="fixed inset-0 bg-[#060f16]/70 backdrop-blur-md z-50 flex justify-end transition-opacity duration-300"
            onClick={handleCloseMonitoringPanel}
          >
            <div 
              id="monitoring-modal-drawer"
              className="w-full max-w-xl bg-[#141c24]/95 border-l border-white/10 h-full overflow-y-auto p-4 sm:p-6 md:p-8 flex flex-col gap-6 shadow-2xl relative select-text"
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
              <button 
                id="monitoring-drawer-close-btn"
                onClick={handleCloseMonitoringPanel}
                className="absolute top-5 right-5 text-[#bbc9cf] hover:text-white p-1 hover:bg-[#2d363e]/60 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-start gap-3.5 select-none pr-8 border-b border-[#3c494e]/30 pb-5">
                <div className="w-11 h-11 rounded-lg bg-[#222b33] border border-[#3c494e] flex items-center justify-center shrink-0">
                  <Cpu className="w-6 h-6 text-[#00d1ff] fill-[#00d1ff]/5" />
                </div>
                <div>
                  <h2 className="text-xl font-black text-white leading-tight flex items-center gap-2">
                    Monitoring Panel
                  </h2>
                  <p className="text-xs text-[#bbc9cf] font-light mt-1">
                    Live monitoring detail derived from the current Flask asset and alert feed.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-[#0d1117] border border-white/5 rounded-xl p-4">
                  <p className="text-[10px] uppercase tracking-wider text-[#7f9faf] mb-3">Asset Overview</p>
                  <div className="space-y-2 text-sm text-[#bbc9cf]">
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Hostname</span><span>{monitoringTarget?.hostname ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">IP Address</span><span>{monitoringTarget?.ipAddress ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">CPU Model</span><span>{monitoringTarget?.cpuModel ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">RAM Size</span><span>{monitoringTarget?.ram ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">BIOS Serial</span><span>{monitoringTarget?.biosSerial ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Baseboard Serial</span><span>{monitoringTarget?.history.find(item => item.includes("Baseboard Serial"))?.split(": ")[1] ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">MAC Address</span><span>{monitoringTarget?.history.find(item => item.includes("MAC Address"))?.split(": ")[1] ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Windows Version</span><span>{monitoringTarget?.os ?? "Unknown"}</span></div>
                  </div>
                </div>

                <div className="bg-[#0d1117] border border-white/5 rounded-xl p-4">
                  <p className="text-[10px] uppercase tracking-wider text-[#7f9faf] mb-3">Live Monitoring</p>
                  <div className="space-y-2 text-sm text-[#bbc9cf]">
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Monitoring Status</span><span>{monitoringTarget?.status ?? "Unknown"}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Last Scan Time</span><span>{monitoringMetrics.lastScanTime}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Total Alerts</span><span>{monitoringMetrics.totalAlerts}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Critical Alert Count</span><span>{monitoringMetrics.criticalCount}</span></div>
                    <div className="flex justify-between gap-3"><span className="text-[#94a3b8]">Warning Alert Count</span><span>{monitoringMetrics.warningCount}</span></div>
                  </div>
                </div>
              </div>

              <div className="grid gap-4">
                <div className="bg-[#0d1117] border border-white/5 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#7f9faf]">Recent RAM_CHANGE Events</p>
                  </div>
                  <div className="space-y-2 text-sm text-[#bbc9cf]">
                    {monitoringMetrics.ramChanges.length > 0 ? (
                      monitoringMetrics.ramChanges.map((log, idx) => (
                        <div key={idx} className="rounded-lg bg-[#141b22] border border-white/5 p-3">
                          <div className="text-[#94a3b8] text-[10px] uppercase tracking-wider">{log.timestamp}</div>
                          <div>{log.message}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-[#8697a8] text-sm">No recent RAM change events.</div>
                    )}
                  </div>
                </div>

                <div className="bg-[#0d1117] border border-white/5 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-[10px] uppercase tracking-wider text-[#7f9faf]">Recent MOTHERBOARD_CHANGE Events</p>
                  </div>
                  <div className="space-y-2 text-sm text-[#bbc9cf]">
                    {monitoringMetrics.motherboardChanges.length > 0 ? (
                      monitoringMetrics.motherboardChanges.map((log, idx) => (
                        <div key={idx} className="rounded-lg bg-[#141b22] border border-white/5 p-3">
                          <div className="text-[#94a3b8] text-[10px] uppercase tracking-wider">{log.timestamp}</div>
                          <div>{log.message}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-[#8697a8] text-sm">No recent motherboard change events.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {isAnalyticsOpen && (
          <div 
            id="analytics-modal-scaffolding"
            className="fixed inset-0 bg-[#060f16]/80 backdrop-blur-md z-50 flex justify-center items-start p-3 sm:p-6 md:pt-16 transition-opacity duration-300"
            onClick={handleCloseAnalyticsPanel}
          >
            <div 
              id="analytics-modal-drawer"
              className="w-full max-w-6xl max-h-[calc(100vh-1.5rem)] md:max-h-[calc(100vh-8rem)] bg-[#0c1318]/95 border border-white/10 rounded-2xl md:rounded-3xl overflow-y-auto shadow-2xl shadow-[#000000]/50"
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
              <div className="border-b border-[#1f2a34]/70 px-4 sm:px-6 py-5 flex items-start justify-between gap-4 bg-[#0f1720]/80">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full bg-[#002a3f] px-3 py-1 text-[10px] sm:text-xs uppercase tracking-[0.2em] sm:tracking-[0.35em] text-[#7dd3fc] font-semibold">
                    <Zap className="w-4 h-4" /> Executive Intelligence
                  </div>
                  <h2 className="mt-4 text-2xl sm:text-3xl font-black text-white tracking-tight">Analytics Intelligence</h2>
                  <p className="mt-2 text-sm text-[#9ca3af] leading-relaxed max-w-2xl">
                    Premium SOC-level analytics synthesized from live asset and alert telemetry, tailored for enterprise security leadership.
                  </p>
                </div>
                <button 
                  id="analytics-drawer-close-btn"
                  onClick={handleCloseAnalyticsPanel}
                  className="text-[#cbd5e1] hover:text-white p-3 rounded-full bg-[#111827]/80 border border-[#334155]/60 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-4 sm:p-6 grid gap-6">
                <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="rounded-3xl bg-[#111827] border border-[#1f2937]/70 p-5">
                    <p className="text-[10px] uppercase tracking-[0.35em] text-[#60a5fa] mb-4">Executive Overview</p>
                    <div className="grid gap-3">
                      <div className="flex items-center justify-between rounded-2xl bg-[#0f172a]/80 p-3">
                        <span className="text-xs uppercase text-[#94a3b8]">Total Assets</span>
                        <span className="text-xl font-semibold text-white">{kpiStats.totalAssets}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl bg-[#0f172a]/80 p-3">
                        <span className="text-xs uppercase text-[#94a3b8]">Online Devices</span>
                        <span className="text-xl font-semibold text-white">{kpiStats.onlineDevices}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl bg-[#0f172a]/80 p-3">
                        <span className="text-xs uppercase text-[#94a3b8]">Offline Devices</span>
                        <span className="text-xl font-semibold text-white">{kpiStats.offlineDevices}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl bg-[#0f172a]/80 p-3">
                        <span className="text-xs uppercase text-[#94a3b8]">Critical Alerts</span>
                        <span className="text-xl font-semibold text-[#f87171]">{analyticsMetrics.criticalCount}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl bg-[#0f172a]/80 p-3">
                        <span className="text-xs uppercase text-[#94a3b8]">Warning Alerts</span>
                        <span className="text-xl font-semibold text-[#fbbf24]">{analyticsMetrics.warningCount}</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl bg-[#0f172a]/80 p-3">
                        <span className="text-xs uppercase text-[#94a3b8]">Active Users</span>
                        <span className="text-xl font-semibold text-white">{kpiStats.activeUsers}</span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-3xl bg-[#111827] border border-[#1f2937]/70 p-5 sm:col-span-2 lg:col-span-1">
                    <p className="text-[10px] uppercase tracking-[0.35em] text-[#60a5fa] mb-4">Security Intelligence</p>
                    <div className="grid gap-4">
                      <div className="rounded-3xl bg-[#0f172a]/90 border border-[#1f2937]/70 p-4">
                        <p className="text-sm text-[#cbd5e1] font-semibold">Device Integrity Score</p>
                        <p className="mt-3 text-4xl font-black text-white">{analyticsMetrics.deviceIntegrityScore}%</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.3em] text-[#94a3b8]">Computed from current alert severity and asset health.</p>
                      </div>
                      <div className="rounded-3xl bg-[#0f172a]/90 border border-[#1f2937]/70 p-4">
                        <p className="text-sm text-[#cbd5e1] font-semibold">Security Posture</p>
                        <p className="mt-3 text-sm text-[#e2e8f0] leading-relaxed">{analyticsMetrics.securityPostureSummary}</p>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="rounded-3xl bg-[#0f172a]/90 border border-[#1f2937]/70 p-4">
                          <p className="text-[10px] uppercase tracking-[0.35em] text-[#94a3b8] mb-2">RAM Change Events</p>
                          <p className="text-3xl font-black text-white">{analyticsMetrics.recentRamChanges.length}</p>
                        </div>
                        <div className="rounded-3xl bg-[#0f172a]/90 border border-[#1f2937]/70 p-4">
                          <p className="text-[10px] uppercase tracking-[0.35em] text-[#94a3b8] mb-2">Motherboard Change Events</p>
                          <p className="text-3xl font-black text-white">{analyticsMetrics.recentMotherboardChanges.length}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-3xl bg-[#111827] border border-[#1f2937]/70 p-5">
                    <p className="text-[10px] uppercase tracking-[0.35em] text-[#60a5fa] mb-4">Asset Intelligence</p>
                    <div className="space-y-3 text-sm text-[#cbd5e1]">
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <p className="text-xs uppercase tracking-[0.35em] text-[#94a3b8]">Most Alerted Device</p>
                        <p className="mt-2 text-lg font-semibold text-white">{analyticsMetrics.mostAlertedNode}</p>
                      </div>
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <p className="text-xs uppercase tracking-[0.35em] text-[#94a3b8]">Most Recent Device</p>
                        <p className="mt-2 text-lg font-semibold text-white">{analyticsMetrics.mostRecentDevice}</p>
                      </div>
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <p className="text-xs uppercase tracking-[0.35em] text-[#94a3b8]">Unique Devices Monitored</p>
                        <p className="mt-2 text-lg font-semibold text-white">{analyticsMetrics.uniqueDevicesMonitored}</p>
                      </div>
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <p className="text-xs uppercase tracking-[0.35em] text-[#94a3b8]">Highest Risk Device</p>
                        <p className="mt-2 text-lg font-semibold text-white">{analyticsMetrics.highestRiskDevice}</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-3xl bg-[#111827] border border-[#1f2937]/70 p-5">
                    <p className="text-[10px] uppercase tracking-[0.35em] text-[#60a5fa] mb-4">Risk Distribution</p>
                    <div className="space-y-3">
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <div className="flex items-center justify-between mb-2"><span className="text-sm text-[#94a3b8]">Critical</span><span className="text-white font-semibold">{analyticsMetrics.criticalCount}</span></div>
                        <div className="h-2 rounded-full bg-[#111827]"><div className="h-2 rounded-full bg-[#f87171]" style={{ width: `${Math.min(100, analyticsMetrics.criticalCount * 14)}%` }} /></div>
                      </div>
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <div className="flex items-center justify-between mb-2"><span className="text-sm text-[#94a3b8]">Warning</span><span className="text-white font-semibold">{analyticsMetrics.warningCount}</span></div>
                        <div className="h-2 rounded-full bg-[#111827]"><div className="h-2 rounded-full bg-[#fbbf24]" style={{ width: `${Math.min(100, analyticsMetrics.warningCount * 14)}%` }} /></div>
                      </div>
                      <div className="rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                        <div className="flex items-center justify-between mb-2"><span className="text-sm text-[#94a3b8]">Informational</span><span className="text-white font-semibold">{analyticsMetrics.infoCount}</span></div>
                        <div className="h-2 rounded-full bg-[#111827]"><div className="h-2 rounded-full bg-[#60a5fa]" style={{ width: `${Math.min(100, analyticsMetrics.infoCount * 12)}%` }} /></div>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="rounded-3xl bg-[#111827] border border-[#1f2937]/70 p-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.35em] text-[#60a5fa]">Alert Timeline</p>
                      <h3 className="mt-2 text-lg font-semibold text-white">Recent alert activity</h3>
                    </div>
                    <span className="text-[10px] uppercase tracking-[0.35em] text-[#94a3b8]">Latest 8 events</span>
                  </div>
                  <div className="space-y-3">
                    {analyticsMetrics.alertTimeline.length > 0 ? (
                      analyticsMetrics.alertTimeline.map((log, idx) => (
                        <div key={idx} className="grid grid-cols-1 sm:grid-cols-[110px_1fr_120px_90px] gap-2 sm:gap-3 sm:items-center rounded-3xl bg-[#0f172a]/80 p-4 border border-[#1f2937]/50">
                          <div className="text-[11px] uppercase tracking-[0.25em] text-[#94a3b8]">{log.timestamp}</div>
                          <div className="text-sm text-white font-semibold">{log.node}</div>
                          <div className="text-sm text-[#cbd5e1] truncate">{log.message}</div>
                          <div className={`text-xs font-bold uppercase tracking-[0.3em] ${log.type === "critical" ? "text-[#f87171]" : log.type === "warning" ? "text-[#fbbf24]" : "text-[#60a5fa]"}`}>{log.type}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-[#94a3b8] text-sm">No alert timeline events available.</div>
                    )}
                  </div>
                </section>
              </div>
            </div>
          </div>
        )}

        {isAssetHistoryOpen && (
          <div
            id="asset-history-scaffolding"
            className="fixed inset-0 bg-[#060f16]/70 backdrop-blur-md z-50 flex justify-center items-start p-3 sm:p-6 md:pt-16 transition-opacity duration-300 overflow-y-auto"
            onClick={handleCloseAssetHistory}
          >
            <div className="w-full max-w-6xl p-0 sm:p-6" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
              <AssetHistory assets={assets} liveLogs={liveLogs} onClose={handleCloseAssetHistory} />
            </div>
          </div>
        )}

        {isCriticalAlertsOpen && (
          <div
            id="critical-alerts-modal-scaffolding"
            className="fixed inset-0 bg-[#05070b]/85 backdrop-blur-md z-50 flex justify-center items-start p-3 sm:p-6 md:pt-12 transition-opacity duration-300 overflow-y-auto"
            onClick={handleCloseCriticalAlertsPanel}
          >
            <div
              id="critical-alerts-modal"
              className="w-full max-w-6xl max-h-[calc(100vh-1.5rem)] md:max-h-[calc(100vh-6rem)] overflow-y-auto bg-[#080d12]/98 border border-red-500/25 rounded-xl shadow-2xl shadow-red-950/30"
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
              <div className="sticky top-0 z-10 border-b border-red-500/20 bg-[#0a1016]/95 px-4 sm:px-6 py-5 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-lg bg-red-950/30 border border-red-500/35 flex items-center justify-center shrink-0">
                    <ShieldAlert className="w-6 h-6 text-red-400" />
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.35em] text-red-300 font-bold">Critical Alerts Center</p>
                    <h2 className="mt-2 text-2xl font-black text-white tracking-tight">
                      {selectedCriticalAlert ? selectedCriticalAlert.alertType : "Active Critical Incidents"}
                    </h2>
                    <p className="mt-1 text-sm text-[#94a3b8]">
                      Dedicated incident triage view for critical security alerts only.
                    </p>
                  </div>
                </div>
                <button
                  id="critical-alerts-close-btn"
                  onClick={handleCloseCriticalAlertsPanel}
                  className="text-[#cbd5e1] hover:text-white p-2 rounded-lg bg-[#111827]/80 border border-white/10 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {!selectedCriticalAlert ? (
                <div className="p-4 sm:p-6">
                  {criticalAlertRecords.length === 0 ? (
                    <div className="min-h-[260px] flex flex-col items-center justify-center text-center border border-emerald-500/20 bg-emerald-950/10 rounded-xl p-8">
                      <CheckCircle2 className="w-10 h-10 text-emerald-400 mb-4" />
                      <p className="text-lg font-semibold text-white">No critical alerts are currently active.</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {criticalAlertRecords.map((alertRecord) => (
                        <button
                          key={alertRecord.id}
                          onClick={() => setSelectedCriticalAlert(alertRecord)}
                          className="text-left rounded-xl bg-[#0d1117] border border-red-500/20 hover:border-red-400/60 hover:bg-red-950/10 transition-all p-4 sm:p-5 cursor-pointer"
                        >
                          <div className="flex items-start justify-between gap-3 mb-4">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                                <span className="text-sm font-black text-white uppercase tracking-wider truncate">{alertRecord.alertType}</span>
                              </div>
                              <p className="mt-1 text-xs text-[#94a3b8] truncate">{alertRecord.description}</p>
                            </div>
                            <span className="shrink-0 rounded-full border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-red-300">
                              {resolveAlertStatus(alertRecord)}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-[11px]">
                            <DetailField label="Device Name" value={alertRecord.deviceName} accent />
                            <DetailField label="Employee" value={resolveAlertEmployee(alertRecord)} />
                            <DetailField label="Severity" value={alertRecord.severity} />
                            <DetailField label="Time" value={formatTelemetryTimestamp(alertRecord.time)} />
                            <DetailField label="Previous Value" value={alertRecord.previousValue} />
                            <DetailField label="Current Value" value={alertRecord.currentValue} />
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-4 sm:p-6 grid gap-5">
                  <section className="rounded-xl bg-[#0d1117] border border-red-500/25 p-4 sm:p-5">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-5">
                      <div>
                        <p className="text-[10px] uppercase tracking-[0.35em] text-red-300 font-bold">Incident Detail</p>
                        <h3 className="mt-2 text-xl font-black text-white">{selectedCriticalAlert.alertType}</h3>
                      </div>
                      <span className="self-start rounded-full border border-red-500/40 bg-red-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-red-300">
                        {resolveAlertStatus(selectedCriticalAlert)}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-[11px]">
                      <DetailField label="Alert Type" value={selectedCriticalAlert.alertType} accent />
                      <DetailField label="Device Name" value={selectedCriticalAlert.deviceName} />
                      <DetailField label="Employee" value={resolveAlertEmployee(selectedCriticalAlert)} />
                      <DetailField label="Severity" value={selectedCriticalAlert.severity} />
                      <DetailField label="Time" value={formatTelemetryTimestamp(selectedCriticalAlert.time)} />
                      <DetailField label="Alert Status" value={resolveAlertStatus(selectedCriticalAlert)} />
                    </div>
                  </section>

                  <section className="rounded-xl bg-[#0d1117] border border-white/10 p-4 sm:p-5 font-mono text-[11px]">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <DetailField label="Description" value={selectedCriticalAlert.description} />
                      <DetailField label="Previous Value" value={selectedCriticalAlert.previousValue} />
                      <DetailField label="Current Value" value={selectedCriticalAlert.currentValue} accent />
                    </div>
                  </section>

                  <div className="flex flex-col sm:flex-row gap-2 sm:justify-end border-t border-red-500/15 pt-4">
                    <button
                      onClick={() => handleViewCriticalAlertDevice(selectedCriticalAlert)}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#00d1ff]/10 hover:bg-[#00d1ff]/20 border border-[#00d1ff]/30 px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#00d1ff] transition-colors"
                    >
                      <Laptop className="w-4 h-4" />
                      View Device
                    </button>
                    <button
                      onClick={() => handleAcknowledgeCriticalAlert(selectedCriticalAlert)}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 px-4 py-2 text-xs font-bold uppercase tracking-wider text-emerald-300 transition-colors"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      Acknowledge
                    </button>
                    <button
                      onClick={handleCloseCriticalAlertsPanel}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1f2937]/80 hover:bg-[#334155]/80 border border-white/10 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white transition-colors"
                    >
                      <X className="w-4 h-4" />
                      Close
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {selectedAsset && (
          <div 
            id="asset-detail-scaffolding"
            className="fixed inset-0 bg-[#020617]/78 backdrop-blur-md z-50 flex justify-end transition-opacity duration-300"
            onClick={handleCloseAssetDetail}
          >
            <div 
              id="asset-detail-drawer"
            ref={assetDetailDrawerRef}
            onScroll={(event) => {
                persistScrollPosition("detailScrollTop", event.currentTarget.scrollTop);
            }}
              className="w-full max-w-7xl bg-[#0B1220] border-l border-[#2B3752] h-full overflow-y-auto p-4 sm:p-6 md:p-8 flex flex-col gap-5 shadow-2xl relative select-text font-sans"
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
              
              {/* Corner Close Box */}
              <button 
                id="drawer-close-btn"
                onClick={handleCloseAssetDetail}
                className="absolute top-5 right-5 z-20 text-[#bbc9cf] hover:text-white p-1 hover:bg-[#2d363e]/60 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Executive Header */}
              <div className="relative z-10 select-none overflow-visible rounded-3xl border border-[#2B3752] bg-[linear-gradient(135deg,#141B2D_0%,#0B1220_62%,#10233A_100%)] p-5 pr-14 sm:pr-16 shadow-[0_24px_70px_rgba(0,0,0,0.36)]">
                <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                  <div className="flex min-w-0 items-start gap-3.5">
                    <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center shrink-0 shadow-[0_0_24px_rgba(56,189,248,0.16)]">
                      <Monitor className="w-7 h-7 text-sky-300" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-white leading-tight flex flex-wrap items-center gap-2 break-words">
                        <span className="min-w-0 max-w-full break-all">{selectedAsset.hostname}</span>
                        <StatusChip status={selectedAsset.status} />
                        {selectedAsset.complianceStatus ? (
                          <span className="text-[11px] font-semibold text-emerald-300 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/30 shadow-[0_0_18px_rgba(34,197,94,0.16)]">Risk Low</span>
                        ) : (
                          <span className="text-[11px] font-semibold text-red-300 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/30 shadow-[0_0_18px_rgba(239,68,68,0.16)]">Risk Elevated</span>
                        )}
                      </h2>
                      <p className="text-sm text-[#a9bac7] mt-1">
                        {selectedAsset.status} • Last seen {selectedAsset.lastSeenHuman || formatTelemetryTimestamp(selectedAsset.lastSeen)}
                        {assetDetailLoading ? <span className="ml-2 text-sky-300">Refreshing...</span> : null}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-[#A8B3C7]">
                        <span className="flex items-center gap-2"><Laptop className="h-4 w-4 text-[#38BDF8]" />{selectedAsset.os}</span>
                        <span className="flex items-center gap-2"><User className="h-4 w-4 text-blue-300" />{selectedAsset.currentUser || selectedAsset.employee}</span>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap xl:justify-end">
                    <button onClick={() => handleAICorporateAudit(selectedAsset)} disabled={auditLoading || selectedAsset.status === "Offline"} className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#38BDF8]/35 bg-[#38BDF8] px-3.5 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[#07111F] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_0_24px_rgba(56,189,248,0.32)] disabled:cursor-not-allowed disabled:opacity-40">
                      <Sparkles className="h-4 w-4" />{auditLoading ? "Scanning" : "AI Audit"}
                    </button>
                    {!isDemoMode && (
                      <button onClick={() => handleTriggerTelemetryAlert(selectedAsset)} disabled={selectedAsset.status === "Offline" || selectedAsset.status === "Overload"} className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-500/35 bg-red-500/10 px-3.5 py-2.5 text-[11px] font-bold uppercase tracking-wider text-red-300 transition-all duration-200 hover:-translate-y-0.5 hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-35">
                        <AlertTriangle className="h-4 w-4" />Tamper
                      </button>
                    )}
                    {!isDemoMode && (
                      <button onClick={() => handleTacticalQuarantine(selectedAsset)} disabled={selectedAsset.status === "Offline"} className="inline-flex items-center justify-center gap-2 rounded-xl border border-amber-500/35 bg-amber-500/10 px-3.5 py-2.5 text-[11px] font-bold uppercase tracking-wider text-amber-300 transition-all duration-200 hover:-translate-y-0.5 hover:bg-amber-500/15 disabled:cursor-not-allowed disabled:opacity-35">
                        <Lock className="h-4 w-4" />Quarantine
                      </button>
                    )}
                    {!isDemoMode && (
                      <button onClick={() => handleReflashBIOSReset(selectedAsset)} className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#2B3752] bg-[#0F1728] px-3.5 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[#E2E8F0] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#1B2338]">
                        <RotateCcw className="h-4 w-4" />Reset
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="relative z-0 grid grid-cols-1 gap-4 pt-1 xl:grid-cols-2">
              <DetailSection title="Device Overview" icon={<Laptop className="w-5 h-5 text-sky-300" />} compact>
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  <DetailField label="Hostname" value={selectedAsset.hostname} accent compact />
                  <DetailField label="Logged-in User" value={selectedAsset.currentUser || selectedAsset.employee} compact />
                  <DetailField label="Device Status" value={<StatusChip status={selectedAsset.status} />} compact />
                  <DetailField label="Device ID" value={selectedAsset.deviceId} compact />
                  <DetailField label="IP Address" value={selectedAsset.ipAddress} accent compact />
                  <DetailField label="MAC Address" value={selectedAsset.macAddress} compact />
                  <DetailField label="Windows Version" value={selectedAsset.os} compact />
                  <DetailField label="CPU" value={selectedAsset.cpuModel} compact />
                  <DetailField label="RAM" value={selectedAsset.ram} compact />
                  <DetailField label="BIOS Serial" value={selectedAsset.biosSerial} compact />
                  <DetailField label="Motherboard Serial" value={selectedAsset.motherboardSerial} compact />
                  <DetailField label="UUID" value={selectedAsset.uuid} compact />
                  <DetailField label="Last Seen" value={`${selectedAsset.status} • Last seen ${selectedAsset.lastSeenHuman || formatTelemetryTimestamp(selectedAsset.lastSeen)}`} accent compact />
                  <DetailField label="Uptime" value={selectedAsset.uptime} compact />
                </div>
              </DetailSection>

              <DetailSection title="Login Activity" icon={<LogIn className="w-5 h-5 text-emerald-300" />} compact>
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  <DetailField label="Current Logged-in User" value={selectedAsset.currentUser || selectedAsset.employee} compact />
                  <DetailField label="Current Login Time" value={selectedAsset.lastLogin} compact />
                  <DetailField label="Last Logout Time" value={selectedAsset.lastLogout || "No logout recorded"} compact />
                  <DetailField label="Total Logins Today" value={selectedAsset.loginsToday ?? 0} compact />
                  <DetailField label="Total Logins This Week" value={selectedAsset.loginsThisWeek ?? 0} compact />
                  <DetailField label="Current Session Duration" value={selectedAsset.loginDuration} accent compact />
                  <DetailField label="Last Successful Login" value={formatTelemetryTimestamp(selectedAsset.lastSuccessfulLogin || selectedAsset.lastLogin)} compact />
                  <DetailField label="Last Failed Login" value={formatTelemetryTimestamp(selectedAsset.lastFailedLogin)} compact />
                </div>
              </DetailSection>
              </div>

              <section className="rounded-2xl border border-[#334155] bg-[linear-gradient(135deg,#111827_0%,#141B2D_54%,#0B1220_100%)] p-5 shadow-[0_18px_54px_rgba(2,8,23,0.34)]">
                <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#38BDF8]/45 bg-[#38BDF8]/12 shadow-[0_0_22px_rgba(56,189,248,0.2)]">
                      <Activity className="h-5 w-5 text-[#7DD3FC]" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold tracking-tight text-white">Active Application Timeline</h3>
                      <p className="text-sm text-[#A8B3C7]">Live foreground activity with newest entries first.</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => {
                        setPendingTimelineHistoryPreset(timelineHistoryPreset);
                        setPendingCustomHistoryStart(customHistoryStart);
                        setPendingCustomHistoryEnd(customHistoryEnd);
                        setIsTimelineSelectorOpen(true);
                      }}
                      className="inline-flex h-9 w-fit items-center gap-2 rounded-full border border-amber-300/35 bg-amber-300/10 px-3 py-1.5 text-xs font-semibold text-amber-100 shadow-[0_0_18px_rgba(245,158,11,0.1)] transition-colors hover:border-amber-200/55 hover:bg-amber-300/15"
                    >
                      <Search className="h-3.5 w-3.5" />
                      Activity History Search
                    </button>
                    <span className="inline-flex h-9 w-fit items-center gap-2 rounded-full border border-emerald-400/45 bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-200 shadow-[0_0_20px_rgba(52,211,153,0.16)]">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-300" />
                      Live Monitoring
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-[0.92fr_1.08fr] gap-5">
                  <div className="grid grid-cols-1 gap-3">
                    <div className="rounded-2xl border border-emerald-300/30 bg-[linear-gradient(135deg,rgba(16,185,129,0.12),rgba(15,23,42,0.86))] p-4 shadow-[0_16px_40px_rgba(16,185,129,0.08)]">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <span className="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-200">Current Application</span>
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300/35 bg-emerald-300/12 px-2 py-0.5 text-[9px] font-black uppercase text-emerald-100">
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" />
                          Active
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-[#0B1220]/80 text-emerald-100">
                          {timelineIconFor(selectedAsset.activeApplication || "")}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-xl font-black text-white">{selectedAsset.activeApplication || "No active application"}</p>
                          <p className="mt-1 truncate text-xs text-[#A8B3C7]" title={selectedAsset.activeWindow}>{selectedAsset.activeWindow || "No active window"}</p>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-[#38BDF8]/25 bg-[#38BDF8]/8 p-3">
                        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7DD3FC]">Active Path</p>
                        <p className="mt-2 truncate text-sm font-semibold text-white" title={resolveActivePath(selectedAsset)}>{resolveActivePath(selectedAsset)}</p>
                      </div>
                      <div className="rounded-xl border border-amber-300/25 bg-amber-300/8 p-3">
                        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-amber-100">Last Active</p>
                        <p className="mt-2 truncate text-sm font-semibold text-white">{formatTelemetryTimestamp(selectedAsset.lastActiveTime)}</p>
                      </div>
                    </div>
                    <div className="rounded-xl border border-[#2B3752] bg-[#0F1728]/80 p-3">
                      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8EA0B8]">Live Status</p>
                      <div className="mt-2">
                        {selectedAsset.status === "Online"
                          ? <span className="inline-flex items-center gap-2 text-sm font-bold text-emerald-300"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-300" />Heartbeat active</span>
                          : <span className="inline-flex items-center gap-2 text-sm font-bold text-red-300"><span className="h-2 w-2 rounded-full bg-red-300" />Heartbeat stopped</span>}
                      </div>
                    </div>
                  </div>
                  <div className="max-h-80 overflow-y-auto pr-2">
                    {liveApplicationTimeline.length ? (
                      <div className="space-y-3">
                        {liveApplicationTimeline.map((entry, index) => {
                          const appName = appTimelineTitle(entry);
                          const isCurrent = index === 0;
                          return (
                            <div
                              key={`${entry.timestamp}-${index}`}
                              className={`grid grid-cols-[38px_78px_1fr] gap-3 rounded-xl border p-3 ${timelineAccentFor(appName)} ${isCurrent ? "ring-1 ring-emerald-300/35" : ""}`}
                            >
                              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-[#0B1220]/80">
                                {timelineIconFor(appName)}
                              </div>
                              <div className="pt-0.5">
                                <div className="text-[11px] font-black text-white">{timeOnlyLabel(entry.timestamp)}</div>
                                {isCurrent ? <div className="mt-1 text-[9px] font-bold uppercase tracking-[0.16em] text-emerald-300">Current</div> : null}
                              </div>
                              <div className="min-w-0">
                                <div className="flex min-w-0 flex-wrap items-center gap-2">
                                  <p className="truncate text-sm font-bold text-white">{appName}</p>
                                  {isCurrent ? <span className="rounded-full border border-emerald-300/35 bg-emerald-300/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-200">Live</span> : null}
                                </div>
                                <p className="mt-1 truncate text-[11px] text-[#A8B3C7]" title={appTimelineDetail(entry)}>{appTimelineDetail(entry)}</p>
                                {entry.process_path ? <p className="mt-1 truncate text-[10px] text-[#64748B]" title={entry.process_path}>{entry.process_path}</p> : null}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[#2B3752] bg-[#0F1728]/70 p-4 text-sm text-[#8EA0B8]">No active application events stored in Neon yet.</div>
                    )}
                  </div>
                </div>
              </section>

              <ApplicationUsageAnalytics detail={selectedAssetDetail} selectedPeriod={selectedUsagePeriod} onPeriodChange={setSelectedUsagePeriod} />

              <ProductivityInsights detail={selectedAssetDetail} selectedPeriod={selectedUsagePeriod} />

              <DetailSection title="System Metrics" icon={<Gauge className="w-5 h-5 text-sky-300" />}>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 select-none">
                  {[
                    { label: "CPU Usage", value: selectedAsset.status === "Offline" ? "0%" : formatPercent(selectedAsset.cpuUsage), icon: <Cpu className="w-4 h-4 text-sky-300" />, color: "text-sky-300" },
                    { label: "RAM Usage", value: selectedAsset.status === "Offline" ? "0%" : formatPercent(selectedAsset.ramUsage), icon: <MemoryStick className="w-4 h-4 text-emerald-300" />, color: "text-emerald-300" },
                    { label: "Memory Used", value: formatGb(selectedAsset.memoryUsedGb), icon: <HardDrive className="w-4 h-4 text-amber-300" />, color: "text-amber-300" },
                    { label: "Memory Available", value: formatGb(selectedAsset.memoryAvailableGb), icon: <Database className="w-4 h-4 text-blue-300" />, color: "text-blue-300" },
                  ].map((metric) => (
                    <div key={metric.label} className="rounded-xl border border-[#2B3752] bg-[#0F1728] p-4 shadow-[0_12px_30px_rgba(0,0,0,0.18)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#1B2338]">
                      <div className="flex items-center justify-between text-[#8EA0B8] text-[10px] uppercase tracking-[0.18em] font-semibold">
                        {metric.label}
                        {metric.icon}
                      </div>
                      <div className={`mt-3 text-2xl font-bold ${metric.color}`}>{metric.value}</div>
                    </div>
                  ))}
                </div>
              </DetailSection>

              <DetailSection title="Security & Alerts" icon={<ShieldAlert className="w-5 h-5 text-red-300" />}>
                {(selectedAssetDetail?.alerts || []).length ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {(selectedAssetDetail?.alerts || []).slice(0, 12).map((alert, index) => (
                      <div key={`${alert.timestamp}-${index}`} className="rounded-xl border border-[#2B3752] bg-[#0F1728] p-3 transition-all hover:bg-[#1B2338]">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-semibold text-[#d6e3ec]">{alert.alert_type || "Security Warning"}</span>
                          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${severityStyles[String(alert.severity || "LOW").toUpperCase()] || severityStyles.LOW}`}>{alert.severity || "LOW"}</span>
                        </div>
                        <p className="mt-1 text-[11px] text-[#9fb0bd]">{formatTelemetryTimestamp(alert.timestamp)}</p>
                        <p className="mt-2 text-[12px] text-[#d6e3ec]">{typeof alert.details === "object" ? (alert.details.description || alert.details.message || JSON.stringify(alert.details)) : alert.details}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                    <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/10 p-5">
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="h-7 w-7 text-emerald-300" />
                        <div>
                          <p className="text-lg font-bold text-white">System Secure</p>
                          <p className="text-sm text-emerald-200/80">No critical alerts detected</p>
                        </div>
                      </div>
                    </div>
                    <DetailField label="Last Security Scan" value={selectedAsset.lastSeenHuman || "2 minutes ago"} accent />
                    <DetailField label="Security Score" value="98%" accent />
                    <DetailField label="Risk Level" value={<span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-300">LOW</span>} />
                    <DetailField label="Alert State" value="No active critical incidents" />
                    <DetailField label="Monitoring Coverage" value="Endpoint, login, hardware, active app" />
                  </div>
                )}
              </DetailSection>

              <DetailSection title="Charts" icon={<BarChart3 className="w-5 h-5 text-sky-300" />}>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <MiniLineChart title="CPU Usage History" icon={<Cpu className="w-4 h-4 text-sky-300" />} data={selectedAssetDetail?.charts.cpu_usage_history || []} color="#38bdf8" />
                  <MiniLineChart title="RAM Usage History" icon={<MemoryStick className="w-4 h-4 text-emerald-300" />} data={selectedAssetDetail?.charts.ram_usage_history || []} color="#34d399" />
                  <MiniBarChart title="Login Frequency" icon={<User className="w-4 h-4 text-blue-300" />} data={selectedAssetDetail?.charts.login_frequency || []} colorClass="bg-blue-400" />
                  <div className="lg:col-span-2">
                    <MiniBarChart title="Alert Trend" icon={<AlertCircle className="w-4 h-4 text-red-300" />} data={selectedAssetDetail?.charts.alert_trend || []} colorClass="bg-red-400" />
                  </div>
                </div>
              </DetailSection>

              <DetailSection title="Device Timeline" icon={<Clock className="w-5 h-5 text-blue-300" />}>
                <div className="flex flex-col gap-2.5 max-h-96 overflow-y-auto pr-1">
                  {(selectedAssetDetail?.timeline || selectedAsset.timeline || []).length ? (
                    (selectedAssetDetail?.timeline || selectedAsset.timeline || []).slice(0, 80).map((event, idx) => {
                      const eventType = String(event.event_type || event.type || "Event");
                      const severity = String(event.severity || "LOW").toUpperCase();
                      const Icon = eventType.includes("Login") ? LogIn : eventType.includes("Application") ? Activity : eventType.includes("Offline") ? WifiOff : eventType.includes("Alert") || eventType.includes("Change") ? AlertTriangle : Info;
                      return (
                        <div key={`${eventType}-${event.timestamp}-${idx}`} className="grid grid-cols-[36px_120px_1fr] gap-3 bg-[#0b1218] p-3 border border-white/10 rounded-lg text-[12px] leading-relaxed">
                          <div className="h-8 w-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center"><Icon className="w-4 h-4 text-sky-300" /></div>
                          <div className="text-[#9fb0bd]">{formatTelemetryTimestamp(event.timestamp)}</div>
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-[#d6e3ec] font-semibold">{eventType}</span>
                              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${severityStyles[severity] || severityStyles.LOW}`}>{severity}</span>
                            </div>
                            <div className="text-[#a9bac7] break-words mt-1">{event.description || event.detail}</div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="rounded-xl border border-dashed border-[#2B3752] bg-[#0F1728]/70 p-4 text-sm text-[#8EA0B8]">No device timeline events stored in Neon yet.</div>
                  )}
                </div>
              </DetailSection>

              {/* AI Forensic results window output */}
              {(auditLoading || auditReport) && (
                <div className="bg-[#0D1117] border border-white/5 p-4 rounded-xl flex flex-col gap-3 font-sans shadow-inner selection:bg-[#00d1ff]/20">
                  
                  {/* Headline item */}
                  <div className="flex items-center justify-between border-b border-[#3c494e]/30 pb-2 mb-1">
                    <span className="text-xs uppercase font-black text-[#00d1ff] tracking-widest flex items-center gap-1.5 font-mono">
                      <Sparkles className="w-3.5 h-3.5" />
                      Sentinel Forensic AI Analyst
                    </span>
                    {auditRiskScore !== null && (
                      <span className={`text-[10px] font-mono font-extrabold px-2.5 py-0.5 rounded-full ${auditRiskScore > 70 ? "bg-red-950/40 text-red-400 border border-red-500/30" : auditRiskScore > 30 ? "bg-amber-950/40 text-amber-400 border border-amber-500/30" : "bg-emerald-992/30 text-emerald-400 border border-emerald-500/30"}`}>
                        Risk Index: {auditRiskScore}/100
                      </span>
                    )}
                  </div>

                  {/* Loading Scanline Sequencer */}
                  {auditLoading ? (
                    <div className="flex flex-col gap-3 py-6 items-center justify-center text-center select-none font-mono text-[11px] text-[#00d1ff]">
                      <RefreshCw className="w-8 h-8 animate-spin text-[#00d1ff]" />
                      <div className="flex flex-col gap-1 mt-2">
                        <span className="animate-pulse">Handshaking cryptographic node signatures...</span>
                        <span className="text-[#bbc9cf] text-[9px] font-light">Querying secure full-stack forensic intelligence model [gemini-3.5-flash]</span>
                      </div>
                    </div>
                  ) : (
                    <div id="ai-forensic-report-markdown" className="text-xs text-[#bbc9cf] leading-relaxed select-text space-y-3 prose prose-invert font-light max-w-none">
                      
                      {/* Formatted markdown text box */}
                      <div className="whitespace-pre-line font-mono text-[11px] text-[#dae3ee]">
                        {auditReport}
                      </div>

                    </div>
                  )}

                </div>
              )}

              {/* Asset Historical logs list panel */}
              <div className="flex flex-col gap-2.5 border-t border-[#3c494e]/20 pt-4 selection:bg-[#00d1ff]/10">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#bbc9cf] select-none flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-[#859399]" />
                  Internal Endpoint Changelog
                </h3>
                <div className="flex flex-col gap-2 h-44 overflow-y-auto pr-1">
                  {selectedAsset.history.map((logStr: string, lIdx: number) => (
                    <div key={lIdx} className="bg-[#0d1117] p-2.5 border border-white/5 rounded-lg text-[10.5px] font-mono leading-relaxed text-[#bbc9cf] hover:text-[#dae3ee]">
                      <span className="text-[#00d1ff] font-bold mr-1.5 select-none font-mono">▸</span>
                      {logStr}
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>
        )}

        {isTimelineSelectorOpen && selectedAsset && (
          <div className="fixed inset-0 z-[68] flex items-center justify-center bg-[#020617]/62 px-4 py-6 backdrop-blur-sm">
            <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-amber-300/30 bg-[linear-gradient(145deg,#101827_0%,#141B2D_64%,#0B1220_100%)] p-5 shadow-[0_24px_80px_rgba(2,8,23,0.66),0_0_34px_rgba(245,158,11,0.12)]">
              <div className="mb-5 flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-amber-200">Activity History Search</p>
                  <h3 className="mt-1 text-lg font-bold text-white">Select Time Range</h3>
                </div>
                <button
                  onClick={() => setIsTimelineSelectorOpen(false)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] transition-colors hover:border-amber-300/45 hover:text-white"
                  aria-label="Cancel activity history search"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {(Object.keys(timelineHistoryLabels) as TimelineHistoryPreset[]).map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setPendingTimelineHistoryPreset(preset)}
                    className={`inline-flex h-10 items-center justify-center rounded-lg border px-3 text-xs font-bold transition-colors ${
                      pendingTimelineHistoryPreset === preset
                        ? "border-amber-200/70 bg-amber-300/18 text-amber-50"
                        : "border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] hover:border-amber-300/45 hover:text-white"
                    }`}
                  >
                    {timelineHistoryLabels[preset]}
                  </button>
                ))}
              </div>
              {pendingTimelineHistoryPreset === "custom" ? (
                <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div className="grid gap-3">
                    <label className="grid gap-2 text-xs font-bold uppercase tracking-[0.16em] text-[#8EA0B8]">
                      Start Date
                      <input
                        type="date"
                        value={datePartFromDateTimeValue(pendingCustomHistoryStart)}
                        onChange={(event) => setPendingCustomHistoryStart((value) => withDatePart(value, event.target.value))}
                        className="h-10 rounded-lg border border-[#2B3752] bg-[#0F1728] px-3 text-sm font-semibold normal-case tracking-normal text-white outline-none transition-colors focus:border-amber-300/60"
                      />
                    </label>
                    <ClockTimePicker
                      label="Start Time"
                      value={timePartFromDateTimeValue(pendingCustomHistoryStart)}
                      onChange={(value) => setPendingCustomHistoryStart((current) => withTimePart(current, value))}
                    />
                  </div>
                  <div className="grid gap-3">
                    <label className="grid gap-2 text-xs font-bold uppercase tracking-[0.16em] text-[#8EA0B8]">
                      End Date
                      <input
                        type="date"
                        value={datePartFromDateTimeValue(pendingCustomHistoryEnd)}
                        onChange={(event) => setPendingCustomHistoryEnd((value) => withDatePart(value, event.target.value))}
                        className="h-10 rounded-lg border border-[#2B3752] bg-[#0F1728] px-3 text-sm font-semibold normal-case tracking-normal text-white outline-none transition-colors focus:border-amber-300/60"
                      />
                    </label>
                    <ClockTimePicker
                      label="End Time"
                      value={timePartFromDateTimeValue(pendingCustomHistoryEnd)}
                      onChange={(value) => setPendingCustomHistoryEnd((current) => withTimePart(current, value))}
                    />
                  </div>
                </div>
              ) : null}
              <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <button
                  onClick={() => setIsTimelineSelectorOpen(false)}
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-[#2B3752] bg-[#0F1728] px-4 text-xs font-bold text-[#CBD5E1] transition-colors hover:bg-[#1B2338]"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setTimelineHistoryPreset(pendingTimelineHistoryPreset);
                    setCustomHistoryStart(pendingCustomHistoryStart);
                    setCustomHistoryEnd(pendingCustomHistoryEnd);
                    setIsTimelineSelectorOpen(false);
                    setIsTimelineHistoryOpen(true);
                  }}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-amber-300/45 bg-amber-300/14 px-4 text-xs font-bold text-amber-100 transition-colors hover:border-amber-200/70 hover:bg-amber-300/22"
                >
                  <Clock className="h-4 w-4" />
                  View Activity
                </button>
              </div>
            </div>
          </div>
        )}

        {isTimelineHistoryOpen && selectedAsset && (
          <div className="fixed inset-0 z-[70] flex items-center justify-center bg-[#020617]/78 px-4 py-6 backdrop-blur-sm">
            <div className="flex max-h-[86vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-[#38BDF8]/35 bg-[#101827] shadow-[0_28px_110px_rgba(2,8,23,0.72),0_0_42px_rgba(56,189,248,0.16)]">
              <div className="flex items-start justify-between gap-4 border-b border-[#2B3752] bg-[#141B2D] px-5 py-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#7DD3FC]">Activity History</p>
                  <h3 className="mt-1 text-xl font-bold text-white">
                    {timelineHistoryPreset === "custom" ? selectedTimelineHistoryBounds.label : timelineHistoryLabels[timelineHistoryPreset]}
                  </h3>
                </div>
                <button
                  onClick={() => setIsTimelineHistoryOpen(false)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] transition-colors hover:border-[#38BDF8]/45 hover:text-white"
                  aria-label="Close activity history"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="overflow-y-auto p-5">
                {filteredTimelineIntervals.length ? (
                  <div className="relative space-y-0 pl-5 before:absolute before:left-4 before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-[#2B3752]">
                    {filteredTimelineIntervals.map((entry, index) => {
                      const appName = appTimelineTitle(entry);
                      return (
                        <div key={`filtered-${entry.timestamp}-${index}`} className="relative pb-4 pl-6 last:pb-0">
                          <div className="absolute left-[-0.15rem] top-4 flex h-5 w-5 items-center justify-center rounded-full border border-[#7DD3FC]/45 bg-[#0B1220] shadow-[0_0_18px_rgba(56,189,248,0.18)]">
                            <span className="h-2 w-2 rounded-full bg-[#7DD3FC]" />
                          </div>
                          <div className={`rounded-xl border p-4 ${timelineAccentFor(appName)}`}>
                            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                              <div className="inline-flex items-center gap-2 text-xs font-bold text-white">
                                <Clock className="h-3.5 w-3.5 text-[#7DD3FC]" />
                                {timeOnlyLabel(entry.timestamp)} - {entry.endTimestamp ? timeOnlyLabel(entry.endTimestamp) : formatTelemetryTimestamp(new Date(selectedTimelineHistoryBounds.endMs).toISOString())}
                              </div>
                              {entry.durationSeconds ? (
                                <span className="rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#CBD5E1]">
                                  {formatUsageDuration(entry.durationSeconds)}
                                </span>
                              ) : null}
                            </div>
                            <div className="grid grid-cols-[40px_1fr] gap-3">
                              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-[#0B1220]/80">
                                {timelineIconFor(appName)}
                              </div>
                              <div className="min-w-0">
                                <p className="truncate text-base font-bold text-white">{appName}</p>
                                <p className="mt-1 truncate text-sm text-[#CBD5E1]" title={entry.window_title || ""}>{entry.window_title || "Unknown window title"}</p>
                                <p className="mt-1 truncate text-[11px] text-[#8EA0B8]" title={entry.process_path || ""}>{entry.process_path || "No process path stored"}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-[#2B3752] bg-[#0F1728]/70 p-5 text-sm text-[#8EA0B8]">
                    No application events found for {selectedTimelineHistoryBounds.label}.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {isSupportCenterOpen && (
          <div className="fixed inset-0 z-[80] flex items-center justify-center bg-[#020617]/78 px-4 py-6 backdrop-blur-sm">
            <div className="w-full max-w-2xl rounded-2xl border border-[#38BDF8]/30 bg-[linear-gradient(145deg,#101827_0%,#141B2D_58%,#0B1220_100%)] p-5 shadow-[0_28px_100px_rgba(2,8,23,0.7),0_0_42px_rgba(56,189,248,0.12)]">
              <div className="mb-5 flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#7DD3FC]">Support Center</p>
                  <h3 className="mt-1 text-2xl font-bold text-white">Asset Sentinel Support</h3>
                </div>
                <button
                  onClick={() => setIsSupportCenterOpen(false)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] transition-colors hover:border-[#38BDF8]/45 hover:text-white"
                  aria-label="Close support center"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <button
                  onClick={() => {
                    setIsSupportCenterOpen(false);
                    setIsRaiseTicketOpen(true);
                  }}
                  className="rounded-xl border border-emerald-300/30 bg-emerald-300/10 p-5 text-left shadow-[0_14px_34px_rgba(52,211,153,0.08)] transition-colors hover:border-emerald-200/55 hover:bg-emerald-300/15"
                >
                  <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-emerald-300/30 bg-[#0B1220]/70">
                    <HelpCircle className="h-5 w-5 text-emerald-200" />
                  </div>
                  <p className="text-lg font-bold text-white">Raise Ticket</p>
                  <p className="mt-1 text-sm text-[#A8B3C7]">Create a new technical support request</p>
                </button>
                <button
                  onClick={() => {
                    setIsSupportCenterOpen(false);
                    setIsEmailSupportOpen(true);
                  }}
                  className="rounded-xl border border-amber-300/30 bg-amber-300/10 p-5 text-left shadow-[0_14px_34px_rgba(245,158,11,0.08)] transition-colors hover:border-amber-200/55 hover:bg-amber-300/15"
                >
                  <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-amber-300/30 bg-[#0B1220]/70">
                    <Info className="h-5 w-5 text-amber-100" />
                  </div>
                  <p className="text-lg font-bold text-white">Email Support</p>
                  <p className="mt-1 text-sm text-[#A8B3C7]">Contact support team directly</p>
                </button>
              </div>
            </div>
          </div>
        )}

        {isRaiseTicketOpen && (
          <div className="fixed inset-0 z-[81] flex items-center justify-center bg-[#020617]/78 px-4 py-6 backdrop-blur-sm">
            <div className="w-full max-w-xl rounded-2xl border border-emerald-300/30 bg-[#101827] p-5 shadow-[0_28px_100px_rgba(2,8,23,0.7)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-200">Raise Support Ticket</p>
                  <h3 className="mt-1 text-2xl font-bold text-white">Create Technical Ticket</h3>
                </div>
                <button onClick={() => setIsRaiseTicketOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] hover:text-white" aria-label="Close raise ticket">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-5 grid gap-3">
                {supportMessage && <div className="rounded-lg border border-emerald-300/30 bg-emerald-300/10 px-3 py-2 text-sm text-emerald-100">{supportMessage}</div>}
                {supportError && <div className="rounded-lg border border-red-300/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">{supportError}</div>}
                <input
                  value={ticketForm.title}
                  onChange={(event) => setTicketForm((form) => ({ ...form, title: event.target.value }))}
                  placeholder="Ticket title"
                  className="rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-emerald-300/60"
                />
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <select value={ticketForm.category} onChange={(event) => setTicketForm((form) => ({ ...form, category: event.target.value }))} className="rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-emerald-300/60">
                    {SUPPORT_CATEGORIES.map((category) => <option key={category}>{category}</option>)}
                  </select>
                  <select value={ticketForm.priority} onChange={(event) => setTicketForm((form) => ({ ...form, priority: event.target.value }))} className="rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-emerald-300/60">
                    {SUPPORT_PRIORITIES.map((priority) => <option key={priority}>{priority}</option>)}
                  </select>
                </div>
                <input
                  value={ticketForm.relatedDevice}
                  onChange={(event) => setTicketForm((form) => ({ ...form, relatedDevice: event.target.value }))}
                  placeholder={selectedAsset?.hostname ? `Related device: ${selectedAsset.hostname}` : "Related device or hostname"}
                  className="rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-emerald-300/60"
                />
                <textarea
                  value={ticketForm.description}
                  onChange={(event) => setTicketForm((form) => ({ ...form, description: event.target.value }))}
                  placeholder="Describe the issue, affected device, and expected behavior"
                  rows={5}
                  className="resize-none rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-emerald-300/60"
                />
                <button
                  onClick={submitSupportTicket}
                  disabled={supportBusy}
                  className="rounded-lg bg-emerald-300 px-4 py-3 text-sm font-black uppercase tracking-widest text-[#052016] disabled:opacity-60"
                >
                  {supportBusy ? "Creating..." : "Create Ticket"}
                </button>
              </div>
            </div>
          </div>
        )}

        {isEmailSupportOpen && (
          <div className="fixed inset-0 z-[81] flex items-center justify-center bg-[#020617]/78 px-4 py-6 backdrop-blur-sm">
            <div className="w-full max-w-xl rounded-2xl border border-amber-300/30 bg-[#101827] p-5 shadow-[0_28px_100px_rgba(2,8,23,0.7)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-amber-200">Email Support</p>
                  <h3 className="mt-1 text-2xl font-bold text-white">Contact Support Team</h3>
                </div>
                <button onClick={() => setIsEmailSupportOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#2B3752] bg-[#0F1728] text-[#A8B3C7] hover:text-white" aria-label="Close email support">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-5 grid gap-3">
                {supportMessage && <div className="rounded-lg border border-emerald-300/30 bg-emerald-300/10 px-3 py-2 text-sm text-emerald-100">{supportMessage}</div>}
                {supportError && <div className="rounded-lg border border-red-300/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">{supportError}</div>}
                <input
                  value={emailSupportForm.subject}
                  onChange={(event) => setEmailSupportForm((form) => ({ ...form, subject: event.target.value }))}
                  placeholder="Subject"
                  className="rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-amber-300/60"
                />
                <select value={emailSupportForm.priority} onChange={(event) => setEmailSupportForm((form) => ({ ...form, priority: event.target.value }))} className="rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-amber-300/60">
                  {SUPPORT_PRIORITIES.map((priority) => <option key={priority}>{priority}</option>)}
                </select>
                <textarea
                  value={emailSupportForm.message}
                  onChange={(event) => setEmailSupportForm((form) => ({ ...form, message: event.target.value }))}
                  placeholder="Write your support message"
                  rows={6}
                  className="resize-none rounded-lg border border-[#2B3752] bg-[#0B1220] px-3 py-3 text-sm text-white outline-none focus:border-amber-300/60"
                />
                <button
                  onClick={submitSupportEmail}
                  disabled={supportBusy}
                  className="rounded-lg bg-amber-300 px-4 py-3 text-sm font-black uppercase tracking-widest text-[#2a1700] disabled:opacity-60"
                >
                  {supportBusy ? "Sending..." : "Send Email"}
                </button>
              </div>
            </div>
          </div>
        )}

      </main>

    </div>
  );
}

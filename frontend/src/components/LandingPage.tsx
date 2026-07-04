import React, { useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback } from "react";
import { 
  Shield, 
  Cpu, 
  HardDrive, 
  Layers, 
  ShieldAlert, 
  Fingerprint, 
  Globe, 
  BellRing, 
  Sliders, 
  ArrowRight, 
  AlertTriangle, 
  LogIn,
  Activity,
  CheckCircle2,
  Server,
  X
} from "lucide-react";
import { CORE_TELEMETRY_PROTOCOLS } from "../data";
import { apiFetch, authFetch } from "../lib/api";
import ShaderBackground from "./ShaderBackground";
import { SentinelLogo } from "./SentinelLogo";

interface LandingPageProps {
  onNavigate: (view: "landing" | "login" | "admin-signup" | "dashboard" | "demo") => void;
}

interface RollingKpiValueProps {
  value: string;
  className: string;
  duration: number;
}

const GRID_CELL_BASE_CLASS = "w-full aspect-square rounded-sm border transition-all duration-300";
const HEX_CHARS = "0123456789ABCDEF";
const HERO_TYPEWRITER_LINES = [
  "Monitor Every Asset.",
  "Detect Every Change.",
  "Secure Every Endpoint.",
  "Monitor. Detect. Protect.",
  "Enterprise IT Asset Monitoring Reimagined."
];

const getGridCellColorClass = (state: string) => {
  if (state === "nominal") return "bg-emerald-500/10 border-emerald-400/20 shadow-[0_0_2px_rgba(16,185,129,0.1)]";
  if (state === "warning") return "bg-amber-500/30 border-amber-400/40 shadow-[0_0_3px_rgba(245,158,11,0.2)]";
  if (state === "alert") return "bg-red-500 border-red-400 shadow-[0_0_8px_#ef4444] animate-ping";
  return "bg-[#2d363e]/40 border-white/5";
};

const getGridCellClassName = (state: string) => `${GRID_CELL_BASE_CLASS} ${getGridCellColorClass(state)}`;

const LandingScrollPerformanceController = React.memo(function LandingScrollPerformanceController() {
  useEffect(() => {
    const landingScreen = document.getElementById("landing-screen");
    if (!landingScreen) return;

    let scrollEndTimer = 0;
    const perfRegions = Array.from(document.querySelectorAll<HTMLElement>(".landing-perf-region"));
    const visibilityObserver = "IntersectionObserver" in window
      ? new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            (entry.target as HTMLElement).dataset.visible = entry.isIntersecting ? "true" : "false";
          });
        }, { rootMargin: "360px 0px" })
      : null;

    perfRegions.forEach((region) => {
      region.dataset.visible = "true";
      visibilityObserver?.observe(region);
    });

    const handleScroll = () => {
      landingScreen.dataset.scrolling = "true";
      window.clearTimeout(scrollEndTimer);
      scrollEndTimer = window.setTimeout(() => {
        delete landingScreen.dataset.scrolling;
      }, 140);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.clearTimeout(scrollEndTimer);
      window.removeEventListener("scroll", handleScroll);
      visibilityObserver?.disconnect();
      perfRegions.forEach((region) => {
        delete region.dataset.visible;
      });
      delete landingScreen.dataset.scrolling;
    };
  }, []);

  return null;
});

const RollingKpiValue = React.memo(function RollingKpiValue({ value, className, duration }: RollingKpiValueProps) {
  const previousDigitsRef = useRef<number[]>([]);
  const animationFrameRef = useRef(0);
  const settleTimeoutRef = useRef(0);
  const [digitOffsets, setDigitOffsets] = useState<number[]>(() => {
    let digitIndex = 0;
    return value.split("").reduce<number[]>((offsets, char) => {
      if (/\d/.test(char)) {
        offsets[digitIndex] = 0;
        digitIndex += 1;
      }
      return offsets;
    }, []);
  });
  const [isRolling, setIsRolling] = useState(false);
  const valueChars = useMemo(() => value.split(""), [value]);
  const targetDigits = useMemo(() => valueChars.filter((char) => /\d/.test(char)).map(Number), [valueChars]);
  const stripDigits = useMemo(() => Array.from({ length: 100 }, (_, index) => index % 10), []);

  useLayoutEffect(() => {
    cancelAnimationFrame(animationFrameRef.current);
    window.clearTimeout(settleTimeoutRef.current);
    setIsRolling(false);
    animationFrameRef.current = requestAnimationFrame(() => {
      const previousDigits = previousDigitsRef.current.length === targetDigits.length
        ? previousDigitsRef.current
        : new Array(targetDigits.length).fill(0);
      setDigitOffsets((currentOffsets) => targetDigits.map((digit, index) => {
        const previousDigit = previousDigits[index] ?? 0;
        const previousOffset = currentOffsets[index] ?? previousDigit;
        const delta = (digit - (previousOffset % 10) + 10) % 10;
        return previousOffset + delta + (delta === 0 && previousDigit !== digit ? 10 : 0);
      }));
      previousDigitsRef.current = targetDigits;
      setIsRolling(true);
      const animationDuration = Math.min(3000, Math.max(2000, duration));
      settleTimeoutRef.current = window.setTimeout(() => {
        setIsRolling(false);
        setDigitOffsets((currentOffsets) => currentOffsets.map((offset) => (offset % 10) + 20));
      }, animationDuration + targetDigits.length * 28 + 80);
    });

    return () => {
      cancelAnimationFrame(animationFrameRef.current);
      window.clearTimeout(settleTimeoutRef.current);
    };
  }, [duration, targetDigits]);

  let digitRefIndex = 0;
  const rollDuration = Math.min(3000, Math.max(2000, duration));

  return (
    <span
      className={className}
      aria-label={value}
      style={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}
    >
      {valueChars.map((char, charIndex) => {
        if (!/\d/.test(char)) {
          return (
            <span key={`${char}-${charIndex}`} aria-hidden="true">
              {char}
            </span>
          );
        }

        const currentDigitRefIndex = digitRefIndex;
        const offset = digitOffsets[currentDigitRefIndex] ?? Number(char);
        digitRefIndex += 1;

        return (
          <span
            key={`${char}-${charIndex}`}
            aria-hidden="true"
            className="odometer-digit"
            style={{
              display: "inline-block",
              minWidth: "0.62em",
              height: "1em",
              lineHeight: "1",
              textAlign: "center",
              verticalAlign: "-0.02em",
              overflow: "hidden",
            }}
          >
            <span
              className="odometer-digit-strip"
              style={{
                display: "flex",
                flexDirection: "column",
                transform: `translate3d(0, -${offset}em, 0)`,
                transition: isRolling ? `transform ${rollDuration + currentDigitRefIndex * 28}ms cubic-bezier(0.18, 0.9, 0.22, 1)` : "none",
                willChange: isRolling ? "transform" : "auto",
              }}
            >
              {stripDigits.map((digit, index) => (
                <span key={`${digit}-${index}`} className="odometer-strip-digit" style={{ height: "1em", lineHeight: "1" }}>{digit}</span>
              ))}
            </span>
          </span>
        );
      })}
    </span>
  );
});

const TypewriterHeroText = React.memo(function TypewriterHeroText() {
  const [lineIndex, setLineIndex] = useState(0);
  const [visibleText, setVisibleText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const currentLine = HERO_TYPEWRITER_LINES[lineIndex];
    const isComplete = visibleText === currentLine;
    const isEmpty = visibleText.length === 0;
    const delay = isComplete && !isDeleting ? 1500 : isDeleting ? 34 : 56;

    const timer = window.setTimeout(() => {
      if (!isDeleting && isComplete) {
        setIsDeleting(true);
        return;
      }

      if (isDeleting && isEmpty) {
        setIsDeleting(false);
        setLineIndex((current) => (current + 1) % HERO_TYPEWRITER_LINES.length);
        return;
      }

      setVisibleText((current) => {
        if (isDeleting) return current.slice(0, -1);
        return currentLine.slice(0, current.length + 1);
      });
    }, delay);

    return () => window.clearTimeout(timer);
  }, [isDeleting, lineIndex, visibleText]);

  return (
    <h1 className="hero-typewriter min-h-[7.2rem] md:min-h-[8.4rem] lg:min-h-[10rem] text-3xl md:text-4xl lg:text-5xl font-black tracking-tight leading-[1.08] text-[#dae3ee]">
      <span className="block text-[#dae3ee]">Asset Sentinel Enterprise</span>
      <span className="mt-2 block text-[#00d1ff] text-transparent bg-clip-text bg-gradient-to-r from-[#00d1ff] via-[#a4e6ff] to-emerald-300 drop-shadow-[0_0_12px_rgba(0,209,255,0.28)]">
        {visibleText}
        <span className="typewriter-cursor" aria-hidden="true">|</span>
      </span>
    </h1>
  );
});

const HeroTelemetryBackdrop = React.memo(function HeroTelemetryBackdrop() {
  return (
    <div className="hero-telemetry-layer" aria-hidden="true">
      <div className="hero-gradient-field"></div>
      <div className="hero-glowing-grid"></div>
      <div className="hero-radar-sweep"></div>
      <svg className="hero-network-lines" viewBox="0 0 900 520" preserveAspectRatio="none">
        <path className="network-path network-path-a" d="M40 390 C180 270 245 330 365 206 S612 110 845 220" />
        <path className="network-path network-path-b" d="M78 148 C220 90 322 178 448 160 S652 245 832 118" />
        <path className="network-path network-path-c" d="M112 462 C260 394 346 456 496 342 S706 296 850 386" />
      </svg>
      {[...Array(12)].map((_, index) => (
        <span key={index} className={`hero-particle hero-particle-${index + 1}`}></span>
      ))}
      <span className="hero-node hero-node-a"><Shield className="w-3 h-3" /></span>
      <span className="hero-node hero-node-b"><Server className="w-3 h-3" /></span>
      <span className="hero-node hero-node-c"><Activity className="w-3 h-3" /></span>
    </div>
  );
});

const LiveDashboardPreview = React.memo(function LiveDashboardPreview() {
  const [tick, setTick] = useState(0);
  const [activeApps, setActiveApps] = useState<string[]>([]);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((current) => current + 1), 3000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;
    const loadActiveApps = async () => {
      try {
        const response = await apiFetch("/api/active-applications");
        if (!response.ok) return;
        const payload = await response.json();
        if (!active || !Array.isArray(payload)) return;
        const names = payload
          .map((item) => item.application_name || item.executable_name)
          .filter(Boolean)
          .slice(0, 4);
        setActiveApps(names);
      } catch {
        // Public landing page can render the integration-ready placeholder.
      }
    };
    const idleId = window.setTimeout(loadActiveApps, 900);
    return () => {
      active = false;
      window.clearTimeout(idleId);
    };
  }, []);

  const onlineDevices = 1240 + (tick % 9);
  const cpu = 42 + ((tick * 7) % 31);
  const ram = 56 + ((tick * 5) % 25);
  const alertLabels = ["RAM delta verified", "Motherboard hash mismatch", "Login anomaly cleared", "App timeline updated"];
  const timeline = ["Chrome.exe", "Teams.exe", "PowerShell.exe", "pgAdmin.exe"];
  const displayedApps = activeApps.length ? activeApps : ["Google Chrome", "VS Code", "Microsoft Outlook", "Explorer"];

  return (
    <div className="hero-dashboard-preview glass-panel rounded-xl border border-[#00d1ff]/30 bg-[#0d131b]/92 p-3 md:p-4 shadow-[0_0_45px_rgba(0,209,255,0.16)] overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20 pointer-events-none"></div>
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#00d1ff] to-transparent"></div>
      <div className="relative flex items-center justify-between gap-3 mb-3">
        <div>
          <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-[#00d1ff]">Live Command Preview</span>
          <h3 className="text-sm font-black text-[#dae3ee] uppercase mt-1">Enterprise Fleet Telemetry</h3>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1">
          <span className="w-2 h-2 rounded-full bg-emerald-300 heartbeat-dot"></span>
          <span className="font-mono text-[9px] text-emerald-300 uppercase font-bold">Live</span>
        </div>
      </div>

      <div className="relative grid grid-cols-3 gap-3 mb-3">
        <MetricTile label="Online" value={onlineDevices.toLocaleString()} tone="cyan" />
        <MetricTile label="Alerts" value={String(7 + (tick % 3))} tone="amber" />
        <MetricTile label="Logins" value={String(318 + (tick % 13))} tone="emerald" />
      </div>

      <div className="relative grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-white/10 bg-[#070b10]/85 p-3">
          <div className="flex items-center justify-between mb-3">
            <span className="font-mono text-[9px] text-[#bbc9cf] uppercase tracking-widest">Current Active Application</span>
            <span className="text-[9px] text-emerald-300 font-mono">{activeApps.length ? "LIVE" : "READY"}</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {displayedApps.map((appName, index) => (
              <div
                key={`${appName}-${index}`}
                className={`flex items-center justify-between rounded-md border px-2.5 py-1.5 text-[10px] font-mono transition-all duration-500 ${index === tick % displayedApps.length ? "border-[#00d1ff]/35 bg-[#00d1ff]/10 text-[#dae3ee]" : "border-white/10 bg-white/[0.03] text-[#bbc9cf]"}`}
              >
                <span className="truncate">{appName}</span>
                <span className={index === tick % displayedApps.length ? "text-emerald-300" : "text-[#65737c]"}>
                  {index === tick % displayedApps.length ? "active" : "seen"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-[#070b10]/85 p-3">
          <div className="flex items-center justify-between mb-3">
            <span className="font-mono text-[9px] text-[#bbc9cf] uppercase tracking-widest">CPU / RAM</span>
            <Activity className="w-3.5 h-3.5 text-[#00d1ff]" />
          </div>
          <AnimatedBar label="CPU" value={cpu} />
          <AnimatedBar label="RAM" value={ram} />
        </div>
      </div>

      <div className="relative mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-red-400/20 bg-red-950/10 p-3 overflow-hidden">
          <span className="font-mono text-[9px] text-red-300 uppercase tracking-widest">Hardware Alert Queue</span>
          <div className="mt-2 rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-[10px] font-mono text-red-200">
            {alertLabels[tick % alertLabels.length]}
          </div>
        </div>
        <div className="rounded-lg border border-[#00d1ff]/20 bg-[#00d1ff]/5 p-3 overflow-hidden">
          <span className="font-mono text-[9px] text-[#00d1ff] uppercase tracking-widest">Active Application Timeline</span>
          <div className="mt-2 flex items-center justify-between rounded-md border border-white/10 bg-[#070b10]/80 px-3 py-2 text-[10px] font-mono text-[#dae3ee]">
            <span>{timeline[tick % timeline.length]}</span>
            <span className="text-emerald-300">recorded</span>
          </div>
        </div>
      </div>
    </div>
  );
});

const HeroEarlyAccessCard = React.memo(function HeroEarlyAccessCard({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="hero-early-access-card rounded-xl border border-amber-300/45 bg-[#16120a]/88 p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-amber-300/12 via-transparent to-[#00d1ff]/8"></div>
      <div className="relative flex items-start justify-between gap-4">
        <div>
          <span className="inline-flex items-center rounded-full border border-amber-400/35 bg-amber-400/10 px-2.5 py-1 text-[8px] font-black uppercase tracking-widest text-amber-200 font-mono">
            Limited Early Access
          </span>
          <h3 className="mt-2 text-sm font-black uppercase tracking-wide text-amber-100">Early Access Program</h3>
          <p className="mt-1 text-[11px] leading-relaxed text-[#bbc9cf]">
            Priority onboarding for teams evaluating endpoint integrity, login telemetry, and hardware tamper detection.
          </p>
        </div>
        <button
          type="button"
          onClick={onOpen}
          className="enterprise-hero-button early-access-yellow-button shrink-0 rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-wider"
        >
          Join
        </button>
      </div>
      <div className="relative mt-3 grid grid-cols-3 gap-2 text-[9px] font-mono text-[#bbc9cf]">
        <span className="rounded border border-amber-300/20 bg-amber-300/8 px-2 py-1">Priority access</span>
        <span className="rounded border border-amber-300/20 bg-amber-300/8 px-2 py-1">Security review</span>
        <span className="rounded border border-amber-300/20 bg-amber-300/8 px-2 py-1">Product previews</span>
      </div>
    </div>
  );
});

const DeferredLandingSection = React.memo(function DeferredLandingSection({
  children,
  minHeight = 620,
}: {
  children: React.ReactNode;
  minHeight?: number;
}) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [shouldRender, setShouldRender] = useState(false);

  useEffect(() => {
    const node = rootRef.current;
    if (!node) return;
    if (!("IntersectionObserver" in window)) {
      setShouldRender(true);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setShouldRender(true);
        observer.disconnect();
      }
    }, { rootMargin: "760px 0px" });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={rootRef} style={{ minHeight }}>
      {shouldRender ? children : null}
    </div>
  );
});

const HeroStatsStrip = React.memo(function HeroStatsStrip() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((current) => current + 1), 4200);
    return () => window.clearInterval(timer);
  }, []);

  const stats = [
    { label: "Protected Devices", value: (12486 + (tick % 8)).toLocaleString(), className: "text-[#00d1ff]", duration: 2100 },
    { label: "Active Sessions", value: (1284 + (tick % 6)).toLocaleString(), className: "text-emerald-300", duration: 2300 },
    { label: "Hardware Alerts", value: String(27 + (tick % 3)), className: "text-amber-300", duration: 1800 },
    { label: "System Uptime", value: "99.98%", className: "text-[#a4e6ff]", duration: 2500 },
  ];

  return (
    <div className="hero-stats-strip lg:col-span-12 grid grid-cols-2 lg:grid-cols-4 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="rounded-xl border border-[#00d1ff]/18 bg-[#0d131b]/82 px-4 py-3 backdrop-blur-md">
          <span className="block text-[9px] font-mono uppercase tracking-widest text-[#bbc9cf]">{stat.label}</span>
          <RollingKpiValue
            value={stat.value}
            className={`mt-1 block text-xl md:text-2xl font-black tabular-nums ${stat.className}`}
            duration={stat.duration}
          />
        </div>
      ))}
    </div>
  );
});

function MetricTile({ label, value, tone }: { label: string; value: string; tone: "cyan" | "amber" | "emerald" }) {
  const toneClass = tone === "cyan" ? "text-[#00d1ff]" : tone === "amber" ? "text-amber-300" : "text-emerald-300";
  return (
    <div className="rounded-lg border border-white/10 bg-[#070b10]/85 p-3">
      <span className="block font-mono text-[8px] text-[#bbc9cf] uppercase tracking-widest">{label}</span>
      <span className={`mt-1 block text-lg font-black ${toneClass}`}>{value}</span>
    </div>
  );
}

function AnimatedBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between text-[9px] font-mono text-[#bbc9cf] mb-1">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-[#1b2530] overflow-hidden">
        <div className="h-full rounded-full bg-gradient-to-r from-[#00d1ff] to-emerald-300 transition-all duration-700" style={{ width: `${value}%` }}></div>
      </div>
    </div>
  );
}

const KpiAndMonitoringSections = React.memo(function KpiAndMonitoringSections({
  onNavigate
}: {
  onNavigate: LandingPageProps["onNavigate"];
}) {
  const chartWaveLineRef = useRef<SVGPathElement | null>(null);
  const chartWaveFillRef = useRef<SVGPathElement | null>(null);
  const [chartGridCells, setChartGridCells] = useState<string[]>(() =>
    Array.from({ length: 64 }, (_, i) => (
      i === 42 ? "alert" : Math.random() > 0.85 ? "warning" : "nominal"
    ))
  );
  const [deviceAlertCell, setDeviceAlertCell] = useState<number | null>(42);
  const [threatLevel, setThreatLevel] = useState(12);

  useEffect(() => {
    let isVisible = !document.hidden;

    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
    };

    const gridTimer = window.setInterval(() => {
      if (!isVisible) return;
      setChartGridCells(prev =>
        prev.map((state, idx) => {
          if (idx === deviceAlertCell) return "alert";
          if (Math.random() > 0.94) {
            return Math.random() > 0.65 ? "warning" : "nominal";
          }
          return state;
        })
      );
    }, 2400);

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(gridTimer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [deviceAlertCell]);

  useEffect(() => {
    let tick = 0;
    let animationFrameId = 0;
    let lastFrameAt = 0;
    let isRunning = false;
    const points = new Array<string>(25);

    const updateWave = (now: number) => {
      if (!isRunning) return;

      if (now - lastFrameAt < 100) {
        animationFrameId = requestAnimationFrame(updateWave);
        return;
      }

      lastFrameAt = now;
      tick += 0.15;
      for (let i = 0; i <= 24; i++) {
        const x = (i / 24) * 350;
        const y = 90 + Math.sin(i * 0.45 + tick) * 22 + Math.cos(i * 0.2 + tick * 1.5) * 10;
        points[i] = `${x},${y}`;
      }
      const wavePath = `M ${points.join(" L ")}`;
      chartWaveLineRef.current?.setAttribute("d", wavePath);
      chartWaveFillRef.current?.setAttribute("d", `${wavePath} L 350,180 L 0,180 Z`);
      animationFrameId = requestAnimationFrame(updateWave);
    };

    const startWave = () => {
      if (isRunning || document.hidden) return;
      isRunning = true;
      animationFrameId = requestAnimationFrame(updateWave);
    };

    const stopWave = () => {
      isRunning = false;
      cancelAnimationFrame(animationFrameId);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopWave();
      } else {
        startWave();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    startWave();

    return () => {
      stopWave();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const handleResolvePreviewAlarms = useCallback(() => {
    setDeviceAlertCell(null);
    setThreatLevel(0);
    setChartGridCells(prev => prev.map(s => s === "alert" ? "nominal" : s));
  }, []);

  const handleTriggerPreviewThreat = useCallback(() => {
    setDeviceAlertCell(42);
    setThreatLevel(12);
    setChartGridCells(prev => {
      const next = [...prev];
      next[42] = "alert";
      return next;
    });
  }, []);

  return (
    <>
      <section id="kpi-banner" className="landing-perf-region grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8 select-none">
        <div className="glass-panel p-4 md:p-5 rounded-xl text-center flex flex-col justify-center border border-[#00d1ff]/10 hover:border-[#00d1ff]/30 transition-all duration-300 bg-[#121c24]/40">
          <span className="font-mono text-[10px] text-[#bbc9cf] uppercase tracking-widest mb-1.5 block">Protected Devices</span>
          <RollingKpiValue value="14,209" duration={1980} className="text-3xl md:text-4xl font-black text-[#00d1ff] tracking-tight glow-active" />
        </div>
        <div className="glass-panel p-4 md:p-5 rounded-xl text-center flex flex-col justify-center border border-[#00d1ff]/10 hover:border-[#00d1ff]/30 transition-all duration-300 bg-[#121c24]/40">
          <span className="font-mono text-[10px] text-[#bbc9cf] uppercase tracking-widest mb-1.5 block">Active Sessions</span>
          <RollingKpiValue value="842" duration={2160} className="text-3xl md:text-4xl font-black text-[#dae3ee] tracking-tight" />
        </div>
        <div className={`glass-panel p-4 md:p-5 rounded-xl text-center flex flex-col justify-center transition-all duration-500 bg-[#1a0f12]/30 ${deviceAlertCell ? "border-red-500/40 bg-red-950/15" : "border-[#00d1ff]/10"}`}>
          <span className={`font-mono text-[10px] uppercase tracking-widest mb-1.5 block ${deviceAlertCell ? "text-red-400" : "text-[#bbc9cf]"}`}>Hardware Alerts</span>
          <span className={`text-3xl md:text-4xl font-black tracking-tight transition-all ${deviceAlertCell ? "text-red-400 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" : "text-emerald-400"}`}>
            <RollingKpiValue value={deviceAlertCell ? `${threatLevel}` : "0"} duration={1840} className="" />
          </span>
        </div>
        <div className="glass-panel p-4 md:p-5 rounded-xl text-center flex flex-col justify-center border border-[#00d1ff]/10 hover:border-[#00d1ff]/30 transition-all duration-300 bg-[#121c24]/40">
          <span className="font-mono text-[10px] text-[#bbc9cf] uppercase tracking-widest mb-1.5 block">System Uptime</span>
          <RollingKpiValue value="99.98%" duration={2380} className="text-3xl md:text-4xl font-black text-[#00d1ff] tracking-tight" />
        </div>
      </section>

      <section id="live-monitoring-center" className="landing-perf-region mb-16 relative select-none">
        <div className="absolute inset-0 bg-[#00d1ff]/5 blur-3xl rounded-full max-w-4xl mx-auto pointer-events-none"></div>
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-x-4 gap-y-2 mb-6">
          <div>
            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
              <Activity className="w-6 h-6 text-[#00d1ff]" />
              Live Monitoring Center
            </h2>
            <p className="text-sm text-[#bbc9cf] font-light mt-1">
              Real-time telemetry waveform, throughput statistics, and active command subnet node metrics.
            </p>
          </div>
          
          <div className="flex gap-2">
            {deviceAlertCell ? (
              <button 
                onClick={handleResolvePreviewAlarms}
                className="px-4 py-2 border border-emerald-500/30 text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/15 rounded-lg text-xs font-mono font-bold tracking-wide transition-all uppercase flex items-center gap-1.5 active:scale-95 cursor-pointer"
              >
                <CheckCircle2 className="w-4 h-4" />
                Resolve Subnet Alarms
              </button>
            ) : (
              <button 
                onClick={handleTriggerPreviewThreat}
                className="px-4 py-2 border border-red-500/30 text-red-400 bg-red-500/5 hover:bg-red-500/15 rounded-lg text-xs font-mono font-bold tracking-wide transition-all uppercase flex items-center gap-1.5 active:scale-95 cursor-pointer"
              >
                <AlertTriangle className="w-4 h-4 animate-pulse" />
                Simulate Subnet Threat
              </button>
            )}
          </div>
        </div>

        <div className="glass-panel rounded-xl border border-[#3c494e]/30 grid grid-cols-1 md:grid-cols-2 bg-[#0a0f14]/90 shadow-2xl relative z-10 overflow-hidden">
          <div className="p-6 border-b md:border-b-0 md:border-r border-[#3c494e]/20 flex flex-col gap-4 justify-between min-h-[310px]">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-mono tracking-widest font-bold text-[#00d1ff] uppercase">RAM Integrity Trend</span>
              <span className="bg-[#00d1ff]/10 text-[#00d1ff] border border-[#00d1ff]/20 text-[9px] font-mono font-semibold px-2 py-0.5 rounded flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00d1ff] animate-ping"></span>
                INTEGRITY MONITORING STREAM
              </span>
            </div>
            
            <div className="h-32 w-full bg-[#070b10] border border-white/5 rounded-lg relative overflow-hidden flex items-end">
              <div className="absolute inset-0 bg-grid opacity-20 pointer-events-none"></div>
              
              <svg className="w-full h-full" viewBox="0 0 350 180" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="waveGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00d1ff" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#00d1ff" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path 
                  ref={chartWaveFillRef}
                  d="M 0,90 L 350,90 L 350,180 L 0,180 Z" 
                  fill="url(#waveGrad)" 
                  className="transition-all duration-100 ease-linear"
                />
                <path 
                  ref={chartWaveLineRef}
                  d="M 0,90 L 350,90" 
                  fill="none" 
                  stroke="#00d1ff" 
                  strokeWidth="2.5" 
                  strokeLinecap="round"
                  className="transition-all duration-100 ease-linear drop-shadow-[0_0_6px_#00d1ff]"
                />
              </svg>

              <div className="absolute bottom-2 left-2 flex items-center gap-1.5 font-mono text-[8px] text-[#bbc9cf] bg-[#141a22]/80 px-2 py-0.5 rounded border border-white/5 uppercase">
                <span>RAM Verification Activity: ACTIVE</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
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

          <div className="p-6 flex flex-col gap-4 justify-between min-h-[310px]">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-mono tracking-widest font-bold text-[#bbc9cf] uppercase">Subnet Node Grid Array</span>
              <span className="text-[9px] font-mono text-[#00d1ff] font-bold">64 ACTIVE ENDPOINTS</span>
            </div>
            
            <div className="grid grid-cols-8 gap-1.5 bg-[#070b10] p-3 border border-white/5 rounded-lg h-32 items-center justify-center">
              {chartGridCells.map((state, idx) => (
                <div 
                  key={idx} 
                  className={getGridCellClassName(state)}
                  title={`Sector cell ${idx} status: ${state}`}
                />
              ))}
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

            <button 
              onClick={() => onNavigate("dashboard")}
              className="w-full bg-[#00d1ff]/10 hover:bg-[#00d1ff]/20 border border-[#00d1ff]/30 text-[#00d1ff] text-xs font-bold uppercase py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 active:scale-95"
            >
              <Server className="w-4 h-4 text-[#00d1ff]" />
              Explore Command Live Grid
            </button>
          </div>
        </div>
      </section>
    </>
  );
});

const HardwareCardsSection = React.memo(function HardwareCardsSection() {
  const ramValueRef = useRef(72);
  const ramBarRef = useRef<HTMLDivElement | null>(null);
  const ramTextRef = useRef<HTMLSpanElement | null>(null);
  const biosHashRef = useRef<HTMLSpanElement | null>(null);

  const setRamValue = useCallback((nextValue: number) => {
    ramValueRef.current = nextValue;
    if (ramBarRef.current) {
      ramBarRef.current.style.width = `${nextValue}%`;
    }
    if (ramTextRef.current) {
      ramTextRef.current.textContent = `${nextValue}% LOAD`;
    }
  }, []);

  const setBiosHash = useCallback((nextHash: string) => {
    if (biosHashRef.current) {
      biosHashRef.current.textContent = nextHash;
    }
  }, []);

  useEffect(() => {
    let isVisible = !document.hidden;

    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
    };

    const ramTimer = window.setInterval(() => {
      if (!isVisible) return;
      setRamValue(Math.min(98, Math.max(45, ramValueRef.current + Math.floor(Math.random() * 7) - 3)));
    }, 1400);

    const biosTimer = window.setInterval(() => {
      if (!isVisible) return;
      const currentHash = biosHashRef.current?.textContent || "0x0F3C99B2";
      setBiosHash(currentHash.slice(0, 8) + HEX_CHARS[Math.floor(Math.random() * 16)]);
    }, 1200);

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(ramTimer);
      window.clearInterval(biosTimer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [setBiosHash, setRamValue]);

  return (
    <section id="terminal-diagram" className="landing-perf-region relative mb-24">
      <div className="absolute inset-0 bg-[#00d1ff]/5 blur-3xl rounded-full max-w-2xl mx-auto pointer-events-none"></div>
      
      <div className="mb-6">
        <h2 className="text-xl md:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <ShieldAlert className="w-5.5 h-5.5 text-[#00d1ff]" />
          Sentinel Core Hardware Cards
        </h2>
        <p className="text-xs text-[#bbc9cf] font-light mt-1">
          Active endpoint digital signatures, biometrics, motherboard TPM handshakes, and cryptographic memory baselines.
        </p>
      </div>

      <div className="relative w-full bg-[#0a0f14]/90 p-6 rounded-xl border border-[#3c494e]/30 shadow-2xl z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 overflow-hidden">
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="absolute top-[20%] w-full h-[1px] bg-gradient-to-r from-transparent via-[#00d1ff] to-transparent"></div>
          <div className="absolute top-[50%] w-full h-[1px] bg-gradient-to-r from-transparent via-[#00d1ff] to-transparent animate-pulse"></div>
          <div className="absolute top-[80%] w-full h-[1px] bg-gradient-to-r from-transparent via-[#00d1ff] to-transparent"></div>
          <div className="absolute left-[20%] h-full w-[1px] bg-gradient-to-b from-transparent via-[#00d1ff] to-transparent"></div>
          <div className="absolute left-[75%] h-full w-[1px] bg-gradient-to-b from-transparent via-[#00d1ff] to-transparent animate-pulse" style={{ animationDelay: "2s" }}></div>
        </div>

        <div 
          className="glass-panel p-4 rounded-lg border-[#00d1ff]/25 bg-[#141c24]/75 select-none relative group cursor-pointer hover:border-[#00d1ff]/60 transition-all duration-300 animate-float-1"
          onClick={() => setRamValue(Math.min(ramValueRef.current + 5, 99))}
          title="Click to recalculate secure baseline allocation score"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-[9px] text-[#00d1ff] tracking-wider font-semibold">NODE-4912</span>
            <Cpu className="w-4 h-4 text-[#00d1ff] animate-spin" />
          </div>
          <h4 className="text-xs font-semibold text-[#dae3ee]">RAM Verified (32GB)</h4>
          
          <div className="w-full bg-[#2d363e]/50 h-2 mt-4 rounded-full overflow-hidden relative border border-white/5">
            <div 
              ref={ramBarRef}
              style={{ width: "72%" }}
              className="bg-gradient-to-r from-cyan-500 to-[#00d1ff] h-full shadow-[0_0_8px_rgba(0,209,255,0.7)] transition-all duration-500 flex items-center justify-end"
            >
              <div className="h-full w-1 bg-white/50 animate-pulse"></div>
            </div>
          </div>
          <div className="flex justify-between items-center text-[8px] font-mono mt-2 text-[#bbc9cf]/80">
            <span>CAPACITY NOMINAL</span>
            <span ref={ramTextRef} className="text-[#00d1ff] font-bold">72% LOAD</span>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-lg border-[#00d1ff]/20 bg-[#141c24]/75 select-none relative cursor-pointer hover:border-[#00d1ff]/50 transition-all duration-300 animate-float-2">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-[9px] text-[#00d1ff] tracking-wider font-semibold">SERVER-DELTA</span>
            <Sliders className="w-4 h-4 text-[#00d1ff] animate-pulse" />
          </div>
          <h4 className="text-xs font-semibold text-[#dae3ee]">BIOS Identity Intact</h4>
          
          <div className="flex flex-col gap-2 mt-4">
            <div className="flex gap-1">
              <div className="h-1.5 flex-1 bg-[#00d1ff] rounded-full shadow-[0_0_8px_#00d1ff] animate-pulse"></div>
              <div className="h-1.5 flex-1 bg-[#00d1ff] rounded-full shadow-[0_0_8px_#00d1ff] animate-pulse" style={{ animationDelay: "0.2s" }}></div>
              <div className="h-1.5 flex-1 bg-gradient-to-r from-[#00d1ff] to-[#a4e6ff] rounded-full shadow-[0_0_8px_#00d1ff] animate-pulse" style={{ animationDelay: "0.4s" }}></div>
            </div>
            <div className="h-1.5 w-3/4 bg-[#00d1ff] rounded-full animate-pulse" style={{ animationDelay: "0.1s" }}></div>
          </div>
          <div className="font-mono text-[8.5px] mt-2 text-[#bbc9cf]/80 flex justify-between items-center">
            <span>UEFI KEYHASH:</span>
            <span ref={biosHashRef} className="text-cyan-400 font-bold">0x0F3C99B2</span>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-lg border-red-500/30 bg-red-950/10 cursor-pointer hover:border-red-500/60 transition-all duration-300 animate-float-1 animate-warning-border select-none">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-[9px] text-red-400 tracking-wider font-extrabold">NODE-7714</span>
            <HardDrive className="w-4 h-4 text-red-400 animate-pulse" />
          </div>
          <h4 className="text-xs font-semibold text-[#dae3ee]">RAM Change Detected</h4>
          <div className="mt-3 p-1 rounded bg-red-900/20 border border-red-500/20 text-center font-mono text-[9px] text-red-300 animate-pulse">
            HW CONFIG MISMATCH
          </div>
          <span className="font-mono text-[8.5px] text-red-400/90 mt-2 block font-semibold">EXPECT: 64GB | ACTIVE: 32GB</span>
        </div>

        <div className="glass-panel p-4 rounded-lg border-[#00d1ff]/20 bg-[#141c24]/75 select-none cursor-pointer hover:border-[#00d1ff]/50 transition-all duration-300 animate-float-2">
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

        <div className="glass-panel p-4 rounded-lg border-red-500/20 bg-red-950/10 animate-float-1 select-none cursor-pointer hover:border-red-500/40 transition-all duration-300">
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
  );
});

export default function LandingPage({ onNavigate }: LandingPageProps) {
  // Early access form states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [businessEmail, setBusinessEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [formError, setFormError] = useState("");
  const [emailSent, setEmailSent] = useState(false);

  const emailValidationError = (value: string) => {
    const email = value.trim().toLowerCase();
    const match = email.match(/^([A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)$/);
    if (!match) return "Enter a valid email address, for example employee@company.com.";
    const local = match[1];
    const domain = match[2].replace(/\.$/, "");
    const labels = domain.split(".");
    const blocked = new Set(["example.com", "test.com", "invalid", "localhost"]);
    const personal = new Set(["gmail.com", "outlook.com", "yahoo.com", "icloud.com"]);
    const secondLevel = labels.length >= 2 ? labels[labels.length - 2] : "";
    if (blocked.has(domain) || ["invalid", "localhost"].includes(labels[labels.length - 1])) return "Use a real personal or business email domain.";
    if (local.startsWith(".") || local.endsWith(".") || local.includes("..")) return "Enter a valid email address.";
    if (labels.some((label) => !label || label.startsWith("-") || label.endsWith("-"))) return "Enter a valid email domain.";
    if (labels.some((label) => /^\d+$/.test(label))) return "Email domain cannot contain numeric-only labels.";
    if (!personal.has(domain) && (secondLevel.length < 4 || /^\d/.test(secondLevel))) return "Use a legitimate personal or business email domain.";
    return "";
  };

  const resetEarlyAccessForm = () => {
    setFormSubmitted(false);
    setFullName("");
    setCompanyName("");
    setBusinessEmail("");
    setFormError("");
    setEmailSent(false);
  };

  const submitEarlyAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = businessEmail.trim();
    if (!email) {
      setFormError("Business Email is required.");
      return;
    }
    const emailError = emailValidationError(email);
    if (emailError) {
      setFormError(emailError);
      return;
    }
    setFormError("");
    setIsSubmitting(true);
    try {
      const response = await authFetch("/api/early-access", {
        method: "POST",
        body: JSON.stringify({
          fullName: fullName.trim(),
          company: companyName.trim(),
          email,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setFormError(payload.error || "Unable to submit early access request.");
        return;
      }
      if (payload.emailNotificationSent === false) {
        setFormError(payload.message || "Request saved, but email notification could not be sent.");
        setEmailSent(false);
      } else {
        setEmailSent(true);
      }
      setFormSubmitted(true);
    } catch {
      setFormError("Unable to reach the registration service. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };



  const protocolCards = useMemo(() => {
    return CORE_TELEMETRY_PROTOCOLS.map((protocol, i) => {
      const renderIcon = () => {
        switch(protocol.icon) {
          case "Cpu": return <Cpu className="w-5 h-5 text-[#00d1ff]" />;
          case "HardDrive": return <HardDrive className="w-5 h-5 text-[#00d1ff]" />;
          case "Layers": return <Layers className="w-5 h-5 text-[#00d1ff]" />;
          case "ShieldAlert": return <ShieldAlert className="w-5 h-5 text-[#00d1ff]" />;
          case "Fingerprint": return <Fingerprint className="w-5 h-5 text-[#00d1ff]" />;
          case "Globe": return <Globe className="w-5 h-5 text-[#00d1ff]" />;
          case "BellRing": return <BellRing className="w-5 h-5 text-[#00d1ff]" />;
          case "Sliders": return <Sliders className="w-5 h-5 text-[#00d1ff]" />;
          default: return <Shield className="w-5 h-5 text-[#00d1ff]" />;
        }
      };

      return (
        <div 
          key={i} 
          className="glass-panel p-6 rounded-xl hover:bg-[#1C2128]/75 transition-all duration-300 group border border-[#3c494e]/15 hover:border-[#00d1ff]/40 select-none cursor-pointer hover:shadow-[0_0_15px_rgba(0,209,255,0.06)]"
        >
          <div className="w-10 h-10 rounded-full bg-[#182028] flex items-center justify-center mb-4 border border-[#3c494e]/30 group-hover:border-[#00d1ff]/60 group-hover:shadow-[0_0_12px_rgba(0,209,255,0.25)] transition-all">
            {renderIcon()}
          </div>
          <h3 className="text-base font-bold text-[#dae3ee] mb-2 group-hover:text-[#00d1ff] transition-colors font-mono">
            {protocol.title}
          </h3>
          <p className="text-[#bbc9cf] text-xs leading-relaxed font-light">
            {protocol.description}
          </p>
        </div>
      );
    });
  }, []);

  return (
    <div id="landing-screen" className="relative min-h-screen bg-[#0A0C10] text-[#dae3ee] font-sans overflow-x-hidden selection:bg-[#00d1ff]/20">
      <LandingScrollPerformanceController />
      <HeroTelemetryBackdrop />
      
      {/* Interactive WebGL Matrix/Network Background Overlay shader */}
      <ShaderBackground />
      
      {/* Scanline interference CRT filter overlay */}
      <div className="scanline"></div>

      {/* Top Header Navigation */}
      <nav id="landing-navbar" className="relative z-50 flex items-center justify-between px-6 md:px-12 h-16 w-full bg-[#0A0C10]/80 backdrop-blur-md border-b border-[#3c494e]/30">
        <div 
          onClick={() => onNavigate("landing")}
          className="flex items-center gap-3 cursor-pointer hover:opacity-90 transition-all group"
          title="Refresh Fleet Gate Gateway"
        >
          <div className="w-9 h-9 rounded-md bg-[#182028] border border-[#00d1ff]/40 flex items-center justify-center glow-accent group-hover:border-[#00d1ff]/80 transition-colors">
            <SentinelLogo className="w-5.5 h-5.5 group-hover:scale-105 transition-transform" />
          </div>
          <span className="font-headline-md text-xl md:text-2xl text-[#00d1ff] tracking-tighter font-extrabold select-none group-hover:text-cyan-300 transition-colors">
            SENTINEL COMMAND
          </span>
        </div>
        <div className="flex items-center gap-4">
          <button 
            id="nav-admin-signup-btn"
            onClick={() => onNavigate("admin-signup")}
            className="enterprise-hero-button hidden md:flex items-center gap-2 px-4 py-2 border border-emerald-400/30 rounded-lg text-emerald-300 bg-emerald-400/5 text-sm font-medium tracking-wide"
          >
            Admin Sign Up
          </button>
          <button 
            id="nav-dashboard-btn"
            onClick={() => onNavigate("dashboard")}
            className="enterprise-hero-button hidden md:flex items-center gap-2 px-4 py-2 border border-[#3c494e]/40 rounded-lg text-[#bbc9cf] text-sm font-medium tracking-wide"
          >
            Launch Command
          </button>
          <button 
            id="nav-login-btn"
            onClick={() => onNavigate("login")}
            className="enterprise-hero-button flex items-center gap-2 px-5 py-2 border border-[#00d1ff]/30 rounded-lg text-[#00d1ff] bg-[#00d1ff]/5 text-sm font-medium tracking-wide glow-accent"
          >
            <LogIn className="w-4 h-4" />
            Admin Login
          </button>
        </div>
      </nav>

      {/* Hero Header Area */}
      <main className="relative z-10 px-6 md:px-12 max-w-7xl mx-auto pt-5 lg:pt-6 pb-16">
        
        <section id="hero-heading" className="landing-perf-region hero-enterprise-shell grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-8 items-center mb-3 relative">
          
          {/* LEFT COLUMN: Primary content and actions */}
          <div className="lg:col-span-7 flex flex-col items-start text-left space-y-4 lg:space-y-5">
            
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#00d1ff]/30 bg-[#00d1ff]/10 text-[#00d1ff] font-mono text-xs font-semibold select-none shadow-[0_0_15px_rgba(0,209,255,0.06)]">
              <span className="w-2 rounded-full h-2 bg-[#00d1ff] glow-active"></span>
              ENTERPRISE HARDWARE INTEGRITY PLATFORM
            </div>

            <TypewriterHeroText />

            <p className="text-[#bbc9cf] text-sm md:text-base leading-relaxed font-light max-w-xl">
              Asset Sentinel continuously monitors hardware integrity, detects unauthorized RAM and motherboard changes, validates device identity, and provides real-time security visibility across enterprise environments.
            </p>

            <div className="hero-action-grid flex flex-col sm:flex-row gap-3 w-full sm:w-auto select-none pt-2">
              <button 
                id="hero-login-btn"
                onClick={() => onNavigate("login")}
                className="enterprise-hero-button px-6 py-3 border border-[#00d1ff]/40 bg-[#00d1ff]/5 text-[#00d1ff] rounded-lg font-semibold text-xs uppercase tracking-wider cursor-pointer shadow-[0_0_15px_rgba(0,209,255,0.1)] flex items-center justify-center gap-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                Admin Sign In
              </button>
              <button 
                id="hero-admin-signup-btn"
                onClick={() => onNavigate("admin-signup")}
                className="enterprise-hero-button enterprise-primary-button px-6 py-3 bg-[#00d1ff] text-[#003543] font-bold rounded-lg shadow-[0_0_20px_rgba(0,209,255,0.35)] cursor-pointer flex items-center justify-center text-xs uppercase tracking-wider"
              >
                Admin Sign Up
              </button>
              <button 
                id="launch-dashboard-btn"
                onClick={() => onNavigate("dashboard")}
                className="enterprise-hero-button px-6 py-3 border border-[#3c494e]/50 text-[#dae3ee] font-bold rounded-lg cursor-pointer flex items-center justify-center text-xs uppercase tracking-wider"
              >
                Launch Dashboard
              </button>
              <button 
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="enterprise-hero-button px-6 py-3 border border-amber-400/35 bg-amber-400/10 text-amber-200 font-bold rounded-lg cursor-pointer flex items-center justify-center text-xs uppercase tracking-wider"
              >
                Get Early Access
              </button>
            </div>

            <button
              onClick={() => onNavigate("demo")}
              className="inline-flex items-center gap-2 mt-4 text-[#bbc9cf] hover:text-[#00d1ff] transition-colors text-xs font-semibold uppercase tracking-widest border-b border-dashed border-[#bbc9cf]/40 hover:border-[#00d1ff]/50 pb-1 mt-1.5"
            >
              Launch Command Fleet View Demo 
              <ArrowRight className="w-3.5 h-3.5 text-[#00d1ff]" />
            </button>
          </div>

          {/* RIGHT COLUMN: live enterprise dashboard preview */}
          <div className="lg:col-span-5 w-full flex flex-col gap-3 justify-center lg:justify-end hero-preview-fade">
            <LiveDashboardPreview />
            <HeroEarlyAccessCard onOpen={() => setIsModalOpen(true)} />
          </div>

        </section>

        <KpiAndMonitoringSections onNavigate={onNavigate} />

        <DeferredLandingSection minHeight={380}>
          <HardwareCardsSection />
        </DeferredLandingSection>


        {/* Core Telemetry Protocols Display - Swiss visual, dark neon styling */}
        <DeferredLandingSection minHeight={460}>
        <section id="protocols-showcase" className="landing-perf-region max-w-7xl mx-auto">
          <div className="flex items-center justify-center gap-4 mb-12 select-none">
            <div className="h-px bg-gradient-to-r from-transparent to-[#00d1ff]/40 w-28"></div>
            <h2 className="text-2xl md:text-3xl font-bold text-[#dae3ee] text-center tracking-tight uppercase">
              Core Telemetry Protocols
            </h2>
            <div className="h-px bg-gradient-to-l from-transparent to-[#00d1ff]/40 w-28"></div>
          </div>

          <div id="protocols-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {protocolCards}
          </div>
        </section>
        </DeferredLandingSection>

        {/* Contact and Early Access Section near the bottom of the page */}
        <DeferredLandingSection minHeight={440}>
        <section id="contact-evaluation-sec" className="landing-perf-region mt-20 max-w-7xl mx-auto px-0 select-none">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Left side: Contact Us */}
            <div className="glass-panel p-8 rounded-xl border border-[#3c494e]/30 bg-[#161B22]/70 flex flex-col justify-between min-h-[300px] transition-all hover:border-[#00d1ff]/30 shadow-[0_4px_20px_rgba(0,0,0,0.2)]">
              <div>
                <span className="font-mono text-[9px] text-[#00d1ff] uppercase tracking-widest font-extrabold mb-2 block">
                  COMMUNICATION
                </span>
                <h3 className="text-xl md:text-2xl font-black text-[#dae3ee] tracking-tight uppercase mb-4">
                  Contact Us
                </h3>
                
                <p className="text-sm font-semibold text-[#dae3ee] mb-1 leading-snug">
                  Questions about Asset Sentinel?
                </p>
                <p className="text-xs text-[#bbc9cf] leading-relaxed font-light mb-6">
                  Interested in enterprise deployment, security monitoring, or hardware integrity protection?
                </p>
              </div>

              <div className="space-y-4 font-mono">
                <div className="p-3.5 bg-[#0d1217] border border-white/5 rounded-lg flex flex-col gap-1">
                  <span className="text-[9px] text-[#bbc9cf]/70 uppercase font-bold tracking-wider">Business Email</span>
                  <a 
                    href="mailto:contact@example.com" 
                    className="text-[#00d1ff] text-xs font-semibold hover:underline select-all cursor-pointer transition-colors"
                  >
                    contact@example.com
                  </a>
                </div>
                <div className="p-3.5 bg-[#0d1217] border border-white/5 rounded-lg flex flex-col gap-1">
                  <span className="text-[9px] text-[#bbc9cf]/70 uppercase font-bold tracking-wider">Response Time</span>
                  <span className="text-emerald-400 text-xs font-bold uppercase tracking-wide">
                    Within 24 Hours
                  </span>
                </div>
              </div>
            </div>

            {/* Right side: Early Access Program */}
            <div className="glass-panel p-8 rounded-xl border border-amber-300/35 bg-[#181308]/75 flex flex-col justify-between min-h-[300px] transition-all hover:border-amber-300/60 shadow-[0_4px_24px_rgba(250,204,21,0.08)] relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-tr from-amber-300/10 via-transparent to-[#00d1ff]/5 pointer-events-none"></div>
              
              <div>
                <span className="font-mono text-[9px] text-amber-200 uppercase tracking-widest font-extrabold mb-2 block">
                  EVALUATION POOL
                </span>
                <h3 className="text-xl md:text-2xl font-black text-[#dae3ee] tracking-tight uppercase mb-4">
                  Early Access Program
                </h3>
                
                <p className="text-sm font-semibold text-[#dae3ee] mb-4">
                  Join the first 100 organizations evaluating Asset Sentinel.
                </p>
                
                <div className="space-y-2 mt-4">
                  <span className="text-[9px] font-mono text-[#00d1ff] uppercase tracking-widest font-bold block">
                    Benefits:
                  </span>
                  <ul className="space-y-2.5 text-xs text-[#bbc9cf] font-light">
                    <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-300 shadow-[0_0_6px_rgba(250,204,21,0.9)]"></span>
                      Early platform access
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-300 shadow-[0_0_6px_rgba(250,204,21,0.9)]"></span>
                      Priority onboarding
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-300 shadow-[0_0_6px_rgba(250,204,21,0.9)]"></span>
                      Direct product feedback channel
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-300 shadow-[0_0_6px_rgba(250,204,21,0.9)]"></span>
                      Future enterprise feature previews
                    </li>
                  </ul>
                </div>
              </div>

              <button 
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="early-access-yellow-button w-full mt-6 px-6 py-3 font-mono text-xs font-black uppercase rounded-lg transition-all active:scale-95 cursor-pointer flex items-center justify-center gap-2"
              >
                Get Early Access
              </button>
            </div>

          </div>
        </section>
        </DeferredLandingSection>

      </main>

      {/* Landing Footer Area */}
      <footer id="landing-footer" className="relative z-10 w-full py-8 border-t border-[#3c494e]/20 mt-16 bg-[#060f16]/90 backdrop-blur-md select-none">
        <div className="text-center font-mono text-[11px] text-[#bbc9cf] uppercase tracking-widest">
          © {new Date().getFullYear()} SENTINEL COMMAND. ENTERPRISE TELEMETRY SYSTEMS. ALL RIGHTS RESERVED.
        </div>
      </footer>

      {/* Early Access Program Sign up Modal Overlay */}
      {isModalOpen && (
        <div 
          id="early-access-modal"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-md transition-all duration-300 animate-fade-in"
        >
          <div className="glass-panel early-access-yellow-panel w-full max-w-[440px] rounded-xl p-8 bg-[#161207]/95 border border-amber-300/60 backdrop-blur-xl flex flex-col relative z-[101]">
            
            {/* Cybernetic header details */}
            <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-amber-300 to-transparent"></div>
            
            {/* Close button with premium hover style */}
            <button 
              type="button"
              onClick={() => {
                setIsModalOpen(false);
                resetEarlyAccessForm();
              }}
              className="absolute top-4 right-4 text-[#bbc9cf] hover:text-amber-200 hover:rotate-90 transition-all duration-300 p-1.5 cursor-pointer rounded-full hover:bg-amber-300/10"
              aria-label="Close modal"
            >
              <X className="w-4 h-4" />
            </button>

            {!formSubmitted ? (
              <form 
                onSubmit={submitEarlyAccess}
                className="flex flex-col gap-5 mt-2"
              >
                <div className="flex flex-col items-center text-center gap-2 mb-1 select-none">
                  <div className="w-12 h-12 rounded-full bg-amber-300/10 border border-amber-300/45 flex items-center justify-center shadow-[0_0_18px_rgba(250,204,21,0.22)] mb-1">
                    <SentinelLogo className="w-6.5 h-6.5 animate-pulse" />
                  </div>
                  <h3 className="text-sm font-black text-amber-200 font-mono tracking-[0.2em] uppercase leading-none">
                    Early Access Request
                  </h3>
                  <span className="text-[9px] text-[#bbc9cf] font-mono tracking-widest uppercase mt-1">
                    Secure Verification Node
                  </span>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono" htmlFor="early-full-name">
                    Full Name
                  </label>
                  <input 
                    id="early-full-name"
                    className="early-access-yellow-input w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#070b10] border border-amber-300/15 focus:ring-1 focus:ring-amber-300 placeholder:text-[#3c494e] outline-none transition-all duration-200" 
                    placeholder="Security operations contact" 
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono" htmlFor="company-name">
                    Company Name
                  </label>
                  <input 
                    id="company-name"
                    className="early-access-yellow-input w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#070b10] border border-amber-300/15 focus:ring-1 focus:ring-amber-300 placeholder:text-[#3c494e] outline-none transition-all duration-200" 
                    placeholder="Enter corporate or business entity" 
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold uppercase tracking-widest text-[#bbc9cf] font-mono" htmlFor="business-email">
                    Business Email
                  </label>
                  <input 
                    id="business-email"
                    className="early-access-yellow-input w-full rounded-lg px-4 py-3 text-xs font-mono text-[#dae3ee] bg-[#070b10] border border-amber-300/15 focus:ring-1 focus:ring-amber-300 placeholder:text-[#3c494e] outline-none transition-all duration-200" 
                    placeholder="name@organization.com" 
                    required 
                    type="text"
                    value={businessEmail}
                    onChange={(e) => setBusinessEmail(e.target.value)}
                  />
                </div>

                {formError && (
                  <div className="text-red-400 font-mono text-[10px] bg-red-950/20 border border-red-500/20 px-3 py-2 rounded-md animate-pulse">
                    Error: {formError}
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={isSubmitting}
                  className="early-access-yellow-button w-full rounded-lg py-3.5 mt-2 flex items-center justify-center gap-2 text-xs font-mono font-black uppercase transition-all cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? "TRANSMITTING SIGNATURE..." : "Request Early Access"}
                </button>
              </form>
            ) : (
              <div className="flex flex-col items-center text-center gap-4 py-4">
                <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-400/50 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.2)] mb-2">
                  <span className="w-3 h-3 rounded-full bg-emerald-400 animate-ping absolute"></span>
                  <CheckCircle2 className="w-7 h-7 text-emerald-400 relative z-10" />
                </div>
                
                <h3 className="text-base font-black text-emerald-400 font-mono tracking-widest uppercase">
                  Request Received
                </h3>
                
                <div className="flex flex-col gap-2.5">
                  <p className="text-sm text-[#dae3ee] font-semibold leading-relaxed">
                    Thank you for your interest in Asset Sentinel.
                  </p>
                  <p className="text-xs text-[#bbc9cf] font-light leading-relaxed">
                    {emailSent
                      ? "Thank you! Your Early Access request has been submitted successfully. A confirmation email has been sent."
                      : "Your organization has been added to the Early Access Program waiting list."}
                  </p>
                  {formError && (
                    <p className="text-[10px] text-amber-200 font-mono leading-relaxed bg-amber-400/10 border border-amber-400/25 rounded-md px-3 py-2">
                      {formError}
                    </p>
                  )}
                </div>

                <button 
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false);
                    resetEarlyAccessForm();
                  }}
                  className="mt-6 px-6 py-2.5 bg-[#1B222A] hover:bg-[#252f3a] text-[#dae3ee] border border-white/10 rounded-lg text-xs font-mono font-bold uppercase tracking-wider transition-all cursor-pointer"
                >
                  Close Gateway
                </button>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

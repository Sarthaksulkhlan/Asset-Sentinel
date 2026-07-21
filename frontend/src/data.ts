import { Asset, SecurityFeedItem } from "./types";

const demoNow = new Date("2026-07-21T07:30:00.000Z");
const isoMinutesAgo = (minutes: number) => new Date(demoNow.getTime() - minutes * 60_000).toISOString();

export const DEMO_ASSETS: Asset[] = [
  {
    hostname: "DESKTOP-PETBKU1",
    status: "Online",
    employee: "DESKTOP-PETBKU1\\user",
    department: "Engineering",
    deviceId: "337b0328-9acb-e911-8102-040e3c0716a8",
    assetId: "337b0328-9acb-e911-8102-040e3c0716a8",
    ipAddress: "192.168.1.24",
    os: "Windows 11 Pro",
    ram: "16GB",
    ramUsage: "68.4%",
    diskUsage: "54%",
    networkUsage: "128 Mbps",
    uptime: "05:42:18",
    biosSerial: "CND93565RF",
    biosVersion: "HP Q85 Ver. 01.31.00",
    motherboardSerial: "PHQNFB2MYCQ25J",
    uuid: "337B0328-9ACB-E911-8102-040E3C0716A8",
    macAddress: "04:0E:3C:07:16:A8",
    lastLogin: isoMinutesAgo(250),
    lastLogout: "Currently Active",
    loginDuration: "04:10:00",
    loginsToday: 2,
    currentUser: "DESKTOP-PETBKU1\\user",
    currentWebsite: "C:\\Users\\user\\Desktop\\Nexis AS\\Asset-Sentinel",
    activeApplication: "VS Code",
    activeWindow: ".env - Asset-Sentinel - Visual Studio Code",
    lastActiveTime: isoMinutesAgo(1),
    lastExecutedProcess: "Code.exe",
    threatScore: 18,
    alerts: ["LOW: Chrome restricted-domain review", "INFO: Hardware baseline verified"],
    hardwareChanges: ["RAM baseline unchanged", "Motherboard serial unchanged"],
    unauthorizedSoftware: [],
    usbActivity: ["No unauthorized USB activity"],
    failedLoginAttempts: 0,
    alertStatus: "nominal",
    location: "Home Lab / Windows Service",
    lastReflash: "2026-06-28",
    cpuModel: "Intel Core i5-8265U",
    cpuUsage: "34.2%",
    lastSeen: isoMinutesAgo(1),
    lastSeenHuman: "1 minute ago",
    memoryUsedGb: 10.9,
    memoryAvailableGb: 5.1,
    loginsThisWeek: 9,
    lastSuccessfulLogin: isoMinutesAgo(250),
    lastFailedLogin: isoMinutesAgo(1150),
    applicationHistory: [],
    complianceStatus: true,
    history: [
      "Windows Service heartbeat active.",
      "Render API communication verified.",
      "Supabase-backed device telemetry synchronized.",
      "Hardware baseline verified with BIOS and baseboard serials."
    ],
    timeline: []
  },
  {
    hostname: "DevrishiBhardwaj",
    status: "Idle",
    employee: "Devrishi Bhardwaj",
    department: "Operations",
    deviceId: "demo-locked-devrishi",
    assetId: "demo-locked-devrishi",
    ipAddress: "192.168.1.41",
    os: "Windows 11 Pro",
    ram: "16GB",
    ramUsage: "41.6%",
    biosSerial: "DEMO-LOCKED-02",
    motherboardSerial: "LOCKED-MB-02",
    currentWebsite: "Locked in demo",
    activeApplication: "Locked Device",
    activeWindow: "Sign in required",
    lastActiveTime: isoMinutesAgo(9),
    alertStatus: "warning",
    location: "Demo Workspace",
    lastReflash: "2026-06-12",
    cpuModel: "Intel Core i7",
    cpuUsage: "12.8%",
    lastSeen: isoMinutesAgo(9),
    lastSeenHuman: "9 minutes ago",
    complianceStatus: true,
    history: ["Visible in demo fleet. Full telemetry requires sign in."]
  },
  {
    hostname: "AI",
    status: "Online",
    employee: "AI Lab Workstation",
    department: "Research",
    deviceId: "demo-locked-ai",
    assetId: "demo-locked-ai",
    ipAddress: "192.168.1.55",
    os: "Windows 11 Enterprise",
    ram: "32GB",
    ramUsage: "73.2%",
    biosSerial: "DEMO-LOCKED-03",
    motherboardSerial: "LOCKED-MB-03",
    currentWebsite: "Locked in demo",
    activeApplication: "Locked Device",
    activeWindow: "Sign in required",
    lastActiveTime: isoMinutesAgo(4),
    alertStatus: "nominal",
    location: "Demo Workspace",
    lastReflash: "2026-07-02",
    cpuModel: "AMD Ryzen 9",
    cpuUsage: "49.1%",
    lastSeen: isoMinutesAgo(4),
    lastSeenHuman: "4 minutes ago",
    complianceStatus: true,
    history: ["Visible in demo fleet. Full telemetry requires sign in."]
  }
];

const demoApplicationTimeline = [
  { application: "VS Code", application_name: "VS Code", window_title: ".env - Asset-Sentinel - Visual Studio Code", process_path: "C:\\Users\\user\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe", timestamp: isoMinutesAgo(1) },
  { application: "Chrome", application_name: "Chrome", window_title: "Asset Sentinel Dashboard - Google Chrome", process_path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", timestamp: isoMinutesAgo(8) },
  { application: "Excel", application_name: "Excel", window_title: "Asset Inventory Report.xlsx - Excel", process_path: "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE", timestamp: isoMinutesAgo(18) },
  { application: "Notepad", application_name: "Notepad", window_title: "agent-notes.txt - Notepad", process_path: "C:\\Windows\\System32\\notepad.exe", timestamp: isoMinutesAgo(31) },
  { application: "Teams", application_name: "Teams", window_title: "Daily Standup | Microsoft Teams", process_path: "C:\\Users\\user\\AppData\\Local\\Microsoft\\Teams\\current\\Teams.exe", timestamp: isoMinutesAgo(45) },
  { application: "File Explorer", application_name: "File Explorer", window_title: "Asset-Sentinel", process_path: "C:\\Windows\\explorer.exe", timestamp: isoMinutesAgo(72) },
  { application: "Settings", application_name: "Settings", window_title: "Windows Update", process_path: "C:\\Windows\\ImmersiveControlPanel\\SystemSettings.exe", timestamp: isoMinutesAgo(96) },
  { application: "Windows Explorer", application_name: "Windows Explorer", window_title: "Downloads", process_path: "C:\\Windows\\explorer.exe", timestamp: isoMinutesAgo(128) },
  { application: "Chrome", application_name: "Chrome", window_title: "Supabase Project - Google Chrome", process_path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", timestamp: isoMinutesAgo(165) },
  { application: "VS Code", application_name: "VS Code", window_title: "active_application_user_agent.py - Visual Studio Code", process_path: "C:\\Users\\user\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe", timestamp: isoMinutesAgo(205) }
];

export const DEMO_ASSET_DETAILS: Record<string, any> = {
  "DESKTOP-PETBKU1": {
    asset: { ...DEMO_ASSETS[0], application_history: demoApplicationTimeline },
    sessions: [
      { event_type: "LOGIN", username: "DESKTOP-PETBKU1\\user", hostname: "DESKTOP-PETBKU1", ip_address: "192.168.1.24", session_id: "1", login_timestamp: isoMinutesAgo(250), logout_timestamp: null, session_duration: "Active", active: true, last_seen: isoMinutesAgo(1), login_source: "windows_interactive_logon", windows_event_id: "4624", windows_event_record_id: "DEMO-4624-8451", recorded_at: isoMinutesAgo(250) },
      { event_type: "LOGOUT", username: "DESKTOP-PETBKU1\\user", hostname: "DESKTOP-PETBKU1", ip_address: "192.168.1.24", session_id: "1", login_timestamp: isoMinutesAgo(620), logout_timestamp: isoMinutesAgo(500), session_duration: "02:00:00", active: false, last_seen: isoMinutesAgo(500), login_source: "windows_logoff", windows_event_id: "4634", windows_event_record_id: "DEMO-4634-8120", recorded_at: isoMinutesAgo(500) },
      { event_type: "LOGIN", username: "DESKTOP-PETBKU1\\user", hostname: "DESKTOP-PETBKU1", ip_address: "192.168.1.24", session_id: "1", login_timestamp: isoMinutesAgo(620), logout_timestamp: isoMinutesAgo(500), session_duration: "02:00:00", active: false, last_seen: isoMinutesAgo(500), login_source: "windows_interactive_logon", windows_event_id: "4624", windows_event_record_id: "DEMO-4624-7812", recorded_at: isoMinutesAgo(620) }
    ],
    alerts: [
      { alert_type: "RESTRICTED_SITE_REVIEW", hostname: "DESKTOP-PETBKU1", severity: "LOW", timestamp: isoMinutesAgo(83), details: { description: "Chrome navigation matched a watchlist review rule.", application: "Chrome" } },
      { alert_type: "HARDWARE_BASELINE_VERIFIED", hostname: "DESKTOP-PETBKU1", severity: "INFO", timestamp: isoMinutesAgo(138), details: { description: "RAM, BIOS, UUID, and motherboard identity matched baseline." } }
    ],
    application_timeline: demoApplicationTimeline,
    hardware_changes: [
      { hostname: "DESKTOP-PETBKU1", change_type: "RAM_BASELINE", severity: "LOW", previous_value: { ram_total_gb: 16 }, current_value: { ram_total_gb: 16 }, difference: { changed: false }, detected_at: isoMinutesAgo(137) },
      { hostname: "DESKTOP-PETBKU1", change_type: "MOTHERBOARD_BASELINE", severity: "LOW", previous_value: { baseboard_serial: "PHQNFB2MYCQ25J" }, current_value: { baseboard_serial: "PHQNFB2MYCQ25J" }, difference: { changed: false }, detected_at: isoMinutesAgo(136) }
    ],
    timeline: [
      { type: "Application Started", timestamp: isoMinutesAgo(1), detail: "VS Code opened", description: ".env - Asset-Sentinel - Visual Studio Code", severity: "LOW" },
      { type: "Device Online", timestamp: isoMinutesAgo(1), detail: "Online - Last seen 1 minute ago", severity: "LOW" },
      { type: "Application Started", timestamp: isoMinutesAgo(8), detail: "Chrome opened", description: "Asset Sentinel Dashboard - Google Chrome", severity: "LOW" },
      { type: "Application Started", timestamp: isoMinutesAgo(18), detail: "Excel opened", description: "Asset Inventory Report.xlsx", severity: "LOW" },
      { type: "Alert", timestamp: isoMinutesAgo(83), detail: "Chrome restricted-domain review", description: "Low severity browsing rule matched.", severity: "LOW" },
      { type: "RAM Change", timestamp: isoMinutesAgo(137), detail: "RAM baseline verified", description: "No RAM change detected.", severity: "LOW" },
      { type: "Login", timestamp: isoMinutesAgo(250), detail: "DESKTOP-PETBKU1\\user logged in", severity: "LOW" }
    ],
    charts: {
      cpu_usage_history: [
        { timestamp: isoMinutesAgo(55), value: 22 }, { timestamp: isoMinutesAgo(45), value: 31 }, { timestamp: isoMinutesAgo(35), value: 44 }, { timestamp: isoMinutesAgo(25), value: 27 }, { timestamp: isoMinutesAgo(15), value: 39 }, { timestamp: isoMinutesAgo(5), value: 34 }
      ],
      ram_usage_history: [
        { timestamp: isoMinutesAgo(55), value: 58 }, { timestamp: isoMinutesAgo(45), value: 61 }, { timestamp: isoMinutesAgo(35), value: 64 }, { timestamp: isoMinutesAgo(25), value: 67 }, { timestamp: isoMinutesAgo(15), value: 66 }, { timestamp: isoMinutesAgo(5), value: 68 }
      ],
      login_frequency: [
        { label: "Mon", value: 2 }, { label: "Tue", value: 2 }, { label: "Wed", value: 1 }, { label: "Thu", value: 2 }, { label: "Fri", value: 2 }
      ],
      application_usage: [
        { label: "VS Code", value: 36, application_name: "VS Code", total_duration_seconds: 5600, active_duration_seconds: 5100, productive_duration_seconds: 5100, idle_duration_seconds: 500, locked_duration_seconds: 0, percentage_of_session: 36, window_title: "Asset-Sentinel", process_path: "Code.exe", last_seen_at: isoMinutesAgo(1) },
        { label: "Chrome", value: 24, application_name: "Chrome", total_duration_seconds: 3700, active_duration_seconds: 3150, productive_duration_seconds: 2950, idle_duration_seconds: 550, locked_duration_seconds: 0, percentage_of_session: 24, window_title: "Dashboard / Supabase / Render", process_path: "chrome.exe", last_seen_at: isoMinutesAgo(8) },
        { label: "Excel", value: 16, application_name: "Excel", total_duration_seconds: 2480, active_duration_seconds: 2260, productive_duration_seconds: 2260, idle_duration_seconds: 220, locked_duration_seconds: 0, percentage_of_session: 16, window_title: "Asset Inventory Report.xlsx", process_path: "EXCEL.EXE", last_seen_at: isoMinutesAgo(18) },
        { label: "Teams", value: 12, application_name: "Teams", total_duration_seconds: 1880, active_duration_seconds: 1550, productive_duration_seconds: 1450, idle_duration_seconds: 330, locked_duration_seconds: 0, percentage_of_session: 12, window_title: "Daily Standup", process_path: "Teams.exe", last_seen_at: isoMinutesAgo(45) },
        { label: "Notepad", value: 7, application_name: "Notepad", total_duration_seconds: 1120, active_duration_seconds: 980, productive_duration_seconds: 900, idle_duration_seconds: 140, locked_duration_seconds: 0, percentage_of_session: 7, window_title: "agent-notes.txt", process_path: "notepad.exe", last_seen_at: isoMinutesAgo(31) },
        { label: "File Explorer", value: 5, application_name: "File Explorer", total_duration_seconds: 780, active_duration_seconds: 690, productive_duration_seconds: 650, idle_duration_seconds: 90, locked_duration_seconds: 0, percentage_of_session: 5, window_title: "Asset-Sentinel", process_path: "explorer.exe", last_seen_at: isoMinutesAgo(72) }
      ],
      application_usage_summary: {
        total_session_duration_seconds: 15000,
        total_foreground_duration_seconds: 15560,
        active_working_seconds: 13730,
        idle_seconds: 1530,
        locked_seconds: 240,
        productivity_percentage: 91.53,
        session_started_at: isoMinutesAgo(250),
        last_updated_at: isoMinutesAgo(1)
      },
      application_usage_periods: {},
      alert_trend: [
        { label: "Jul 17", value: 1 }, { label: "Jul 18", value: 0 }, { label: "Jul 19", value: 1 }, { label: "Jul 20", value: 2 }, { label: "Jul 21", value: 1 }
      ]
    }
  }
};

DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage_periods = {
  current_session: {
    items: DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage,
    summary: DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage_summary
  },
  today: {
    items: DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage,
    summary: DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage_summary
  },
  yesterday: {
    items: DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage.slice(0, 4),
    summary: { ...DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage_summary, productivity_percentage: 87.2, total_session_duration_seconds: 13200 }
  },
  last_2_days: {
    items: DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage,
    summary: { ...DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].charts.application_usage_summary, productivity_percentage: 89.1, total_session_duration_seconds: 28200 }
  }
};

DEMO_ASSETS[0].applicationHistory = demoApplicationTimeline;
DEMO_ASSETS[0].timeline = DEMO_ASSET_DETAILS["DESKTOP-PETBKU1"].timeline;

export const DEMO_SECURITY_FEED: SecurityFeedItem[] = [
  { timestamp: "13:28:45", node: "DESKTOP-PETBKU1", message: "Active application switched to VS Code.", type: "info" },
  { timestamp: "13:22:11", node: "DESKTOP-PETBKU1", message: "Chrome browsing review completed. No policy violation escalated.", type: "info" },
  { timestamp: "13:12:03", node: "DESKTOP-PETBKU1", message: "Application usage aggregate written for Excel.", type: "info" },
  { timestamp: "12:54:19", node: "DESKTOP-PETBKU1", message: "Hardware baseline verified: RAM and motherboard unchanged.", type: "info" },
  { timestamp: "12:31:09", node: "DESKTOP-PETBKU1", message: "Low severity restricted-domain review recorded.", type: "warning" }
];

export const INITIAL_ASSETS: Asset[] = [
  {
    hostname: "LPT-ENG-4912",
    status: "Online",
    employee: "Sarah Jenkins",
    ipAddress: "10.14.22.105",
    os: "macOS 14.2",
    ram: "32GB",
    biosSerial: "C02FX4H9Q6L4",
    lastLogin: "08:14 AM",
    currentWebsite: "github.com/asset-sentinel/core",
    alertStatus: "nominal",
    location: "Cupertino HQ, Lab 4",
    lastReflash: "2026-06-01",
    cpuModel: "Apple M3 Pro",
    complianceStatus: true,
    history: [
      "Routine hardware signatures validated.",
      "Automatic check-in complete.",
      "Vapor thermal index: 42°C [Optimal]."
    ]
  },
  {
    hostname: "WRK-FIN-0921",
    status: "Idle",
    employee: "Marcus Reed",
    ipAddress: "10.14.22.88",
    os: "Win 11 Pro",
    ram: "16GB",
    biosSerial: "PF3W7L9A",
    lastLogin: "Yesterday",
    currentWebsite: "salesforce.com/app/lightning",
    alertStatus: "warning",
    location: "Dublin Regional FinCenter",
    lastReflash: "2026-05-15",
    cpuModel: "Intel Core i7-13700",
    complianceStatus: false,
    history: [
      "User inactive for > 2 hours with active high-privilege session.",
      "Alert dispatched to local security lead admin.",
      "BIOS fingerprint intact."
    ]
  },
  {
    hostname: "SRV-DB-PROD-01",
    status: "Overload",
    employee: "System Account",
    ipAddress: "10.0.1.15",
    os: "Ubuntu 22.04",
    ram: "128GB",
    biosSerial: "VMWARE-564D29",
    lastLogin: "02:14 AM",
    currentWebsite: "-",
    alertStatus: "critical",
    location: "Ashburn Virginia DC-3, Rack 12",
    lastReflash: "2026-06-10",
    cpuModel: "Intel Xeon Scalable 64-Core",
    complianceStatus: false,
    history: [
      "Critical query throughput limit exceeded.",
      "Active query CPU saturation reached 98% [Potential DoS].",
      "No unauthorized USB or component swap detected."
    ]
  },
  {
    hostname: "MOB-MKT-004",
    status: "Offline",
    employee: "Elena Costa",
    ipAddress: "Unassigned",
    os: "Android 14",
    ram: "8GB",
    biosSerial: "IMEI-84920184",
    lastLogin: "Oct 12",
    currentWebsite: "-",
    alertStatus: "nominal",
    location: "Remote (Sao Paulo, BR)",
    lastReflash: "2026-04-18",
    cpuModel: "Snapdragon 8 Gen 2",
    complianceStatus: true,
    history: [
      "Asset marked as offline due to vacation policy.",
      "Sub-keys verified under remote quarantine policy.",
      "Secure enclave locked down."
    ]
  },
  {
    hostname: "LPT-DES-1102",
    status: "Online",
    employee: "David Kim",
    ipAddress: "10.14.23.42",
    os: "macOS 14.1",
    ram: "64GB",
    biosSerial: "C02GJ8M4P3L1",
    lastLogin: "09:05 AM",
    currentWebsite: "figma.com/file/asset-sentinel",
    alertStatus: "nominal",
    location: "Cupertino HQ, Floor 2",
    lastReflash: "2026-06-08",
    cpuModel: "Apple M2 Max",
    complianceStatus: true,
    history: [
      "RAM module signature fully intact.",
      "No anomalies logged in external kernel modules.",
      "BIOS is certified by Apple Trust Gateway."
    ]
  },
  {
    hostname: "SRV-AUTH-09",
    status: "Online",
    employee: "Active Directory Sync",
    ipAddress: "10.0.1.22",
    os: "RedHat Enterprise 9",
    ram: "256GB",
    biosSerial: "RH-SECURE-99A0",
    lastLogin: "Continuous",
    currentWebsite: "-",
    alertStatus: "nominal",
    location: "Frankfurt DC-1, Server Cage B",
    lastReflash: "2026-06-11",
    cpuModel: "AMD EPYC 9654",
    complianceStatus: true,
    history: [
      "Kerberos session validation loop: 1.2M keys checked.",
      "Root key verification succeeded under compliance check.",
      "ECC Memory correction reports 0 errors in 48 hours."
    ]
  },
  {
    hostname: "WRK-HR-0032",
    status: "Online",
    employee: "Linda Vance",
    ipAddress: "10.12.33.19",
    os: "Win 11 Home",
    ram: "16GB",
    biosSerial: "PF2209A34",
    lastLogin: "01:22 PM",
    currentWebsite: "workday.com/feed",
    alertStatus: "nominal",
    location: "Chicago Regional Office",
    lastReflash: "2026-05-20",
    cpuModel: "Intel Core i5-12400",
    complianceStatus: true,
    history: [
      "BIOS version confirmed within HR security policies.",
      "External device whitelisting: No unauthorized storage."
    ]
  },
  {
    hostname: "LPT-SAL-9821",
    status: "Offline",
    employee: "Tony Stark",
    ipAddress: "10.14.50.12",
    os: "macOS 14.0",
    ram: "16GB",
    biosSerial: "C02HW781A0",
    lastLogin: "Last Week",
    currentWebsite: "zoom.us/meeting/join",
    alertStatus: "warning",
    location: "Remote (Malibu, CA)",
    lastReflash: "2026-01-10",
    cpuModel: "Apple M1 Ultra",
    complianceStatus: false,
    history: [
      "Vulnerability scan flag: Legacy SSH open server on port 22.",
      "Recommendation: Apply macOS update patch and rotate admin credentials."
    ]
  },
  {
    hostname: "SRV-WEB-EDGE-02",
    status: "Online",
    employee: "Cloudflare proxy",
    ipAddress: "10.0.5.1",
    os: "FreeBSD 14",
    ram: "64GB",
    biosSerial: "CDN-EDGE-FREEBSD-99",
    lastLogin: "Continuous",
    currentWebsite: "-",
    alertStatus: "nominal",
    location: "Tokyo Edge Location",
    lastReflash: "2026-05-30",
    cpuModel: "Intel Xeon-E 8-Core",
    complianceStatus: true,
    history: [
      "Nominal traffic flow routed safely.",
      "Zero malicious payloads detected in network buffer."
    ]
  }
];

export const CORE_TELEMETRY_PROTOCOLS = [
  {
    icon: "Cpu",
    title: "Hardware Detection",
    description: "Instant telemetry alerts on memory module swaps or physical hardware chassis modifications."
  },
  {
    icon: "HardDrive",
    title: "RAM Monitoring",
    description: "Continuous real-time tracking of memory module signatures, capacities, and voltage thresholds."
  },
  {
    icon: "Layers",
    title: "Motherboard Tracking",
    description: "Cryptographically bound motherboard identity checks that prevent system-level board spoofing."
  },
  {
    icon: "ShieldAlert",
    title: "BIOS Tracking",
    description: "Rigorous firmware audits and unauthorized flash/re-flash counter monitoring protocols."
  },
  {
    icon: "Globe",
    title: "Restricted Sites",
    description: "Real-time DNS-level firewalls monitoring lateral network routes to prohibited external IPs."
  },
  {
    icon: "BellRing",
    title: "Real-Time Alerts",
    description: "Instant sub-second pushes for critical telemetry alerts, triggered instantly on anomaly events."
  },
  {
    icon: "Sliders",
    title: "Central Dashboard",
    description: "Synthesized single-pane terminal managing entire decentralized corporate hardware fleets."
  }
];

export const STREAMING_FEED_PRESETS: SecurityFeedItem[] = [
  { timestamp: "08:14:10", node: "NODE-4912", message: "RAM Signature Verified (32GB Apple M3)", type: "info" },
  { timestamp: "08:14:22", node: "NODE-8821", message: "ALERT: Unauthorized USB physical entry on Port 0", type: "critical" },
  { timestamp: "08:14:45", node: "SRV-DELTA", message: "Motherboard hardware certified by Apple Trust", type: "info" },
  { timestamp: "08:15:10", node: "FIREWALL", message: "RESTRICTED ACCESS BLOCKED - Source IP: 10.14.22.88", type: "critical" },
  { timestamp: "08:15:55", node: "GATEWAY", message: "NEW SESSION INITIATED - ADMIN-DASHBOARD (Cupertino, CA)", type: "info" },
  { timestamp: "08:16:02", node: "SRV-DB-01", message: "BIOS Intact & MD5 verification passed", type: "info" },
  { timestamp: "08:16:30", node: "NODE-7714", message: "RAM CAPACITY CHANGE DETECTED - (EXPECTED: 64GB | FOUND: 32GB)", type: "warning" },
  { timestamp: "08:17:02", node: "NET-MONITOR", message: "DNS lookup flagged under strict security guidelines", type: "warning" },
  { timestamp: "08:17:45", node: "INVENTORY-SYS", message: "New device signature registered: iMac-24 M4 core", type: "info" }
];

import { Asset, SecurityFeedItem } from "./types";

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

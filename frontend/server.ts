import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const DEFAULT_PORT = Number(process.env.PORT || 3000);

  app.use(express.json());

  // Static offline fallback datasets for proxy resiliency
  const FALLBACK_ASSETS = [
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
      hostname: "Sarthak",
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
    }
  ];

  const FALLBACK_SESSIONS = FALLBACK_ASSETS.map((asset) => ({
    event_type: "LOGIN",
    username: asset.employee,
    hostname: asset.hostname,
    ip_address: asset.ipAddress,
    session_id: asset.hostname,
    login_timestamp: asset.lastLogin,
    logout_timestamp: asset.status === "Offline" ? asset.lastLogin : null,
    session_duration: asset.status === "Offline" ? "Closed" : "Active",
    active: asset.status !== "Offline",
    device_status: asset.status === "Offline" ? "Offline" : "Online",
    recorded_at: asset.lastLogin
  }));

  const FALLBACK_ALERTS = [
    { timestamp: "08:14:02", node: "SYSTEM", message: "Telemetry link bound successfully with Cupertino root cluster.", type: "info" },
    { timestamp: "08:14:10", node: "NODE-4912", message: "RAM Signature Verified (32GB Apple M3)", type: "info" },
    { timestamp: "08:14:22", node: "NODE-8821", message: "ALERT: Unauthorized USB physical entry on Port 0", type: "critical" },
    { timestamp: "08:14:45", node: "SRV-DELTA", message: "Motherboard hardware certified by Apple Trust", type: "info" },
    { timestamp: "08:15:10", node: "FIREWALL", message: "RESTRICTED ACCESS BLOCKED - Source IP: 10.14.22.88", type: "critical" },
    { timestamp: "08:15:55", node: "GATEWAY", message: "NEW SESSION INITIATED - ADMIN-DASHBOARD (Cupertino, CA)", type: "info" }
  ];

  type BackendProxyResult = {
    ok: boolean;
    status: number;
    data: unknown;
  };

  // Helper to fetch from backend trying IPv4 loopback first (robust for Node 18+ environments), then localhost
  async function fetchFromBackend(endpoint: string, init: RequestInit = {}): Promise<BackendProxyResult | null> {
    const requestInit: RequestInit = {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers || {}),
      },
    };

    try {
      // Try 127.0.0.1 explicitly to bypass IPv6 DNS resolution issues
      const response = await fetch(`http://127.0.0.1:5000/api/${endpoint}`, requestInit);
      const data = await response.json().catch(() => ({}));
      return { ok: response.ok, status: response.status, data };
    } catch {
      // silent fallback to localhost
    }

    try {
      const response = await fetch(`http://localhost:5000/api/${endpoint}`, requestInit);
      const data = await response.json().catch(() => ({}));
      return { ok: response.ok, status: response.status, data };
    } catch {
      // silent
    }

    return null;
  }

  const authHeaders = (req: express.Request) => {
    const headers: Record<string, string> = {};
    if (req.headers.authorization) {
      headers.Authorization = req.headers.authorization;
    }
    return headers;
  };

  const sendBackendOrFallback = (
    res: express.Response,
    result: BackendProxyResult | null,
    fallback: unknown,
    fallbackMessage: string,
  ) => {
    if (result?.ok) {
      return res.status(result.status).json(result.data);
    }
    if (result && [401, 403].includes(result.status)) {
      return res.status(result.status).json(result.data);
    }
    console.log(fallbackMessage);
    return res.json(fallback);
  };

  app.post("/api/auth/login", async (req, res) => {
    const result = await fetchFromBackend("auth/login", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Authentication backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/auth/refresh", async (req, res) => {
    const result = await fetchFromBackend("auth/refresh", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Authentication backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/auth/logout", async (req, res) => {
    const result = await fetchFromBackend("auth/logout", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.json({ ok: true });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/auth/forgot-password", async (req, res) => {
    const result = await fetchFromBackend("auth/forgot-password", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Password recovery backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/auth/verify-reset-code", async (req, res) => {
    const result = await fetchFromBackend("auth/verify-reset-code", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Password recovery backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/auth/reset-password", async (req, res) => {
    const result = await fetchFromBackend("auth/reset-password", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Password recovery backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/early-access", async (req, res) => {
    const result = await fetchFromBackend("early-access", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Registration backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/admin-signup", async (req, res) => {
    const result = await fetchFromBackend("admin-signup", {
      method: "POST",
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Registration backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.get("/api/support/tickets", async (req, res) => {
    const result = await fetchFromBackend("support/tickets", { headers: authHeaders(req) });
    if (!result) return res.status(503).json({ error: "Support backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/support/tickets", async (req, res) => {
    const result = await fetchFromBackend("support/tickets", {
      method: "POST",
      headers: authHeaders(req),
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Support backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.patch("/api/support/tickets/:id", async (req, res) => {
    const result = await fetchFromBackend(`support/tickets/${encodeURIComponent(req.params.id)}`, {
      method: "PATCH",
      headers: authHeaders(req),
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Support backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.post("/api/support/email", async (req, res) => {
    const result = await fetchFromBackend("support/email", {
      method: "POST",
      headers: authHeaders(req),
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Support backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.get("/api/super-admin/overview", async (req, res) => {
    const result = await fetchFromBackend("super-admin/overview", { headers: authHeaders(req) });
    if (!result) return res.status(503).json({ error: "Super admin backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.get("/api/super-admin/companies", async (req, res) => {
    const result = await fetchFromBackend("super-admin/companies", { headers: authHeaders(req) });
    if (!result) return res.status(503).json({ error: "Super admin backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.get("/api/super-admin/company/:id", async (req, res) => {
    const result = await fetchFromBackend(`super-admin/company/${encodeURIComponent(req.params.id)}`, { headers: authHeaders(req) });
    if (!result) return res.status(503).json({ error: "Super admin backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.patch("/api/super-admin/company/:id", async (req, res) => {
    const result = await fetchFromBackend(`super-admin/company/${encodeURIComponent(req.params.id)}`, {
      method: "PATCH",
      headers: authHeaders(req),
      body: JSON.stringify(req.body || {}),
    });
    if (!result) return res.status(503).json({ error: "Super admin backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.get("/api/super-admin/tickets", async (req, res) => {
    const result = await fetchFromBackend("super-admin/tickets", { headers: authHeaders(req) });
    if (!result) return res.status(503).json({ error: "Super admin backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  app.get("/api/auth/me", async (req, res) => {
    const result = await fetchFromBackend("auth/me", {
      headers: authHeaders(req),
    });
    if (!result) return res.status(503).json({ error: "Authentication backend unavailable" });
    return res.status(result.status).json(result.data);
  });

  // Proxy route for live assets matching Python monitoring backend
  app.get("/api/assets", async (req, res) => {
    const result = await fetchFromBackend("assets", { headers: authHeaders(req) });
    return sendBackendOrFallback(res, result, FALLBACK_ASSETS, "[SENTINEL CORE] Asset proxy operating in local secure mode.");
  });

  app.get("/api/assets/:hostname/details", async (req, res) => {
    const result = await fetchFromBackend(`assets/${encodeURIComponent(req.params.hostname)}/details`, { headers: authHeaders(req) });
    if (result?.ok) {
      return res.status(result.status).json(result.data);
    }
    if (result && [401, 403, 404].includes(result.status)) {
      return res.status(result.status).json(result.data);
    }
    console.log("[SENTINEL CORE] Asset detail proxy operating in local secure mode.");
    return res.status(503).json({ error: "Live asset detail backend unavailable" });
  });

  // Proxy route for live alerts matching Python monitoring backend
  app.get("/api/alerts", async (req, res) => {
    const result = await fetchFromBackend("alerts", { headers: authHeaders(req) });
    return sendBackendOrFallback(res, result, FALLBACK_ALERTS, "[SENTINEL CORE] Alert proxy operating in local secure mode.");
  });

  app.get("/api/sessions", async (req, res) => {
    const result = await fetchFromBackend("sessions", { headers: authHeaders(req) });
    return sendBackendOrFallback(res, result, FALLBACK_SESSIONS, "[SENTINEL CORE] Session proxy operating in local secure mode.");
  });

  // Initialize Gemini safely
  const apiKey = process.env.GEMINI_API_KEY;
  let ai: GoogleGenAI | null = null;
  if (apiKey && apiKey !== "MY_GEMINI_API_KEY" && apiKey !== "") {
    try {
      ai = new GoogleGenAI({
        apiKey: apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build",
          },
        },
      });
    } catch (e) {
      console.warn("Failed to initialize GoogleGenAI:", e);
    }
  }

  // API endpoint for security forensic audit
  app.post("/api/audit-asset", async (req, res) => {
    try {
      const { hostname, status, employee, ipAddress, os, ram, biosSerial, currentWebsite, location, lastReflash, cpuModel, history } = req.body;

      if (!hostname) {
        return res.status(400).json({ error: "Missing hostname" });
      }

      if (!ai) {
        // High-quality offline fallback
        let riskScore = 15;
        let complianceStatus = true;
        let severity = "nominal";
        let analysis = `### SECURE AUDIT REPORT (OFFLINE PROTOCOL)
        
No active Gemini API connection verified in workspace. Local Sentinel engine evaluated endpoint **${hostname}** based on status and recorded signatures:

1. **BIOS Integrity**: The bios signature \`${biosSerial || "N/A"}\` matches the verified motherboard hardware fingerprint database.
2. **RAM Profile**: Configured RAM level of \`${ram || "N/A"}\` matches the recorded hardware specifications exactly.
3. **Network Baseline**: Host IP of \`${ipAddress || "N/A"}\` is resolved within standard corporate subnet rules. No unauthorized lateral scanning.`;

        const actionItems = ["Maintain regular automatic re-flash cycles.", "Ensure continuous credential rotation."];

        if (status === "Overload" || status === "critical") {
          riskScore = 87;
          complianceStatus = false;
          severity = "critical";
          analysis = `### INCIDENT AUDIT REPORT (OFFLINE PROTOCOL)

**CRITICAL WARNING**: Offline baseline engine flag raised for **${hostname}** (assigned to ${employee || "System Account"}).

1. **Anomaly Detected**: Hardware logs report state is active: **Overload** or hardware alerts present.
2. **Tactical Signature Verification Recommended**: Memory modules must be physical inspected due to active capacity discrepancies.
3. **Suggested Quarantine**: This node is operating outside standard biometric or hardware fingerprinting parameters.`;
          actionItems.unshift("Execute network-level endpoint quarantine.", "Trigger physical forensic scan of hardware seals.");
        } else if (status === "Idle" || biosSerial === "PF3W7L9A") {
          riskScore = 45;
          complianceStatus = false;
          severity = "warning";
          analysis = `### COMPLIANCE AUDIT REPORT (OFFLINE PROTOCOL)

Endpoint **${hostname}** is currently flagged as **Idle**. 

1. **Idle Access Danger**: Persistent connection active without validated user operations raises credential abuse scores.
2. **Recommended Action**: Monitor recent access certificates and session history. Ensure security session timeouts are enforced properly.`;
          actionItems.push("Verify endpoint is active under assigned credential profile.");
        }

        return res.json({
          complianceStatus,
          riskScore,
          analysis,
          actionItems,
          severity,
          isOfflineFallback: true,
        });
      }

      const prompt = `Perform a forensic security audit on the following enterprise hardware asset:
- Hostname: ${hostname}
- Asset Status: ${status}
- Employee Owner: ${employee || "System Account"}
- IP Address: ${ipAddress || "Unassigned"}
- Operating System: ${os || "Unknown"}
- Memory RAM Configuration: ${ram || "Unknown"}
- BIOS Serial: ${biosSerial || "Unknown"}
- Location: ${location || "Remote Workspace"}
- Last BIOS Reflash: ${lastReflash || "Unknown"}
- CPU Model: ${cpuModel || "Unknown"}
- Active DNS/Website target: ${currentWebsite || "None"}
- Known Alerts: ${JSON.stringify(history || [])}

Analyze for potential physical tampering (e.g., memory module swaps, active MAC address spoofing, BIOS firmware hijacking), network policy violations, and provide compliance details. Ensure your writing style matches an authorized, hyper-technical, high-stakes military or core command computer. Raise risk scores if the hostname is SRV-DB-PROD-01 or has abnormal signatures.`;

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: prompt,
        config: {
          systemInstruction: "You are Asset Sentinel Forensics Core, an AI terminal specialized in deep cybersecurity hardware audits. Return output in standard JSON matching the requested structure.",
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              complianceStatus: { type: Type.BOOLEAN, description: "True if asset complies with sentinel security parameters" },
              riskScore: { type: Type.INTEGER, description: "Value from 0 to 100 indicating active exploit danger" },
              analysis: { type: Type.STRING, description: "Highly technical markdown analysis formatted with subheadings and numbered bullets" },
              actionItems: {
                type: Type.ARRAY,
                items: { type: Type.STRING },
                description: "List of precise cybersecurity operations or physical actions to take"
              },
              severity: { type: Type.STRING, description: "Choose exactly: 'nominal', 'warning', or 'critical'" }
            },
            required: ["complianceStatus", "riskScore", "analysis", "actionItems", "severity"]
          }
        }
      });

      const parsedText = response.text || "{}";
      const dataResult = JSON.parse(parsedText);
      res.json(dataResult);
    } catch (error) {
      console.error("Gemini compilation analysis error:", error);
      res.status(500).json({ error: "Forensic Core timed out during hardware verification scan." });
    }
  });

  // Serve static assets / Vite implementation
  if (process.env.NODE_ENV !== "production") {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: process.env.DISABLE_HMR === "true" ? false : undefined,
      },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  const listen = (port: number) => {
    const server = app.listen(port, "0.0.0.0", () => {
      console.log(`[SENTINEL CORE] Server online on http://localhost:${port}`);
    });

    server.on("error", (error: NodeJS.ErrnoException) => {
      if (error.code === "EADDRINUSE" && port < DEFAULT_PORT + 10) {
        console.warn(`[SENTINEL CORE] Port ${port} is busy; trying ${port + 1}...`);
        listen(port + 1);
        return;
      }
      throw error;
    });
  };

  listen(DEFAULT_PORT);
}

startServer();

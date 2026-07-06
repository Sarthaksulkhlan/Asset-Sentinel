import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Building2, CheckCircle2, CircleDot, LifeBuoy, LogOut, Monitor, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { apiFetch } from "../lib/api";

type Overview = {
  totalCompanies: number;
  activeCompanies: number;
  totalDevices: number;
  onlineDevices: number;
  offlineDevices: number;
  criticalAlerts: number;
  openSupportTickets: number;
  platformHealth: string;
};

type CompanyRow = {
  id: number;
  name: string;
  companyAdmin?: string;
  adminEmail?: string;
  registrationDate?: string;
  plan: string;
  totalDevices: number;
  onlineDevices: number;
  criticalAlerts: number;
  status: string;
};

type TicketRow = {
  id: number;
  ticketNumber: string;
  companyName?: string;
  title: string;
  category: string;
  priority: string;
  status: string;
  adminResponse?: string;
  createdAt?: string;
};

export default function SuperAdminDashboard({ onSignOut }: { onSignOut: () => void }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [companies, setCompanies] = useState<CompanyRow[]>([]);
  const [tickets, setTickets] = useState<TicketRow[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [overviewRes, companiesRes, ticketsRes] = await Promise.all([
        apiFetch("/api/super-admin/overview"),
        apiFetch("/api/super-admin/companies"),
        apiFetch("/api/super-admin/tickets"),
      ]);
      if (!overviewRes.ok || !companiesRes.ok || !ticketsRes.ok) throw new Error("Unable to load command center.");
      setOverview(await overviewRes.json());
      setCompanies((await companiesRes.json()).companies || []);
      setTickets((await ticketsRes.json()).tickets || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load command center.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const cards = useMemo(() => {
    const data = overview || {
      totalCompanies: 0,
      activeCompanies: 0,
      totalDevices: 0,
      onlineDevices: 0,
      offlineDevices: 0,
      criticalAlerts: 0,
      openSupportTickets: 0,
      platformHealth: "Loading",
    };
    return [
      { label: "Total Companies", value: data.totalCompanies, icon: Building2 },
      { label: "Active Companies", value: data.activeCompanies, icon: CheckCircle2 },
      { label: "Total Devices", value: data.totalDevices, icon: Monitor },
      { label: "Online Devices", value: data.onlineDevices, icon: CircleDot },
      { label: "Offline Devices", value: data.offlineDevices, icon: XCircle },
      { label: "Critical Alerts", value: data.criticalAlerts, icon: AlertTriangle },
      { label: "Open Tickets", value: data.openSupportTickets, icon: LifeBuoy },
      { label: "Platform Health", value: data.platformHealth, icon: ShieldCheck },
    ];
  }, [overview]);

  const setCompanyStatus = async (companyId: number, status: "Active" | "Suspended") => {
    const response = await apiFetch(`/api/super-admin/company/${companyId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    if (response.ok) loadData();
  };

  const viewCompany = async (companyId: number) => {
    const response = await apiFetch(`/api/super-admin/company/${companyId}`);
    if (response.ok) setSelectedCompany(await response.json());
  };

  const updateTicket = async (ticketId: number, status: string) => {
    const response = await apiFetch(`/api/support/tickets/${ticketId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    if (response.ok) loadData();
  };

  return (
    <div className="min-h-screen bg-[#071017] text-[#dae3ee]">
      <header className="border-b border-white/10 bg-[#0b141c]/95 px-5 py-4">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-[#00d1ff]">Asset Sentinel</p>
            <h1 className="mt-1 text-2xl font-black text-white">Command Center</h1>
          </div>
          <div className="flex gap-2">
            <button onClick={loadData} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs font-bold text-[#a4e6ff]">
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
            <button onClick={onSignOut} className="inline-flex items-center gap-2 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs font-bold text-red-200">
              <LogOut className="h-4 w-4" /> Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-5 px-5 py-6">
        {error && <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-lg border border-white/10 bg-[#0e1822] p-4 shadow-[0_18px_60px_rgba(0,0,0,0.25)]">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#8fa3ad]">{label}</span>
                <Icon className="h-4 w-4 text-[#00d1ff]" />
              </div>
              <p className="mt-3 text-2xl font-black text-white">{String(value)}</p>
            </div>
          ))}
        </section>

        <section className="rounded-lg border border-white/10 bg-[#0e1822]">
          <div className="border-b border-white/10 px-4 py-3">
            <h2 className="text-sm font-black uppercase tracking-widest text-white">Company Management</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-white/[0.03] text-[10px] uppercase tracking-widest text-[#8fa3ad]">
                <tr>
                  {["Company", "Admin", "Registered", "Plan", "Devices", "Online", "Critical", "Status", "Actions"].map((head) => (
                    <th key={head} className="px-4 py-3 font-bold">{head}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {companies.map((company) => (
                  <tr key={company.id} className="border-t border-white/10">
                    <td className="px-4 py-3 font-bold text-white">{company.name}</td>
                    <td className="px-4 py-3 text-[#bbc9cf]">{company.companyAdmin || company.adminEmail || "Unassigned"}</td>
                    <td className="px-4 py-3 text-[#8fa3ad]">{company.registrationDate ? new Date(company.registrationDate).toLocaleDateString() : "-"}</td>
                    <td className="px-4 py-3">{company.plan}</td>
                    <td className="px-4 py-3">{company.totalDevices}</td>
                    <td className="px-4 py-3 text-emerald-300">{company.onlineDevices}</td>
                    <td className="px-4 py-3 text-red-300">{company.criticalAlerts}</td>
                    <td className="px-4 py-3">{company.status}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button onClick={() => viewCompany(company.id)} className="rounded-md border border-[#00d1ff]/30 px-2 py-1 text-xs text-[#a4e6ff]">View</button>
                        <button onClick={() => setCompanyStatus(company.id, "Active")} className="rounded-md border border-emerald-400/30 px-2 py-1 text-xs text-emerald-200">Activate</button>
                        <button onClick={() => setCompanyStatus(company.id, "Suspended")} className="rounded-md border border-amber-400/30 px-2 py-1 text-xs text-amber-200">Suspend</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && companies.length === 0 && (
                  <tr><td className="px-4 py-8 text-center text-[#8fa3ad]" colSpan={9}>No companies enrolled yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-[#0e1822]">
          <div className="border-b border-white/10 px-4 py-3">
            <h2 className="text-sm font-black uppercase tracking-widest text-white">Support Tickets</h2>
          </div>
          <div className="grid gap-3 p-4">
            {tickets.map((ticket) => (
              <div key={ticket.id} className="rounded-lg border border-white/10 bg-[#071017] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-[10px] text-[#00d1ff]">{ticket.ticketNumber} • {ticket.companyName || "Unassigned"}</p>
                    <h3 className="mt-1 font-bold text-white">{ticket.title}</h3>
                    <p className="mt-1 text-xs text-[#8fa3ad]">{ticket.category} • {ticket.priority}</p>
                  </div>
                  <select value={ticket.status} onChange={(event) => updateTicket(ticket.id, event.target.value)} className="rounded-lg border border-white/10 bg-[#0e1822] px-3 py-2 text-xs text-white">
                    {["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"].map((status) => <option key={status}>{status}</option>)}
                  </select>
                </div>
              </div>
            ))}
            {!loading && tickets.length === 0 && <p className="py-6 text-center text-sm text-[#8fa3ad]">No support tickets yet.</p>}
          </div>
        </section>
      </main>

      {selectedCompany && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-[#00d1ff]/25 bg-[#0e1822] p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-[#00d1ff]">Company Details</p>
                <h2 className="mt-1 text-xl font-black text-white">{selectedCompany.company?.name}</h2>
              </div>
              <button onClick={() => setSelectedCompany(null)} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-[#bbc9cf]">Close</button>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <DetailBlock title="Overview" rows={selectedCompany.company} />
              <DetailBlock title="Users/Admins" rows={{ count: selectedCompany.users?.length || 0 }} />
              <DetailBlock title="Devices" rows={{ count: selectedCompany.devices?.length || 0 }} />
              <DetailBlock title="Alerts" rows={{ count: selectedCompany.alerts?.length || 0 }} />
              <DetailBlock title="Support Tickets" rows={{ count: selectedCompany.tickets?.length || 0 }} />
              <DetailBlock title="Last Activity" rows={{ latestDevice: selectedCompany.devices?.[0]?.lastSeen || "No activity" }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailBlock({ title, rows }: { title: string; rows: Record<string, any> }) {
  return (
    <div className="rounded-lg border border-white/10 bg-[#071017] p-4">
      <h3 className="text-xs font-black uppercase tracking-widest text-white">{title}</h3>
      <div className="mt-3 grid gap-2 text-xs text-[#bbc9cf]">
        {Object.entries(rows || {}).slice(0, 6).map(([key, value]) => (
          <div key={key} className="flex justify-between gap-3 border-b border-white/5 pb-2">
            <span className="capitalize text-[#8fa3ad]">{key.replace(/([A-Z])/g, " $1")}</span>
            <span className="text-right text-white">{String(value ?? "-")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

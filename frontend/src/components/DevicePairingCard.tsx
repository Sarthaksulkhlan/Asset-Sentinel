import React, { useEffect, useState } from "react";
import { Check, Copy, KeyRound, RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";

type PairingCode = {
  code: string | null;
  createdAt: string | null;
  expiresAt: string | null;
  used: boolean;
};

const EMPTY_PAIRING_CODE: PairingCode = {
  code: null,
  createdAt: null,
  expiresAt: null,
  used: false,
};

const formatExpiry = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value || "";
  return `${part("day")} ${part("month")} ${part("year")} \u2022 ${part("hour")}:${part("minute")} ${part("dayPeriod").toUpperCase()}`;
};

const copyText = async (value: string) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const input = document.createElement("textarea");
  input.value = value;
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  document.body.removeChild(input);
};

export default function DevicePairingCard() {
  const [pairingCode, setPairingCode] = useState<PairingCode>(EMPTY_PAIRING_CODE);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiFetch("/api/device-pairing/code")
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Unable to load pairing code.");
        if (active) setPairingCode({ ...EMPTY_PAIRING_CODE, ...payload });
      })
      .catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load pairing code.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const generateCode = async () => {
    setGenerating(true);
    setCopied(false);
    setError("");
    try {
      const response = await apiFetch("/api/device-pairing/code", { method: "POST" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || "Unable to generate a pairing code.");
      setPairingCode({ ...EMPTY_PAIRING_CODE, ...payload });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to generate a pairing code.");
    } finally {
      setGenerating(false);
    }
  };

  const copyCode = async () => {
    if (!pairingCode.code) return;
    try {
      await copyText(pairingCode.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Unable to copy the pairing code. Please select it manually.");
    }
  };

  return (
    <section className="w-full max-w-2xl rounded-lg border border-[#2B3752] bg-[#141B2D] shadow-[0_18px_50px_rgba(0,0,0,0.26)]">
      <div className="flex items-center gap-3 border-b border-[#2B3752] px-5 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#38BDF8]/25 bg-[#38BDF8]/10">
          <KeyRound className="h-4 w-4 text-[#38BDF8]" />
        </div>
        <div className="min-w-0">
          <h2 className="text-base font-bold text-white">Device Pairing</h2>
          <p className="mt-0.5 text-xs text-[#8EA0B8]">Pair a Windows Agent with this account.</p>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        {loading ? (
          <div className="flex min-h-32 items-center justify-center text-sm text-[#8EA0B8]">
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> Loading pairing code...
          </div>
        ) : pairingCode.code ? (
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#8EA0B8]">Current Pairing Code</p>
            <div className="mt-3 rounded-lg border border-[#38BDF8]/25 bg-[#0B1220] px-4 py-5 text-center font-mono text-4xl font-bold tracking-[0.28em] text-white sm:text-5xl">
              {pairingCode.code}
            </div>
            {pairingCode.expiresAt && (
              <div className="mt-4 text-sm text-[#A8B3C7]">
                <span className="block text-xs text-[#8EA0B8]">Valid until</span>
                <span className="mt-1 block font-semibold text-white">{formatExpiry(pairingCode.expiresAt)}</span>
              </div>
            )}
            <button
              type="button"
              onClick={copyCode}
              className="mt-5 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-[#00d1ff] px-4 py-2.5 text-sm font-bold text-[#003543] transition-colors hover:bg-cyan-300 sm:w-auto"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copied" : "Copy Pairing Code"}
            </button>
          </div>
        ) : (
          <p className="py-5 text-sm text-[#A8B3C7]">No active pairing code.</p>
        )}

        {error && <p role="alert" className="mt-4 text-sm text-red-300">{error}</p>}

        <div className="mt-6 border-t border-[#2B3752] pt-5">
          <button
            type="button"
            onClick={generateCode}
            disabled={loading || generating}
            className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-[#38BDF8]/35 bg-[#38BDF8]/10 px-4 py-2.5 text-sm font-bold text-[#A4E6FF] transition-colors hover:bg-[#38BDF8]/15 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
          >
            <RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />
            {generating ? "Generating..." : "Generate New Pairing Code"}
          </button>
        </div>
      </div>
    </section>
  );
}

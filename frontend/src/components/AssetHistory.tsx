import React, { useMemo } from "react";
import { Asset, SecurityFeedItem } from "../types";

interface AssetHistoryProps {
  assets: Asset[];
  liveLogs: SecurityFeedItem[];
  onClose: () => void;
}

const severityClass = (type: string) => {
  if (type === "critical") return "text-[#f87171] bg-[#3b0f12]/30";
  if (type === "warning") return "text-[#fbbf24] bg-[#3b2100]/20";
  return "text-[#60a5fa] bg-[#08202b]/20";
};

const extractRamChange = (msg: string) => {
  const re = /([0-9]+\s?GB)/ig;
  const m = Array.from(msg.matchAll(re)).map(r => r[1]);
  return { oldVal: m[0] ?? null, newVal: m[1] ?? null };
};

const extractBoardChange = (msg: string) => {
  const re = /([A-F0-9]{6,})/ig;
  const m = Array.from(msg.matchAll(re)).map(r => r[1]);
  return { oldVal: m[0] ?? null, newVal: m[1] ?? null };
};

export default function AssetHistory({ assets, liveLogs, onClose }: AssetHistoryProps) {
  const timeline = useMemo(() => {
    return [...liveLogs].slice().reverse(); // most recent first
  }, [liveLogs]);

  return (
    <div className="w-full max-w-4xl max-h-[calc(100vh-1.5rem)] md:max-h-[calc(100vh-8rem)] overflow-y-auto bg-[#0b1116] p-4 sm:p-6 rounded-2xl text-sm text-[#dbeafe]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-lg font-bold">Asset History</h3>
          <p className="text-xs text-[#94a3b8]">Chronological audit log of hardware and security events.</p>
        </div>
        <div className="text-xs text-[#94a3b8]">Events: {liveLogs.length}</div>
      </div>

      <div className="space-y-3">
        {timeline.length === 0 && (
          <div className="text-[#94a3b8]">No history events available.</div>
        )}

        {timeline.map((ev, idx) => {
          const isRam = /ram[_ ]change/i.test(ev.message);
          const isBoard = /motherboard[_ ]change/i.test(ev.message);
          const ram = isRam ? extractRamChange(ev.message) : null;
          const board = isBoard ? extractBoardChange(ev.message) : null;
          const assetName = ev.node || "Unknown";

          return (
            <div key={idx} className="rounded-xl bg-[#07121a]/60 border border-white/5 p-3 grid grid-cols-1 sm:grid-cols-[120px_1fr] lg:grid-cols-[120px_1fr_110px] gap-3 lg:gap-4 items-start">
              <div className="text-[11px] text-[#94a3b8] uppercase">{ev.timestamp}</div>
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <div className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${severityClass(ev.type)}`}>{ev.type.toUpperCase()}</div>
                  <div className="text-sm font-semibold">{assetName}</div>
                </div>
                <div className="text-[#cbd5e1]">{ev.message}</div>
                {isRam && ram && (
                  <div className="mt-2 text-xs text-[#94a3b8]">
                    <div>Old RAM: <span className="text-white">{ram.oldVal ?? 'N/A'}</span></div>
                    <div>New RAM: <span className="text-white">{ram.newVal ?? 'N/A'}</span></div>
                  </div>
                )}
                {isBoard && board && (
                  <div className="mt-2 text-xs text-[#94a3b8]">
                    <div>Old Board: <span className="text-white">{board.oldVal ?? 'N/A'}</span></div>
                    <div>New Board: <span className="text-white">{board.newVal ?? 'N/A'}</span></div>
                  </div>
                )}
              </div>
              <div className="text-left lg:text-right text-xs text-[#94a3b8] sm:col-start-2 lg:col-start-auto">
                <div>{ev.node}</div>
                <div className="mt-2">Type: <span className="text-white">{ev.message.split(':')[0]}</span></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex justify-end">
        <button onClick={onClose} className="min-h-10 px-4 py-2 bg-[#0b1220] border border-[#23303a] text-[#9fb7c9] rounded-lg">Close</button>
      </div>
    </div>
  );
}

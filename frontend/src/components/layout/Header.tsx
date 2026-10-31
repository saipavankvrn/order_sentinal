import React from 'react';
import { ShieldCheck, RefreshCw, Activity } from 'lucide-react';

interface HeaderProps {
  isPolling: boolean;
  onTogglePolling: () => void;
  onManualRefresh: () => void;
  isRefreshing: boolean;
  systemStatus: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
}

export const Header: React.FC<HeaderProps> = ({
  isPolling,
  onTogglePolling,
  onManualRefresh,
  isRefreshing,
  systemStatus
}) => {
  return (
    <header className="bg-[#0B1120] text-white border-b border-slate-800/80 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center space-x-3.5">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-900/30 ring-1 ring-white/10">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base font-bold tracking-tight text-white">
                  OrderFlow Sentinel
                </span>
                <span className="text-[10px] font-mono font-bold bg-blue-950 text-blue-300 border border-blue-800/60 px-1.5 py-0.5 rounded">
                  v1.2.1
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block font-medium">
                Autonomous Self-Healing & Policy-Governed Order Reliability
              </p>
            </div>
          </div>

          {/* Controls & Status */}
          <div className="flex items-center space-x-3">
            {/* System Status */}
            <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono">
              <span className="relative flex h-2 w-2">
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    systemStatus === 'ONLINE'
                      ? 'bg-emerald-400'
                      : systemStatus === 'DEGRADED'
                      ? 'bg-amber-400'
                      : 'bg-rose-400'
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    systemStatus === 'ONLINE'
                      ? 'bg-emerald-500'
                      : systemStatus === 'DEGRADED'
                      ? 'bg-amber-500'
                      : 'bg-rose-500'
                  }`}
                />
              </span>
              <span className="text-slate-400">Backend:</span>
              <span
                className={`font-bold ${
                  systemStatus === 'ONLINE'
                    ? 'text-emerald-400'
                    : systemStatus === 'DEGRADED'
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }`}
              >
                {systemStatus}
              </span>
            </div>

            {/* Auto-poll status */}
            <button
              onClick={onTogglePolling}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                isPolling
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/80 hover:bg-emerald-900/40'
                  : 'bg-slate-900/90 text-slate-400 border-slate-800 hover:bg-slate-800 text-slate-300'
              }`}
              title={isPolling ? 'Auto-polling active (every 3s)' : 'Auto-polling paused'}
            >
              <Activity className={`w-3.5 h-3.5 ${isPolling ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span className="hidden md:inline font-mono">{isPolling ? 'Auto-Poll: 3s' : 'Polling: Paused'}</span>
            </button>

            {/* Manual Refresh */}
            <button
              onClick={onManualRefresh}
              disabled={isRefreshing}
              className="flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-sm shadow-blue-900/30 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

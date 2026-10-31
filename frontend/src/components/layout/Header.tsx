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
    <header className="bg-[#0F172A] text-white border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-inner">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold tracking-tight text-white">
                  OrderFlow Sentinel
                </span>
                <span className="text-[10px] font-semibold bg-blue-900/60 text-blue-300 border border-blue-700/50 px-1.5 py-0.5 rounded">
                  v1.2.1
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                AI-Powered Self-Healing Order Failure Detection & Resolution
              </p>
            </div>
          </div>

          {/* Controls & Status */}
          <div className="flex items-center space-x-4">
            {/* System Status */}
            <div className="flex items-center space-x-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-md text-xs">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300">Backend:</span>
              <span
                className={`font-semibold ${
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
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                isPolling
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800 hover:bg-emerald-900/40'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700'
              }`}
              title={isPolling ? 'Auto-polling active (every 3s)' : 'Auto-polling paused'}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isPolling ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                }`}
              />
              <span>{isPolling ? 'Auto-Poll: 3s' : 'Polling: Paused'}</span>
            </button>

            {/* Manual Refresh */}
            <button
              onClick={onManualRefresh}
              disabled={isRefreshing}
              className="flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-md text-xs font-medium transition-colors shadow-sm disabled:opacity-50"
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


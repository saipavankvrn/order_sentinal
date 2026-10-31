import React from 'react';
import { LayoutDashboard, GitFork, ShieldAlert, Sparkles } from 'lucide-react';

export type ActiveTab = 'dashboard' | 'journey' | 'approvals' | 'live-demo';

interface NavigationProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  pendingApprovalsCount: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onTabChange,
  pendingApprovalsCount
}) => {
  const tabs = [
    {
      id: 'live-demo' as ActiveTab,
      label: 'Live Order Demonstration',
      badgeText: 'LIVE DEMO',
      icon: Sparkles,
      isSpecial: true
    },
    {
      id: 'dashboard' as ActiveTab,
      label: 'Dashboard & Monitoring',
      badgeText: 'VIEW A',
      icon: LayoutDashboard
    },
    {
      id: 'journey' as ActiveTab,
      label: 'Order Journey & Incident RCA',
      badgeText: 'VIEW B',
      icon: GitFork
    },
    {
      id: 'approvals' as ActiveTab,
      label: 'Human Approval Queue & Audit',
      badgeText: 'VIEW C',
      icon: ShieldAlert,
      count: pendingApprovalsCount
    }
  ];

  return (
    <div className="bg-white border-b border-slate-200/90 sticky top-16 z-30 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex space-x-1 sm:space-x-3 overflow-x-auto py-2" aria-label="Main Navigation">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`group flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? tab.isSpecial
                      ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20'
                      : 'bg-slate-900 text-white shadow-sm'
                    : tab.isSpecial
                    ? 'text-blue-700 bg-blue-50/70 hover:bg-blue-100/70 border border-blue-200/80 font-bold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
                }`}
              >
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive
                      ? 'text-white'
                      : tab.isSpecial
                      ? 'text-blue-600'
                      : 'text-slate-400 group-hover:text-slate-600'
                  }`}
                />
                <span>{tab.label}</span>

                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                    isActive
                      ? 'bg-white/20 text-white'
                      : tab.isSpecial
                      ? 'bg-blue-200/70 text-blue-900'
                      : 'bg-slate-200/80 text-slate-600'
                  }`}
                >
                  {tab.badgeText}
                </span>

                {tab.count !== undefined && tab.count > 0 && (
                  <span
                    className={`ml-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-tight ${
                      isActive
                        ? 'bg-rose-500 text-white'
                        : 'bg-rose-100 text-rose-700 border border-rose-200'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};

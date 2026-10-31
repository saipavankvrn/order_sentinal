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
      sublabel: 'Demo Mode',
      icon: Sparkles,
      highlight: true
    },
    {
      id: 'dashboard' as ActiveTab,
      label: 'Dashboard & Monitoring',
      sublabel: 'View A',
      icon: LayoutDashboard
    },
    {
      id: 'journey' as ActiveTab,
      label: 'Order Journey & Incident RCA',
      sublabel: 'View B',
      icon: GitFork
    },
    {
      id: 'approvals' as ActiveTab,
      label: 'Human Approval Queue & Audit',
      sublabel: 'View C',
      icon: ShieldAlert,
      badge: pendingApprovalsCount
    }
  ];

  return (
    <div className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex space-x-8" aria-label="Tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-all ${
                  isActive
                    ? 'border-blue-600 text-blue-600 font-semibold'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                <Icon
                  className={`w-4 h-4 mr-2 ${
                    isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-500'
                  }`}
                />
                <span>{tab.label}</span>
                <span
                  className={`ml-1.5 text-[11px] px-1.5 py-0.5 rounded font-mono ${
                    tab.highlight
                      ? isActive
                        ? 'bg-amber-500 text-white font-bold'
                        : 'bg-amber-100 text-amber-800 border border-amber-300 font-bold'
                      : isActive
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {tab.sublabel}
                </span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-rose-600 text-white animate-pulse">
                    {tab.badge}
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


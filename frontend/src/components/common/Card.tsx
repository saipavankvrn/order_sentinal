import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  id?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  action,
  id
}) => {
  return (
    <div
      id={id}
      className={`bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden ${className}`}
    >
      {(title || action) && (
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            {typeof title === 'string' ? (
              <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
            ) : (
              title
            )}
            {subtitle && (
              <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
};


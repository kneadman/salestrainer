import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', hover = true }) => {
  return (
    <div className={`glass-card p-7 ${hover ? '' : 'hover:transform-none hover:shadow-card'} ${className}`}>
      {children}
    </div>
  );
};

export default React.memo(GlassCard);

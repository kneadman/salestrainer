import React from 'react';

interface GhostButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

const GhostButton: React.FC<GhostButtonProps> = ({ children, onClick, className = '' }) => {
  return (
    <button
      onClick={onClick}
      className={`ghost-btn inline-flex items-center justify-center gap-2 text-[15px] ${className}`}
    >
      {children}
    </button>
  );
};

export default React.memo(GhostButton);

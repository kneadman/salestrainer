import React from 'react';

interface GradientButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit';
  fullWidth?: boolean;
}

const GradientButton: React.FC<GradientButtonProps> = ({
  children,
  onClick,
  className = '',
  type = 'button',
  fullWidth = false,
}) => {
  return (
    <button
      type={type}
      onClick={onClick}
      className={`gradient-btn inline-flex items-center justify-center gap-2 text-[15px] ${
        fullWidth ? 'w-full' : ''
      } ${className}`}
    >
      {children}
    </button>
  );
};

export default React.memo(GradientButton);

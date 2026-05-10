import React from 'react';

interface SectionLabelProps {
  text: string;
  centered?: boolean;
}

const SectionLabel: React.FC<SectionLabelProps> = ({ text, centered = false }) => {
  return (
    <span
      className={`section-label block mb-4 ${centered ? 'text-center' : ''}`}
    >
      {text}
    </span>
  );
};

export default React.memo(SectionLabel);

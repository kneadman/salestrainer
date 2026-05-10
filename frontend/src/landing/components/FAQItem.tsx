import React, { useState, useRef } from 'react';

interface FAQItemProps {
  question: string;
  answer: string;
}

const FAQItem: React.FC<FAQItemProps> = ({ question, answer }) => {
  const [isOpen, setIsOpen] = useState(false);
  const answerRef = useRef<HTMLDivElement>(null);

  return (
    <div className="bg-navy-700 rounded-2xl border border-white/[0.04] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-6 text-left transition-colors hover:bg-navy-500/20"
      >
        <span className="font-inter font-medium text-[16px] text-text-primary pr-4">
          {question}
        </span>
        <span
          className="font-mono text-mint text-xl flex-shrink-0 transition-transform duration-300"
          style={{ transform: isOpen ? 'rotate(0deg)' : 'rotate(0deg)' }}
        >
          {isOpen ? '−' : '+'}
        </span>
      </button>
      <div
        ref={answerRef}
        className="overflow-hidden transition-all duration-300 ease-out"
        style={{
          maxHeight: isOpen ? '500px' : '0px',
          opacity: isOpen ? 1 : 0,
        }}
      >
        <div className="px-6 pb-6">
          <p className="font-inter text-[15px] text-text-secondary leading-relaxed pt-2">
            {answer}
          </p>
        </div>
      </div>
    </div>
  );
};

export default React.memo(FAQItem);

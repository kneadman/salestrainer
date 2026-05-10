import React from 'react';
import { ChevronUp } from 'lucide-react';

const currentYear = new Date().getFullYear();

const Footer: React.FC = () => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const scrollTo = (href: string) => {
    document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <footer className="relative bg-navy-900 border-t border-white/[0.04]">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12 items-start">
          {/* Logo & tagline */}
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-lg gradient-accent flex items-center justify-center">
                <span className="font-manrope font-bold text-navy-800 text-sm">R</span>
              </div>
              <span className="font-manrope font-semibold text-text-primary text-[15px]">
                Replikor
              </span>
            </div>
            <p className="font-inter text-[13px] text-text-secondary leading-relaxed max-w-[280px]">
              Тренажёр продаж для пилота, онбординга и разбора качества разговора.
            </p>
          </div>

          {/* Nav links */}
          <div className="flex flex-col sm:flex-row md:flex-col gap-3 md:items-center">
            <button
              onClick={() => scrollTo('#how-it-works')}
              className="font-inter text-[14px] text-text-secondary hover:text-text-primary transition-colors text-left md:text-center"
            >
              Как работает
            </button>
            <button
              onClick={() => scrollTo('#scenarios')}
              className="font-inter text-[14px] text-text-secondary hover:text-text-primary transition-colors text-left md:text-center"
            >
              Сценарии
            </button>
            <button
              onClick={() => scrollTo('#demo')}
              className="font-inter text-[14px] text-text-secondary hover:text-text-primary transition-colors text-left md:text-center"
            >
              Демо
            </button>
          </div>

          {/* Back to top */}
          <div className="flex md:justify-end">
            <button
              onClick={scrollToTop}
              className="w-11 h-11 rounded-full bg-navy-700 border border-white/[0.05] flex items-center justify-center text-text-secondary hover:bg-navy-500 hover:text-text-primary transition-all duration-200"
              aria-label="Наверх"
            >
              <ChevronUp className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/[0.04]">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="font-inter text-[12px] text-text-tertiary text-center sm:text-left">
            © {currentYear} Replikor
          </p>
          <div className="flex items-center gap-4">
            <a href="/privacy" className="font-inter text-[12px] text-text-tertiary hover:text-text-secondary transition-colors">
              Политика конфиденциальности
            </a>
            <a href="/cookies" className="font-inter text-[12px] text-text-tertiary hover:text-text-secondary transition-colors">
              Cookie
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default React.memo(Footer);

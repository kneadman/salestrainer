import React, { useEffect, useState, useCallback } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const navLinks = [
  { label: 'Как работает', href: '#how-it-works' },
  { label: 'Что видно в отчёте', href: '#metrics' },
  { label: 'Для руководителя', href: '#managers' },
  { label: 'Сценарии', href: '#scenarios' },
  { label: 'Пилот', href: '#pilot' },
  { label: 'FAQ', href: '#faq' },
];

interface FixedHeaderProps {
  authenticated: boolean;
  onLoginClick: () => void;
  onDemoClick: () => void;
}

const FixedHeader: React.FC<FixedHeaderProps> = ({ authenticated, onLoginClick, onDemoClick }) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const trigger = ScrollTrigger.create({
      trigger: '#hero',
      start: 'bottom top',
      onEnter: () => setScrolled(true),
      onLeaveBack: () => setScrolled(false),
    });
    return () => trigger.kill();
  }, []);

  const scrollTo = useCallback((href: string) => {
    const el = document.querySelector(href);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
      setMobileOpen(false);
    }
  }, []);

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-[1000] transition-all duration-300 ${
          scrolled ? 'py-3' : 'py-4'
        }`}
        style={{
          background: 'rgba(15, 23, 41, 0.6)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
        }}
      >
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2.5 flex-shrink-0" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
            <div className="w-8 h-8 rounded-lg gradient-accent flex items-center justify-center overflow-hidden">
              <img src="/logo.png" alt="" className="w-full h-full object-cover" aria-hidden="true" />
            </div>
            <div className="flex flex-col">
              <span className="font-manrope font-semibold text-text-primary text-[15px] leading-tight">
                Replikor
              </span>
              <span className="font-inter text-[10px] text-text-tertiary leading-tight hidden sm:block">
                AI-тренажёр продаж
              </span>
            </div>
          </a>

          {/* Desktop Nav */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => scrollTo(link.href)}
                className="font-inter text-[14px] text-text-secondary hover:text-text-primary px-3 py-2 rounded-lg transition-colors duration-200"
              >
                {link.label}
              </button>
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3 flex-shrink-0">
            <button className="ghost-btn !py-2.5 !px-5 !text-[14px]" onClick={onLoginClick}>
              {authenticated ? 'Открыть кабинет' : 'Войти в кабинет'}
            </button>
            <button
              onClick={onDemoClick}
              className="gradient-btn !py-2.5 !px-5 !text-[14px]"
            >
              Попробовать демо
            </button>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="lg:hidden flex flex-col gap-1.5 p-2"
            aria-label="Menu"
          >
            <span className={`block w-5 h-0.5 bg-text-primary transition-all duration-300 ${mobileOpen ? 'rotate-45 translate-y-2' : ''}`} />
            <span className={`block w-5 h-0.5 bg-text-primary transition-all duration-300 ${mobileOpen ? 'opacity-0' : ''}`} />
            <span className={`block w-5 h-0.5 bg-text-primary transition-all duration-300 ${mobileOpen ? '-rotate-45 -translate-y-2' : ''}`} />
          </button>
        </div>
      </header>

      {/* Mobile drawer */}
      <div
        className={`fixed inset-0 z-[999] transition-opacity duration-300 lg:hidden ${
          mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        style={{
          background: 'rgba(15, 23, 41, 0.85)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
        }}
      >
        <div className="flex flex-col items-center justify-center h-full gap-6 pt-16">
          {navLinks.map((link) => (
            <button
              key={link.href}
              onClick={() => scrollTo(link.href)}
              className="font-inter text-[18px] text-text-secondary hover:text-text-primary transition-colors"
            >
              {link.label}
            </button>
          ))}
          <div className="flex flex-col gap-3 mt-4 w-64">
            <button className="ghost-btn w-full" onClick={onLoginClick}>
              {authenticated ? 'Открыть кабинет' : 'Войти в кабинет'}
            </button>
            <button
              onClick={() => { setMobileOpen(false); onDemoClick(); }}
              className="gradient-btn w-full"
            >
              Попробовать демо
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default React.memo(FixedHeader);

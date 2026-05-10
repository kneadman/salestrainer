import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import GradientButton from '@/landing/components/GradientButton';
import GhostButton from '@/landing/components/GhostButton';
import { Check } from 'lucide-react';

const trustSignals = [
  'Без кредитной карты',
  'Настройка за 5 минут',
  '500+ менеджеров уже тренируются',
];

const chatMessages = [
  { type: 'client', text: 'Сейчас у нас всё держится на менеджерах. Чем вы отличаетесь от обычного обучения?' },
  { type: 'manager', text: 'Менеджер проходит живой разговор с тренажёром и получает разбор по конкретным моментам диалога.' },
  { type: 'client', text: 'Если он знает скрипт, этого разве мало?' },
  { type: 'ai', text: 'Выявлена проблема: нет контроля качества разговора в моменте сопротивления клиента.' },
  { type: 'manager', text: 'Скрипт не показывает, как менеджер ведёт себя под давлением. Здесь видно, где он теряет вопрос, боль или следующий шаг.' },
];

interface HeroSectionProps {
  onDemoClick: () => void;
  onMechanicsClick: () => void;
}

const HeroSection: React.FC<HeroSectionProps> = ({ onDemoClick, onMechanicsClick }) => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ delay: 0.3 });

      tl.fromTo('.hero-label', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' })
        .fromTo('.hero-title', { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }, '-=0.3')
        .fromTo('.hero-subtitle', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.4')
        .fromTo('.hero-buttons', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.3')
        .fromTo('.hero-trust', { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }, '-=0.2')
        .fromTo('.hero-chat', { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: 0.8, ease: 'power2.out' }, '-=0.6');
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section id="hero" ref={sectionRef} className="relative min-h-[100dvh] flex items-center overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 z-0">
        <img
          src="/images/hero-bg.jpg"
          alt=""
          className="w-full h-full object-cover scale-105"
          style={{ animation: 'kenburns 20s ease-in-out infinite alternate' }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[rgba(15,23,41,0.5)] via-[rgba(15,23,41,0.65)] to-[#0f1729]" />
      </div>

      {/* Content - 2 columns */}
      <div className="relative z-10 max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 w-full pt-24 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-12 items-center">
          {/* Left - Text */}
          <div className="text-left">
            <span className="hero-label section-label inline-block mb-5">
              AI-ТРЕНАЖЁР ПРОДАЖ
            </span>

            <h1 className="hero-title font-manrope font-bold text-[30px] sm:text-[38px] lg:text-[42px] text-text-primary leading-[1.15] mb-5">
              Тренируйте сложные разговоры до встречи и заранее видьте, где менеджер теряет клиента.
            </h1>

            <p className="hero-subtitle font-inter text-[16px] lg:text-[17px] text-text-secondary leading-relaxed max-w-[520px] mb-8">
              Replikor имитирует живой B2B-диалог, чтобы менеджер отрабатывал сопротивление, вопросы
              и следующий шаг без риска для реальной сделки.
            </p>

            <div className="hero-buttons flex flex-col sm:flex-row gap-4 mb-8">
              <GradientButton onClick={onDemoClick} className="!h-[48px] !px-7">
                Попробовать демо
              </GradientButton>
              <GhostButton onClick={onMechanicsClick} className="!h-[48px] !px-7">
                Посмотреть механику
              </GhostButton>
            </div>

            {/* Trust signals */}
            <div className="hero-trust flex flex-col sm:flex-row gap-3 sm:gap-6">
              {trustSignals.map((signal, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-mint flex-shrink-0" />
                  <span className="font-inter text-[13px] text-text-secondary">{signal}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right - Chat Preview */}
          <div className="hero-chat hidden lg:block">
            <div
              className="rounded-2xl p-5 border border-white/[0.06] shadow-card"
              style={{
                background: 'rgba(19, 29, 50, 0.85)',
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
              }}
            >
              {/* Chat header */}
              <div className="flex items-center gap-2 mb-4 pb-4 border-b border-white/[0.04]">
                <div className="w-2 h-2 rounded-full bg-mint animate-pulse" />
                <span className="font-inter text-[13px] text-text-secondary">Тренировка</span>
                <span className="ml-auto font-inter text-[13px] text-text-primary font-medium">Живой разговор</span>
              </div>

              {/* Messages */}
              <div className="flex flex-col gap-2.5 max-h-[380px] overflow-hidden">
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`max-w-[88%] p-3 rounded-xl text-[13px] leading-relaxed font-inter ${
                      msg.type === 'client'
                        ? 'bg-navy-600 text-text-secondary self-start'
                        : msg.type === 'manager'
                        ? 'bg-gradient-to-r from-mint/15 to-cyan/15 text-text-primary self-end border border-mint/15'
                        : 'bg-navy-500/50 text-mint self-start border border-mint/10'
                    }`}
                  >
                    {msg.text}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 animate-bounce-scroll opacity-40">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-text-secondary">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>

      <style>{`
        @keyframes kenburns {
          0% { transform: scale(1.05) translate(0, 0); }
          100% { transform: scale(1.12) translate(-1%, -1%); }
        }
      `}</style>
    </section>
  );
};

export default React.memo(HeroSection);

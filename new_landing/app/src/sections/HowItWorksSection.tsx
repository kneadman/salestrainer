import React, { useState, useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SectionLabel from '@/components/SectionLabel';

gsap.registerPlugin(ScrollTrigger);

const tabs = [
  {
    id: 'dialog',
    label: 'Разговор',
    messages: [
      { type: 'client', text: 'Сейчас у нас всё держится на менеджерах. Чем вы отличаетесь от обычного обучения?' },
      { type: 'manager', text: 'Менеджер проходит живой разговор с тренажёром и получает разбор по конкретным моментам диалога.' },
      { type: 'client', text: 'Если он знает скрипт, этого разве мало?' },
      { type: 'ai', text: 'Выявлена проблема: нет контроля качества разговора в момент сопротивления клиента.' },
      { type: 'manager', text: 'Скрипт не показывает, как менеджер ведёт себя под давлением. Здесь видно, где он теряет вопрос, боль или следующий шаг.' },
    ],
  },
  {
    id: 'evaluation',
    label: 'Оценка',
    messages: [
      { type: 'ai', text: 'Оценка разговора завершена. Итоговый балл: 72/100' },
      { type: 'ai', text: 'Структура разговора: 86 — хорошо удерживает логику' },
      { type: 'ai', text: 'Выявление боли: 72 — проблема зафиксирована, но не углублена' },
      { type: 'ai', text: 'Работа с возражением: 63 — сомнение снято, но с излишним давлением' },
      { type: 'ai', text: 'Следующий шаг: 58 — договорённость не зафиксирована чётко' },
    ],
  },
  {
    id: 'conclusions',
    label: 'Выводы',
    messages: [
      { type: 'ai', text: 'Что разбирать с командой:' },
      { type: 'ai', text: '1. Менеджер перескакивает в презентацию до выявления боли' },
      { type: 'ai', text: '2. При возражении по цене — давление вместо диалога' },
      { type: 'ai', text: '3. Не фиксирует следующий шаг — сделка без движения' },
      { type: 'ai', text: 'Рекомендация: тренировать удержание логики беседы под давлением' },
    ],
  },
];

const HowItWorksSection: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const sectionRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.hiw-left',
        { opacity: 0, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 80%',
            toggleActions: 'play none none none',
          },
        }
      );

      gsap.fromTo(
        '.hiw-right',
        { opacity: 0, y: 32 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 75%',
            toggleActions: 'play none none none',
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  useEffect(() => {
    if (contentRef.current) {
      gsap.fromTo(
        contentRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.25, ease: 'power2.out' }
      );
    }
  }, [activeTab]);

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800 overflow-hidden"
    >
      {/* Ambient glow */}
      <div
        className="absolute top-0 right-0 w-[600px] h-[600px] pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 70% 30%, rgba(94,234,212,0.04) 0%, transparent 50%)',
        }}
      />

      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 lg:gap-16">
          {/* Left sticky */}
          <div className="hiw-left lg:col-span-2 lg:sticky lg:top-[120px] lg:self-start">
            <SectionLabel text="КАК РАБОТАЕТ" />
            <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
              Сначала разговор, затем оценка и выводы для руководителя.
            </h2>
            <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
              На одном экране видно, как менеджер ведёт диалог, где теряет качество разговора и
              что стоит разбирать дальше.
            </p>
          </div>

          {/* Right — tabs + chat */}
          <div className="hiw-right lg:col-span-3">
            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              {tabs.map((tab, i) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(i)}
                  className={`px-5 py-2.5 rounded-full font-inter text-[14px] font-medium transition-all duration-300 ${
                    i === activeTab
                      ? 'gradient-accent text-navy-800'
                      : 'bg-navy-700 text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Chat preview */}
            <div
              ref={contentRef}
              className="bg-navy-700 rounded-2xl p-6 border border-white/[0.04] shadow-card"
            >
              <div className="flex items-center gap-2 mb-5 pb-4 border-b border-white/[0.04]">
                <div className="w-2 h-2 rounded-full bg-mint animate-pulse" />
                <span className="font-inter text-[14px] text-text-secondary">
                  {tabs[activeTab].label === 'Разговор'
                    ? 'Живой разговор'
                    : tabs[activeTab].label === 'Оценка'
                    ? 'Оценка разговора'
                    : 'Выводы для руководителя'}
                </span>
              </div>

              <div className="flex flex-col gap-3 max-h-[360px] overflow-y-auto pr-2">
                {tabs[activeTab].messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`max-w-[85%] p-3.5 rounded-xl text-[14px] leading-relaxed font-inter ${
                      msg.type === 'client'
                        ? 'bg-navy-600 text-text-secondary self-start'
                        : msg.type === 'manager'
                        ? 'bg-gradient-to-r from-mint/20 to-cyan/20 text-text-primary self-end border border-mint/20'
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
    </section>
  );
};

export default React.memo(HowItWorksSection);

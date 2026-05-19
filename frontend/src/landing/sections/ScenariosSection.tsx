import React, { useLayoutEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SectionLabel from '@/landing/components/SectionLabel';

gsap.registerPlugin(ScrollTrigger);

const scenarios = [
  { text: 'Бухгалтерский аутсорсинг', size: 'full' },
  { text: 'Финансовый директор на аутсорсе', size: 'full' },
  { text: 'B2B SaaS', size: 'half' },
  { text: 'Сложные услуги', size: 'half' },
  { text: 'Первичная квалификация', size: 'half' },
  { text: 'Работа с возражениями', size: 'half' },
  { text: 'Прогрев перед созвоном', size: 'half' },
  { text: 'Проверка знания скрипта', size: 'half' },
];

const ScenariosSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.scenarios-left',
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
        '.scenario-tag',
        { opacity: 0, y: 24, scale: 0.95 },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.4,
          stagger: 0.06,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: '.scenarios-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      id="scenarios"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800"
    >
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 lg:gap-16">
          {/* Left sticky */}
          <div className="scenarios-left lg:col-span-2 lg:sticky lg:top-[120px] lg:self-start">
            <SectionLabel text="СЦЕНАРИИ" />
            <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
              Тренировки собираются под нишу, этап воронки и тип сопротивления клиента.
            </h2>
            <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
              Не один общий шаблон, а отдельные сценарии под конкретный продукт, сегмент и цель
              тренировки.
            </p>
          </div>

          {/* Right — asymmetric tag grid */}
          <div className="scenarios-grid lg:col-span-3 grid grid-cols-2 gap-3">
            {scenarios.map((s, i) => (
              <div
                key={i}
                className={`scenario-tag bg-navy-700 rounded-xl px-5 py-4 font-inter font-medium text-[15px] text-text-primary border border-white/[0.04] shadow-card transition-all duration-200 hover:bg-navy-500 hover:scale-[1.02] cursor-default ${
                  s.size === 'full' ? 'col-span-2' : 'col-span-1'
                }`}
              >
                {s.text}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default React.memo(ScenariosSection);

import React, { useRef } from 'react';
import { useScrollReveal } from '../hooks/useScrollReveal';
import SectionLabel from '@/landing/components/SectionLabel';

const insights = [
  'Кого можно выпускать на лиды без тотальной ручной прослушки.',
  'Кто теряет клиента на диагностике и слишком рано уходит в презентацию.',
  'Кто не держит цену и уводит разговор в скидки.',
  'Кто не фиксирует следующий шаг и оставляет сделку без движения.',
  'Какие возражения повторяются чаще всего и где команда буксует системно.',
  'Где скрипт выглядит убедительно на бумаге, но не работает в живом разговоре.',
];

const ForManagersSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useScrollReveal(sectionRef, [
    {
      targets: '.managers-left',
      from: { opacity: 0, y: 24 },
      to: { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' },
    },
    {
      targets: '.insight-card',
      from: { opacity: 0, y: 32 },
      to: { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, ease: 'power2.out' },
      scrollTrigger: { trigger: '.insight-grid', start: 'top 85%' },
    },
  ]);

  return (
    <section
      id="managers"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800"
    >
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 lg:gap-16">
          {/* Left sticky */}
          <div className="managers-left lg:col-span-2 lg:sticky lg:top-[120px] lg:self-start">
            <SectionLabel text="ДЛЯ РУКОВОДИТЕЛЯ" />
            <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
              Тренажёр нужен не для красивой симуляции, а для решений по качеству разговора.
            </h2>
            <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
              Он помогает понять, кого выпускать на лиды, где команда теряет сделку и какие темы
              нужно тренировать в первую очередь.
            </p>
          </div>

          {/* Right insight cards */}
          <div className="insight-grid lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {insights.map((text, i) => (
              <div
                key={i}
                className="insight-card bg-navy-700 rounded-2xl p-6 border border-white/[0.04] shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover hover:border-white/[0.08] border-l-[3px] border-l-mint/30 hover:border-l-mint"
              >
                <p className="font-inter text-[16px] text-text-primary leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default React.memo(ForManagersSection);

import React, { useRef } from 'react';
import { useScrollReveal } from '../hooks/useScrollReveal';
import SectionLabel from '@/landing/components/SectionLabel';

const problems = [
  {
    num: '01',
    text: 'Менеджер знает скрипт, но теряет логику разговора, когда клиент начинает сопротивляться.',
  },
  {
    num: '02',
    text: 'Ошибку замечают слишком поздно: уже после паузы, возражения по цене или срыва следующего шага.',
  },
  {
    num: '03',
    text: 'Руководитель видит просадку по воронке, но не видит точку, где разговор сломался.',
  },
  {
    num: '04',
    text: 'Разбор зависит от субъективной оценки, а не от единого стандарта качества диалога.',
  },
];

const ProblemSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useScrollReveal(sectionRef, [
    {
      targets: '.problem-left',
      from: { opacity: 0, y: 24 },
      to: { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' },
    },
    {
      targets: '.problem-card',
      from: { opacity: 0, y: 32 },
      to: { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, ease: 'power2.out' },
      scrollTrigger: { trigger: '.problem-grid', start: 'top 85%' },
    },
  ]);

  return (
    <section
      id="problem"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800"
    >
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 lg:gap-16">
          {/* Left sticky */}
          <div className="problem-left lg:col-span-2 lg:sticky lg:top-[120px] lg:self-start">
            <SectionLabel text="ПРОБЛЕМА" />
            <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
              Обычный контроль показывает итог, но не даёт увидеть момент, где разговор начинает
              терять клиента.
            </h2>
            <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
              Скрипт, CRM и прослушка звонков собирают следы, но не показывают саму механику
              провала. Из-за этого обучение часто запаздывает.
            </p>
          </div>

          {/* Right cards */}
          <div className="problem-grid lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {problems.map((p) => (
              <div
                key={p.num}
                className="problem-card bg-navy-700 rounded-2xl p-7 border border-white/[0.04] shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover hover:border-white/[0.08]"
              >
                <span className="font-mono text-[14px] text-mint/50 block mb-3">{p.num}</span>
                <p className="font-inter text-[16px] text-text-primary leading-relaxed">{p.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default React.memo(ProblemSection);

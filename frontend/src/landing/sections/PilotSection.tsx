import React, { useRef } from 'react';
import { useScrollReveal } from '../hooks/useScrollReveal';
import SectionLabel from '@/landing/components/SectionLabel';
import GradientButton from '@/landing/components/GradientButton';

const steps = [
  { num: 1, text: 'Выбираем один сценарий и этап воронки.' },
  { num: 2, text: 'Фиксируем продукт, целевую аудиторию, боли и ограничения клиента.' },
  { num: 3, text: 'Собираем тренировочного клиента под нужный контекст.' },
  { num: 4, text: 'Менеджер проходит тренировку в кабинете.' },
  { num: 5, text: 'Руководитель получает выводы и план разбора.' },
];

interface PilotSectionProps {
  onDemoClick: () => void;
}

const PilotSection: React.FC<PilotSectionProps> = ({ onDemoClick }) => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useScrollReveal(sectionRef, [
    {
      targets: '.pilot-header',
      from: { opacity: 0, y: 24 },
      to: { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' },
    },
    {
      targets: '.pilot-step',
      from: { opacity: 0, y: 24 },
      to: { opacity: 1, y: 0, duration: 0.5, stagger: 0.15, ease: 'power2.out' },
      scrollTrigger: { trigger: '.pilot-timeline', start: 'top 85%' },
    },
    {
      targets: '.pilot-cta',
      from: { opacity: 0, y: 20 },
      to: { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' },
      scrollTrigger: { trigger: '.pilot-cta', start: 'top 90%' },
    },
  ]);

  return (
    <section
      id="pilot"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800 overflow-hidden"
    >
      {/* Ambient glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 50% 50%, rgba(94,234,212,0.03) 0%, transparent 60%)',
        }}
      />

      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="pilot-header text-center max-w-[700px] mx-auto mb-16">
          <SectionLabel text="ПИЛОТ" />
          <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
            Запуск можно собрать вокруг одного сценария без долгого внедрения.
          </h2>
          <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
            Достаточно выбрать важный разговор, собрать тренировочного клиента и получить
            материал для первого разбора.
          </p>
        </div>

        {/* Timeline */}
        <div className="pilot-timeline relative mb-16">
          {/* Connector line - desktop only */}
          <div
            className="hidden lg:block absolute top-[18px] left-[10%] right-[10%] h-[1px]"
            style={{ background: 'rgba(94,234,212,0.15)' }}
          />

          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-8 lg:gap-4">
            {steps.map((step, i) => (
              <div
                key={step.num}
                className={`pilot-step flex flex-col items-center text-center ${
                  i % 2 === 1 ? 'lg:-translate-y-6' : ''
                }`}
              >
                {/* Number badge */}
                <div className="w-9 h-9 rounded-full bg-navy-700 border border-mint/20 flex items-center justify-center mb-4 relative z-10">
                  <span className="font-mono text-[14px] font-medium text-mint">
                    {step.num}
                  </span>
                </div>
                {/* Text */}
                <p className="font-inter text-[15px] text-text-primary leading-relaxed max-w-[200px]">
                  {step.text}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="pilot-cta text-center">
          <p className="font-inter text-[16px] text-text-secondary leading-relaxed max-w-[640px] mx-auto mb-6">
            Не нужна большая программа обучения. Достаточно одного приоритетного разговора,
            чтобы увидеть, как менеджер ведёт сопротивление и фиксирует следующий шаг.
          </p>
          <GradientButton onClick={onDemoClick} className="!h-[52px] !px-10">
            Запустить демо-тренировку
          </GradientButton>
        </div>
      </div>
    </section>
  );
};

export default React.memo(PilotSection);

import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SectionLabel from '@/components/SectionLabel';
import MetricCard from '@/components/MetricCard';

gsap.registerPlugin(ScrollTrigger);

const metrics = [
  {
    name: 'Структура разговора',
    score: 86,
    description: 'Насколько менеджер удерживает логику беседы и не перескакивает в презентацию раньше времени.',
  },
  {
    name: 'Выявление боли',
    score: 72,
    description: 'Увидел ли менеджер реальную причину интереса и зафиксировал ли проблему клиента.',
    offset: true,
  },
  {
    name: 'Квалификация ЛПР',
    score: 68,
    description: 'Понял ли менеджер, кто влияет на решение и как сейчас устроен выбор поставщика.',
  },
  {
    name: 'Работа с возражением',
    score: 63,
    description: 'Снял ли сомнение без давления и не превратил ли разговор в торг.',
  },
  {
    name: 'Следующий шаг',
    score: 58,
    description: 'Договорился ли менеджер о понятном продолжении разговора.',
  },
  {
    name: 'Что разбирать с командой',
    score: 81,
    description: 'Какие сигналы руководитель получает для обучения, проверки и точечной обратной связи.',
  },
];

const MetricsReportSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.metrics-header',
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
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      id="metrics"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800 overflow-hidden"
    >
      {/* Ambient glow */}
      <div
        className="absolute top-1/4 left-0 w-[600px] h-[600px] pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 30% 60%, rgba(56,189,248,0.04) 0%, transparent 50%)',
        }}
      />

      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="metrics-header max-w-[640px] mb-12 lg:mb-16">
          <SectionLabel text="ЧТО ВИДНО В ОТЧЁТЕ" />
          <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
            Не один итоговый балл, а карта разговора по ключевым навыкам.
          </h2>
          <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
            Каждая метрика показывает отдельный управляемый навык и подсказывает, что разбирать
            дальше.
          </p>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {metrics.map((metric, i) => (
            <MetricCard
              key={i}
              name={metric.name}
              score={metric.score}
              description={metric.description}
              offset={metric.offset}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default React.memo(MetricsReportSection);

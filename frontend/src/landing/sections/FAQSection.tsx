import React, { useRef } from 'react';
import { useScrollReveal } from '../hooks/useScrollReveal';
import SectionLabel from '@/landing/components/SectionLabel';
import FAQItem from '@/landing/components/FAQItem';

const faqData = [
  {
    question: 'Это заменяет обучение менеджеров?',
    answer: 'Нет. Тренажёр даёт практику и материал для разбора, а руководитель остаётся владельцем стандарта и обратной связи.',
  },
  {
    question: 'Можно ли настроить сценарии под наш продукт?',
    answer: 'Да. Каждый сценарий собирается под ваш продукт, целевую аудиторию, боли и возражения клиента.',
  },
  {
    question: 'Нужны ли интеграции и длинное внедрение?',
    answer: 'Нет. Запуск занимает 1–2 дня. Нужен только список менеджеров и приоритетный сценарий.',
  },
  {
    question: 'Есть ли кабинет для команды?',
    answer: 'Да. Руководитель видит все тренировки, метрики и выводы по каждому менеджеру в одном кабинете.',
  },
  {
    question: 'Вы гарантируете рост продаж?',
    answer: 'Мы гарантируем прозрачность качества разговора. Рост продаж — результат работы с слабыми местами, который команда видит через 2–4 недели.',
  },
];

const FAQSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useScrollReveal(sectionRef, [
    {
      targets: '.faq-header',
      from: { opacity: 0, y: 24 },
      to: { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' },
    },
    {
      targets: '.faq-item',
      from: { opacity: 0, y: 20 },
      to: { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: 'power2.out' },
      scrollTrigger: { trigger: '.faq-list', start: 'top 85%' },
    },
  ]);

  return (
    <section
      id="faq"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800"
    >
      <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="faq-header text-center mb-12">
          <SectionLabel text="FAQ" centered />
          <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15]">
            Коротко о запуске, кабинетах и границах продукта.
          </h2>
        </div>

        <div className="faq-list flex flex-col gap-3">
          {faqData.map((item, i) => (
            <div key={i} className="faq-item">
              <FAQItem question={item.question} answer={item.answer} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default React.memo(FAQSection);

import React, { useState, useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SectionLabel from '@/components/SectionLabel';
import GradientButton from '@/components/GradientButton';

gsap.registerPlugin(ScrollTrigger);

const DemoFormSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    role: '',
    teamSize: '',
    message: '',
    consent1: false,
    consent2: false,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
    alert('Спасибо! Мы свяжемся с вами в течение 1 рабочего дня.');
  };

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.demo-left',
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
        '.demo-form-card',
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

  return (
    <section
      id="demo"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-navy-800"
    >
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 lg:gap-16">
          {/* Left sticky */}
          <div className="demo-left lg:col-span-2 lg:sticky lg:top-[120px] lg:self-start">
            <SectionLabel text="ДЕМО" />
            <h2 className="font-manrope font-bold text-[28px] sm:text-[32px] lg:text-[36px] text-text-primary leading-[1.15] mb-4">
              Проверьте одного менеджера на одном сценарии и получите картину слабого места до
              реального клиента.
            </h2>
            <p className="font-inter text-[16px] text-text-secondary leading-relaxed">
              Без длинного внедрения. Достаточно демо-тренировки, чтобы увидеть, как менеджер
              держит разговор, реагирует на сопротивление и фиксирует продолжение.
            </p>
          </div>

          {/* Right form */}
          <div className="demo-form-card lg:col-span-3">
            <form
              onSubmit={handleSubmit}
              className="bg-navy-600 rounded-[20px] p-8 sm:p-10 border border-white/[0.05] shadow-form"
            >
              {/* Group 1: Контакты */}
              <div className="mb-6">
                <span className="font-inter font-medium text-[13px] text-text-secondary uppercase tracking-[0.08em] block mb-3">
                  Контакты
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <input
                    type="text"
                    name="name"
                    placeholder="Имя"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary placeholder:text-text-tertiary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)]"
                  />
                  <input
                    type="email"
                    name="email"
                    placeholder="Email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary placeholder:text-text-tertiary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)]"
                  />
                </div>
              </div>

              {/* Group 2: О компании */}
              <div className="mb-6">
                <span className="font-inter font-medium text-[13px] text-text-secondary uppercase tracking-[0.08em] block mb-3">
                  О компании
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <input
                    type="tel"
                    name="phone"
                    placeholder="Телефон"
                    value={formData.phone}
                    onChange={handleChange}
                    required
                    className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary placeholder:text-text-tertiary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)]"
                  />
                  <input
                    type="text"
                    name="company"
                    placeholder="Компания"
                    value={formData.company}
                    onChange={handleChange}
                    required
                    className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary placeholder:text-text-tertiary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)]"
                  />
                </div>
              </div>

              {/* Group 3: Роль + Размер команды */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="font-inter text-[14px] text-text-secondary block mb-2">
                    Роль
                  </label>
                  <select
                    name="role"
                    value={formData.role}
                    onChange={handleChange}
                    required
                    className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)] appearance-none cursor-pointer"
                  >
                    <option value="">Выберите роль</option>
                    <option value="owner">Собственник</option>
                    <option value="rop">РОП</option>
                    <option value="ldhr">L&D / HR</option>
                    <option value="manager">Менеджер</option>
                  </select>
                </div>
                <div>
                  <label className="font-inter text-[14px] text-text-secondary block mb-2">
                    Размер команды
                  </label>
                  <select
                    name="teamSize"
                    value={formData.teamSize}
                    onChange={handleChange}
                    required
                    className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)] appearance-none cursor-pointer"
                  >
                    <option value="">Выберите диапазон</option>
                    <option value="1-5">1-5</option>
                    <option value="6-20">6-20</option>
                    <option value="21-50">21-50</option>
                    <option value="50+">50+</option>
                  </select>
                </div>
              </div>

              {/* Textarea */}
              <div className="mb-6">
                <label className="font-inter text-[14px] text-text-secondary block mb-2">
                  Что хотите проверить в пилоте
                </label>
                <textarea
                  name="message"
                  rows={4}
                  placeholder="Например: входящая встреча, возражение по цене, квалификация ЛПР."
                  value={formData.message}
                  onChange={handleChange}
                  className="w-full bg-navy-800 rounded-xl px-4 py-3.5 border border-white/[0.08] text-text-primary placeholder:text-text-tertiary font-inter text-[15px] outline-none transition-all duration-200 focus:border-mint focus:shadow-[0_0_0_3px_rgba(94,234,212,0.1)] resize-none"
                />
              </div>

              {/* Checkboxes */}
              <div className="flex flex-col gap-3 mb-6">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="consent1"
                    checked={formData.consent1}
                    onChange={handleChange}
                    required
                    className="mt-1 w-4 h-4 rounded border-white/[0.15] bg-navy-800 text-mint focus:ring-mint/30 flex-shrink-0"
                  />
                  <span className="font-inter text-[13px] text-text-secondary leading-relaxed">
                    Согласен на обработку персональных данных для связи по демо.
                  </span>
                </label>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="consent2"
                    checked={formData.consent2}
                    onChange={handleChange}
                    className="mt-1 w-4 h-4 rounded border-white/[0.15] bg-navy-800 text-mint focus:ring-mint/30 flex-shrink-0"
                  />
                  <span className="font-inter text-[13px] text-text-secondary leading-relaxed">
                    Можно прислать материалы по пилоту и продукту.
                  </span>
                </label>
              </div>

              {/* Submit */}
              <GradientButton type="submit" fullWidth className="!h-[52px] !text-[16px]">
                Попробовать демо
              </GradientButton>

              <p className="text-center font-inter text-[12px] text-text-tertiary mt-4">
                Мы перезвоним в течение 1 рабочего дня. Никаких предоплат.
              </p>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
};

export default React.memo(DemoFormSection);

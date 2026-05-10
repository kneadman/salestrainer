import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const fullText = 'Скрипт не показывает, как менеджер ведёт себя под давлением. Здесь видно, где он теряет вопрос, боль или следующий шаг.';

const VideoRevealSection: React.FC = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLParagraphElement>(null);
  const cursorRef = useRef<HTMLSpanElement>(null);
  const [isMobile, setIsMobile] = useState(false);
  const [displayedText, setDisplayedText] = useState('');
  const hasAnimated = useRef(false);

  useEffect(() => {
    setIsMobile(window.innerWidth < 768);
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (isMobile) return;

    const ctx = gsap.context(() => {
      ScrollTrigger.create({
        trigger: sectionRef.current,
        start: 'top 70%',
        onEnter: () => {
          if (hasAnimated.current) return;
          hasAnimated.current = true;

          let index = 0;
          const speed = 35; // ms per character
          let timeoutId: ReturnType<typeof setTimeout> | null = null;
          let cancelled = false;

          const type = () => {
            if (cancelled) return;
            if (index <= fullText.length) {
              setDisplayedText(fullText.slice(0, index));
              index++;
              timeoutId = setTimeout(type, speed + Math.random() * 15);
            }
          };

          type();

          return () => {
            cancelled = true;
            if (timeoutId) clearTimeout(timeoutId);
          };
        },
      });

      // Cursor blink
      gsap.to(cursorRef.current, {
        opacity: 0,
        duration: 0.5,
        repeat: -1,
        yoyo: true,
        ease: 'steps(1)',
      });
    }, sectionRef);

    return () => ctx.revert();
  }, [isMobile]);

  if (isMobile) {
    return (
      <section className="relative py-20 bg-navy-800">
        <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="font-manrope font-bold text-[20px] sm:text-[24px] text-text-primary leading-[1.35]">
            {fullText}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      ref={sectionRef}
      className="relative py-28 lg:py-36 bg-navy-800"
    >
      <div className="max-w-[800px] mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <p
          ref={textRef}
          className="font-manrope font-bold text-[22px] sm:text-[26px] lg:text-[30px] text-text-primary leading-[1.4] min-h-[120px]"
        >
          {displayedText}
          <span
            ref={cursorRef}
            className="inline-block w-[3px] h-[1.1em] bg-mint ml-1 align-middle"
          />
        </p>
      </div>
    </section>
  );
};

export default React.memo(VideoRevealSection);

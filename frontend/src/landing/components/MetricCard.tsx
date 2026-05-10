import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface MetricCardProps {
  name: string;
  score: number;
  description: string;
  offset?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ name, score, description, offset = false }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const scoreRef = useRef<HTMLSpanElement>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const [displayedScore, setDisplayedScore] = useState(0);

  const statusColor = score > 80 ? '#5eead4' : score >= 50 ? '#fbbf24' : '#f472b6';
  const barWidth = `${score}%`;

  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        card,
        { opacity: 0, y: 32 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: card,
            start: 'top 90%',
            toggleActions: 'play none none none',
          },
        }
      );

      const scoreObj = { value: 0 };
      gsap.to(scoreObj, {
        value: score,
        duration: 1,
        ease: 'power2.out',
        snap: { value: 1 },
        scrollTrigger: {
          trigger: card,
          start: 'top 90%',
          toggleActions: 'play none none none',
        },
        onUpdate: () => setDisplayedScore(Math.round(scoreObj.value)),
      });

      if (barRef.current) {
        gsap.fromTo(
          barRef.current,
          { scaleX: 0 },
          {
            scaleX: 1,
            duration: 1,
            ease: 'power2.out',
            scrollTrigger: {
              trigger: card,
              start: 'top 90%',
              toggleActions: 'play none none none',
            },
          }
        );
      }
    }, card);

    return () => ctx.revert();
  }, [score]);

  return (
    <div
      ref={cardRef}
      className={`glass-card p-7 flex flex-col gap-3 ${offset ? 'md:-translate-y-4' : ''}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-manrope font-semibold text-[16px] text-text-primary">{name}</h3>
        <span
          ref={scoreRef}
          className="font-mono font-medium text-[32px]"
          style={{ color: statusColor }}
        >
          {displayedScore}
        </span>
      </div>
      <div className="h-1 bg-navy-500 rounded-full overflow-hidden">
        <div
          ref={barRef}
          className="h-full rounded-full origin-left"
          style={{
            width: barWidth,
            backgroundColor: statusColor,
          }}
        />
      </div>
      <p className="font-inter text-[14px] text-text-secondary leading-relaxed">{description}</p>
    </div>
  );
};

export default React.memo(MetricCard);

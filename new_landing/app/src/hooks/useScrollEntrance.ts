import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface ScrollEntranceOptions {
  y?: number;
  duration?: number;
  delay?: number;
  stagger?: number;
  start?: string;
  childSelector?: string;
}

export function useScrollEntrance(options: ScrollEntranceOptions = {}) {
  const ref = useRef<HTMLDivElement>(null);
  const {
    y = 24,
    duration = 0.6,
    delay = 0,
    stagger = 0,
    start = 'top 85%',
    childSelector,
  } = options;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const targets = childSelector ? el.querySelectorAll(childSelector) : el;
    
    gsap.set(targets, { opacity: 0, y });

    const tween = gsap.to(targets, {
      opacity: 1,
      y: 0,
      duration,
      delay,
      stagger: stagger || 0,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: el,
        start,
        toggleActions: 'play none none none',
      },
    });

    return () => {
      tween.kill();
    };
  }, [y, duration, delay, stagger, start, childSelector]);

  return ref;
}

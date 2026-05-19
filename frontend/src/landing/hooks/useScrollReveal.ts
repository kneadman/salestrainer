import { useLayoutEffect } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

type ScrollRevealAnimation = {
  targets: string;
  from: gsap.TweenVars;
  to: gsap.TweenVars;
  scrollTrigger?: {
    trigger?: string | Element | null;
    start?: string;
    toggleActions?: string;
  };
};

export function useScrollReveal(
  scopeRef: React.RefObject<HTMLElement>,
  animations: ScrollRevealAnimation[],
  deps: React.DependencyList = []
) {
  useLayoutEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = gsap.context(() => {
      animations.forEach((anim) => {
        gsap.fromTo(anim.targets, anim.from, {
          ...anim.to,
          scrollTrigger: {
            trigger: anim.scrollTrigger?.trigger ?? scopeRef.current,
            start: anim.scrollTrigger?.start ?? "top 80%",
            toggleActions: anim.scrollTrigger?.toggleActions ?? "play none none none",
          },
        });
      });
    }, scopeRef);

    return () => ctx.revert();
  }, deps);
}

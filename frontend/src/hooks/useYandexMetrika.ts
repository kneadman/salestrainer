import { useEffect, useRef } from "react";

const COUNTER_ID_RAW = import.meta.env.VITE_YANDEX_METRIKA_ID;
const COUNTER_ID = COUNTER_ID_RAW ? Number(COUNTER_ID_RAW) : 0;

let scriptLoaded = false;

function loadScript(): void {
  if (scriptLoaded || typeof document === "undefined") return;
  scriptLoaded = true;

  const scriptUrl = `https://mc.yandex.ru/metrika/tag.js?id=${COUNTER_ID}`;

  for (let j = 0; j < document.scripts.length; j++) {
    if (document.scripts[j].src === scriptUrl) {
      return;
    }
  }

  const script = document.createElement("script");
  script.type = "text/javascript";
  script.async = true;
  script.src = scriptUrl;

  script.onload = () => {
    if (typeof window !== "undefined" && window.ym) {
      window.ym(COUNTER_ID, "init", {
        ssr: true,
        webvisor: true,
        clickmap: true,
        ecommerce: "dataLayer",
        accurateTrackBounce: true,
        trackLinks: true,
      });
    }
  };

  const firstScript = document.getElementsByTagName("script")[0];
  if (firstScript && firstScript.parentNode) {
    firstScript.parentNode.insertBefore(script, firstScript);
  } else {
    document.head.appendChild(script);
  }
}

export function useYandexMetrika(pathname: string): void {
  const initialised = useRef(false);

  useEffect(() => {
    if (!COUNTER_ID) return;

    if (!initialised.current) {
      initialised.current = true;
      loadScript();
    }

    // Send a hit for the current route on every pathname change.
    // Wait a tick so the script has a chance to initialise on first load.
    const timer = setTimeout(() => {
      if (typeof window !== "undefined" && window.ym) {
        window.ym(COUNTER_ID, "hit", window.location.href);
      }
    }, 0);

    return () => clearTimeout(timer);
  }, [pathname]);
}

export function reachGoal(target: string): void {
  if (!COUNTER_ID) return;
  if (typeof window !== "undefined" && window.ym) {
    window.ym(COUNTER_ID, "reachGoal", target);
  }
}

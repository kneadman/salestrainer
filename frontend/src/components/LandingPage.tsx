import { FormEvent, useEffect, useMemo, useState } from "react";
import { submitLead } from "../api";
import { landingNavItems } from "./landing/content";
import {
  DemoSection,
  EvaluationTilesSection,
  FAQSection,
  FinalCTASection,
  HeroSection,
  LandingFooter,
  LandingHeader,
  ManagementUseCasesSection,
  PilotStepperSection,
  ProblemTilesSection,
  ScenarioTilesSection,
} from "./landing/Sections";

type LeadStatus = "idle" | "submitting" | "success" | "error";

type LandingPageProps = {
  authenticated: boolean;
};

function track(event: string, payload: Record<string, unknown> = {}) {
  /** Emit one lightweight landing analytics event without coupling the page to an analytics SDK. */
  const data = { event, ...payload };
  window.dispatchEvent(new CustomEvent("landing_analytics", { detail: data }));
  const maybeWindow = window as Window & { dataLayer?: Record<string, unknown>[] };
  maybeWindow.dataLayer?.push(data);
}

function collectQueryParams() {
  /** Capture current query params once so lead submissions preserve attribution tags. */
  return Object.fromEntries(new URLSearchParams(window.location.search).entries());
}

function scrollToBlock(id: string, eventName: string) {
  /** Scroll to one landing block and record the associated interaction. */
  track(eventName);
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function LandingPage({ authenticated }: LandingPageProps) {
  /** Render the public landing as a product-led story from problem to demo request. */
  const [mobileOpen, setMobileOpen] = useState(false);
  const [leadStatus, setLeadStatus] = useState<LeadStatus>("idle");
  const [leadConsent, setLeadConsent] = useState(false);
  const [leadFormOpened, setLeadFormOpened] = useState(false);
  const [faqOpen, setFaqOpen] = useState<number | null>(0);
  const [cookiesAccepted, setCookiesAccepted] = useState(() => localStorage.getItem("salestrainer.cookiesAccepted") === "true");
  const queryParams = useMemo(collectQueryParams, []);

  useEffect(() => {
    /** Track the page view and a couple of coarse scroll-depth milestones. */
    track("landing_view", { authenticated });
    let seen50 = false;
    let seen90 = false;

    const onScroll = () => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (maxScroll <= 0) {
        return;
      }

      const progress = window.scrollY / maxScroll;
      if (!seen50 && progress >= 0.5) {
        seen50 = true;
        track("scroll_50");
      }
      if (!seen90 && progress >= 0.9) {
        seen90 = true;
        track("scroll_90");
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [authenticated]);

  const handleLoginClick = () => {
    /** Route authenticated visitors into the cabinet and everyone else into login. */
    track("login_click");
    window.location.href = authenticated ? "/app" : "/login";
  };

  const handleCookieAccept = () => {
    /** Persist cookie consent locally for the public landing only. */
    localStorage.setItem("salestrainer.cookiesAccepted", "true");
    setCookiesAccepted(true);
    track("cookie_accept");
  };

  const handleLeadSubmit = async (event: FormEvent<HTMLFormElement>) => {
    /** Submit the landing demo request through the existing public lead endpoint. */
    event.preventDefault();
    if (!leadConsent || leadStatus === "submitting") {
      setLeadStatus("error");
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = {
      name: String(formData.get("name") ?? "").trim(),
      email: String(formData.get("email") ?? "").trim(),
      phone: String(formData.get("phone") ?? "").trim(),
      company: String(formData.get("company") ?? "").trim(),
      role: String(formData.get("role") ?? "").trim(),
      sales_team_size: String(formData.get("sales_team_size") ?? "").trim(),
      comment: String(formData.get("comment") ?? "").trim() || null,
      consent_personal_data: true,
      consent_marketing: formData.get("consent_marketing") === "on",
      query_params: queryParams,
      page: "landing",
      form_id: "main_lead_form",
    };

    setLeadStatus("submitting");
    track("lead_form_submit");

    try {
      await submitLead(payload);
      setLeadStatus("success");
      track("lead_form_success");
      form.reset();
      setLeadConsent(false);
    } catch {
      setLeadStatus("error");
      track("lead_form_error");
    }
  };

  const handleLeadFormFocus = () => {
    /** Track the first meaningful interaction with the demo-request form. */
    if (!leadFormOpened) {
      setLeadFormOpened(true);
      track("lead_form_open");
    }
  };

  return (
    <div className="lp-page">
      <LandingHeader
        authenticated={authenticated}
        mobileOpen={mobileOpen}
        navItems={landingNavItems}
        onLoginClick={handleLoginClick}
        onMobileToggle={() => setMobileOpen((value) => !value)}
        onCloseMobileMenu={() => setMobileOpen(false)}
        onDemoClick={() => {
          setMobileOpen(false);
          scrollToBlock("lead", "hero_demo_click");
        }}
      />

      <main>
        <HeroSection
          onDemoClick={() => scrollToBlock("lead", "hero_demo_click")}
          onMechanicsClick={() => scrollToBlock("demo", "hero_mechanics_click")}
        />
        <ProblemTilesSection />
        <DemoSection />
        <EvaluationTilesSection />
        <ManagementUseCasesSection />
        <ScenarioTilesSection />
        <PilotStepperSection onDemoClick={() => scrollToBlock("lead", "pilot_cta_click")} />
        <FinalCTASection
          leadStatus={leadStatus}
          leadConsent={leadConsent}
          onConsentChange={setLeadConsent}
          onLeadSubmit={handleLeadSubmit}
          onLeadFormFocus={handleLeadFormFocus}
        />
        <FAQSection openIndex={faqOpen} onToggle={(index) => setFaqOpen((current) => (current === index ? null : index))} />
      </main>

      <LandingFooter />

      {!cookiesAccepted ? (
        <div className="lp-cookies" role="dialog" aria-live="polite" aria-label="Уведомление о cookie">
          <p>Используем cookie и UTM-метки только для работы формы демо и базовой аналитики лендинга.</p>
          <button type="button" className="lp-button lp-button--primary" onClick={handleCookieAccept}>
            Понятно
          </button>
        </div>
      ) : null}
    </div>
  );
}

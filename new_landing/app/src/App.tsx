import { useLenis } from '@/hooks/useLenis';
import AmbientGlow from '@/sections/AmbientGlow';
import FixedHeader from '@/sections/FixedHeader';
import HeroSection from '@/sections/HeroSection';
import VideoRevealSection from '@/sections/VideoRevealSection';
import ProblemSection from '@/sections/ProblemSection';
import HowItWorksSection from '@/sections/HowItWorksSection';
import MetricsReportSection from '@/sections/MetricsReportSection';
import ForManagersSection from '@/sections/ForManagersSection';
import ScenariosSection from '@/sections/ScenariosSection';
import PilotSection from '@/sections/PilotSection';
import DemoFormSection from '@/sections/DemoFormSection';
import FAQSection from '@/sections/FAQSection';
import Footer from '@/sections/Footer';

function App() {
  useLenis();

  return (
    <>
      <AmbientGlow />
      <div className="relative z-[1]">
        <FixedHeader />
        <HeroSection />
        <VideoRevealSection />
        <ProblemSection />
        <HowItWorksSection />
        <MetricsReportSection />
        <ForManagersSection />
        <ScenariosSection />
        <PilotSection />
        <DemoFormSection />
        <FAQSection />
        <Footer />
      </div>
    </>
  );
}

export default App;

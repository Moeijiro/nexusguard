import { Architecture, DashboardCta, Footer, Hero, Modules, Nav, Safety } from "@/components/site/landing";

export default function Home() {
  return (
    <>
      <Nav />
      <main id="main">
        <Hero />
        <Architecture />
        <Modules />
        <Safety />
        <DashboardCta />
      </main>
      <Footer />
    </>
  );
}

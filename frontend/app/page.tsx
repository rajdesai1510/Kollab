import Link from "next/link";
import { ArrowRight, Users, Zap, Shield, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/ModeToggle";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Nav */}
      <header className="sticky top-0 z-50 border-b bg-white/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-outfit font-bold text-xl text-slate-800 tracking-tight">
            Nex<span className="text-indigo-600">us</span>
          </span>
          <div className="flex items-center gap-3">
            <ModeToggle />
            <Link href="/auth/login">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link href="/auth/login">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 max-w-4xl mx-auto w-full">
        <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 text-sm font-medium px-4 py-1.5 rounded-full mb-8">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
          Built for India's micro-influencer market
        </div>

        <h1 className="font-outfit text-5xl sm:text-6xl font-bold text-slate-900 leading-tight mb-6">
          Where creators meet{" "}
          <span className="text-indigo-600">brands that match</span>
        </h1>

        <p className="text-lg text-slate-500 max-w-xl mb-10 leading-relaxed">
          Nexus connects micro-influencers (10K–200K followers) with local
          D2C brands — no agency fees, no cold DMs, just genuine collaborations.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/auth/login">
            <Button size="lg" className="gap-2 px-8">
              Start for free <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <Link href="#how-it-works">
            <Button size="lg" variant="outline" className="px-8">
              See how it works
            </Button>
          </Link>
        </div>

        {/* Social proof numbers */}
        <div className="mt-16 flex gap-12 text-center">
          {[
            { num: "100%", label: "Free to start" },
            { num: "Instagram", label: "Only platform" },
            { num: "India", label: "Focused market" },
          ].map(({ num, label }) => (
            <div key={label}>
              <p className="font-outfit text-2xl font-bold text-slate-800">{num}</p>
              <p className="text-sm text-slate-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="bg-slate-50 py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-outfit text-3xl font-bold text-slate-800 text-center mb-2">
            Simple by design
          </h2>
          <p className="text-slate-500 text-center mb-12">
            From signup to collaboration in minutes.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Users,
                step: "01",
                title: "Sign up with Google",
                desc: "One click. No password to remember. Connect your Instagram account.",
              },
              {
                icon: TrendingUp,
                step: "02",
                title: "Your profile auto-fills",
                desc: "Follower count, engagement rate, and niche — pulled from Instagram automatically.",
              },
              {
                icon: Zap,
                step: "03",
                title: "Browse or be found",
                desc: "Creators browse campaign briefs. Brands search creators by niche and city.",
              },
              {
                icon: Shield,
                step: "04",
                title: "Connect directly",
                desc: "Send a collaboration request. Chat opens once both sides say yes.",
              },
            ].map(({ icon: Icon, step, title, desc }) => (
              <div
                key={step}
                className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm"
              >
                <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-indigo-600" />
                </div>
                <p className="text-xs font-semibold text-indigo-400 mb-2">
                  STEP {step}
                </p>
                <h3 className="font-outfit text-base font-semibold text-slate-800 mb-2">
                  {title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-16 px-6 bg-indigo-600">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="font-outfit text-3xl font-bold text-white mb-4">
            Ready to collaborate?
          </h2>
          <p className="text-indigo-200 mb-8">
            Join creators and brands building real partnerships across India.
          </p>
          <Link href="/auth/login">
            <Button
              size="lg"
              variant="secondary"
              className="bg-white text-indigo-600 hover:bg-indigo-50 px-10"
            >
              Get started — it's free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 px-6 text-center text-sm text-slate-400">
        <p>
          © {new Date().getFullYear()} Nexus · Made for India&apos;s
          creators
        </p>
      </footer>
    </div>
  );
}

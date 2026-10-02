import { HumanBenchmarkLanding } from "@/components/human-benchmark/HumanBenchmarkLanding";
export const metadata = {title:"Human Benchmark | CAPTCHA Challenges",description:"Participate anonymously in a 40-question visual benchmark."};
export default async function HumanBenchmarkPage({searchParams}: {searchParams:Promise<{cohort?:string}>}) {
  const {cohort} = await searchParams;
  return <HumanBenchmarkLanding cohort={cohort === "pilot" || cohort === "creator" ? cohort : "main"} />;
}

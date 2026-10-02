import "server-only";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { analysisCohort, csvExport, exportPage, humanSummary } from "./analytics.server";
import { BenchmarkError, checkAdmin, noStore } from "./security.server";

export async function adminApi(request: NextRequest, operation: "summary" | "json" | "csv", db: D1Database, key?: string) {
  await checkAdmin(request,key);
  const url = new URL(request.url);
  const cohort = analysisCohort(url);
  if (operation === "summary") return noStore(await humanSummary(db,cohort));
  if (operation === "json") {
    const page = await exportPage(db,cohort,url.searchParams.get("cursor") ?? "");
    return noStore({...page,cohort});
  }
  return new Response(csvExport(db,cohort),{headers:{"Content-Type":"text/csv; charset=utf-8","Content-Disposition":`attachment; filename="human-v1-${cohort}.csv"`,"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"}});
}
export async function handleAdmin(request: NextRequest, operation: "summary" | "json" | "csv") {
  try {
    const {env} = await getCloudflareContext({async:true});
    return await adminApi(request,operation,env.HUMAN_BENCHMARK_DB,env.HUMAN_BENCHMARK_ADMIN_KEY);
  } catch(error) {
    return noStore({error:error instanceof BenchmarkError ? error.message : "Administration is temporarily unavailable."},error instanceof BenchmarkError ? error.status : 503);
  }
}

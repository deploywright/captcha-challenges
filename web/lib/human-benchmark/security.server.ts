import "server-only";
import { NextRequest, NextResponse } from "next/server";

export const PARTICIPANT_COOKIE = "hb_participant_id";
export const SESSION_COOKIE = "hb_session_token";
export class BenchmarkError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export function opaqueToken() {
  return Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2,"0")).join("");
}
export async function hashToken(token: string) {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(token));
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2,"0")).join("");
}
export function checkOrigin(request: NextRequest) {
  const origin = request.headers.get("origin");
  const requestUrl = new URL(request.url);
  const host = request.headers.get("host") ?? requestUrl.host;
  const protocol = request.headers.get("x-forwarded-proto")?.split(",")[0].trim() ?? requestUrl.protocol.slice(0,-1);
  let sameOrigin = false;
  try { const source = new URL(origin ?? ""); sameOrigin = source.host === host && source.protocol === `${protocol}:` && source.origin === origin; } catch {}
  if (!sameOrigin || request.headers.get("sec-fetch-site") === "cross-site") {
    throw new BenchmarkError(403,"Please use this site's benchmark page.");
  }
}
export async function readBody(request: NextRequest): Promise<Record<string, unknown>> {
  if (!request.headers.get("content-type")?.startsWith("application/json")) throw new BenchmarkError(415,"JSON is required.");
  const reader = request.body?.getReader();
  if (!reader) throw new BenchmarkError(400,"A request body is required.");
  let size = 0;
  const chunks: Uint8Array[] = [];
  for (;;) {
    const next = await reader.read();
    if (next.done) break;
    size += next.value.byteLength;
    if (size > 4096) { await reader.cancel(); throw new BenchmarkError(413,"Request is too large."); }
    chunks.push(next.value);
  }
  try {
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk,offset); offset += chunk.length; }
    const body = JSON.parse(new TextDecoder().decode(bytes));
    if (!body || Array.isArray(body) || typeof body !== "object") throw new Error();
    return body;
  } catch { throw new BenchmarkError(400,"Invalid JSON request."); }
}
export function exactFields(body: Record<string,unknown>, allowed: string[]) {
  if (Object.keys(body).some(key => !allowed.includes(key))) throw new BenchmarkError(400,"Unexpected request field.");
}
export async function checkAdmin(request: NextRequest, key: string | undefined) {
  if (!key) throw new BenchmarkError(503,"Admin access is not configured.");
  const authorization = request.headers.get("authorization") ?? "";
  if (!authorization.startsWith("Bearer ") || authorization.length <= 7 || authorization.length > 512) throw new BenchmarkError(401,"Admin authentication required.");
  // Compare equal-length digests with constant-time Web Crypto verification.
  const cryptoKey = await crypto.subtle.importKey("raw", new TextEncoder().encode(key), {name:"HMAC",hash:"SHA-256"},false,["sign","verify"]);
  const data = new TextEncoder().encode("human-benchmark-admin");
  const suppliedKey = await crypto.subtle.importKey("raw", new TextEncoder().encode(authorization.slice(7)), {name:"HMAC",hash:"SHA-256"},false,["sign"]);
  const signature = await crypto.subtle.sign("HMAC",suppliedKey,data);
  if (!await crypto.subtle.verify("HMAC",cryptoKey,signature,data)) throw new BenchmarkError(401,"Admin authentication required.");
}
export function noStore(body: unknown, status = 200) {
  return NextResponse.json(body,{status,headers:{"Cache-Control":"private, no-store","Vary":"Cookie","X-Content-Type-Options":"nosniff"}});
}
export function setCookies(response: NextResponse, participantId: string, token: string, secure: boolean) {
  const options = {httpOnly:true,sameSite:"lax" as const,secure,path:"/"};
  response.cookies.set(PARTICIPANT_COOKIE,participantId,{...options,maxAge:60*60*24*365});
  response.cookies.set(SESSION_COOKIE,token,{...options,maxAge:60*60*24*30});
}

import type { NextRequest } from "next/server";
import { handleParticipant } from "@/lib/human-benchmark/api.server";
export const dynamic = "force-dynamic";
export const GET = (request: NextRequest) => handleParticipant(request,"session");
export const POST = (request: NextRequest) => handleParticipant(request,"start");

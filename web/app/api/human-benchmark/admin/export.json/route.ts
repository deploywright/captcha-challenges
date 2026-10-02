import type { NextRequest } from "next/server";
import { handleAdmin } from "@/lib/human-benchmark/admin.server";
export const dynamic = "force-dynamic";
export const GET = (request: NextRequest) => handleAdmin(request,"json");

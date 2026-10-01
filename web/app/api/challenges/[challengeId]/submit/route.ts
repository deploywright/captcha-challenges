import { NextRequest, NextResponse } from "next/server";
import { gradeSubmission } from "@/lib/challenges/validation.server";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ challengeId: string }> }
) {
  try {
    const { challengeId } = await context.params;
    if (!challengeId) {
      return NextResponse.json(
        { error: "Challenge ID is required." },
        { status: 400 }
      );
    }

    const body = await request.json();
    if (!body || body.answer === undefined) {
      return NextResponse.json(
        { error: "Submission must include an 'answer' field." },
        { status: 400 }
      );
    }

    const gradeResult = gradeSubmission(challengeId, body.answer);

    if (!gradeResult.valid) {
      return NextResponse.json(
        {
          error: gradeResult.error || "Submission validation failed.",
          challengeId,
        },
        { status: 404 }
      );
    }

    return NextResponse.json({
      correct: gradeResult.correct,
      challengeId: gradeResult.challengeId,
      variant: gradeResult.variant,
      solveTimeMs: typeof body.solveTimeMs === "number" ? body.solveTimeMs : undefined,
    });
  } catch (error) {
    console.error("Submission processing error:", error);
    return NextResponse.json(
      { error: "An unexpected error occurred while processing the submission." },
      { status: 500 }
    );
  }
}

import { NextResponse } from 'next/server';
import { geminiService } from '@/services/geminiService';

/**
 * Readiness Assessment Handler
 * GET /api/match/readiness/[sessionId]
 */
export async function GET(
  request: Request,
  { params }: { params: { sessionId: string } }
) {
  try {
    const sessionId = params.sessionId;
    const { searchParams } = new URL(request.url);
    const historyParam = searchParams.get('history');

    if (!sessionId || !historyParam) {
      return NextResponse.json(
        { error: 'Session ID and History are required' },
        { status: 400 }
      );
    }

    const history = JSON.parse(historyParam);

    // Call actual Gemini Readiness Engine
    const result = await geminiService.assessReadiness(history);

    return NextResponse.json({
      sessionId,
      status: result.recommendation,
      score: result.score,
      confidence: 0.9,
      recommendation: result.recommendation,
      compatibilityDimensions: result.dimensions,
      moderatorNotes: result.moderator_notes,
      suggestedNextSteps: [
        'Share a recent favorite memory.',
        'Discuss your ideal weekend routine.',
        'Ready for direct messaging!',
      ],
      shareableCardUrl: `https://datenow.app/share/${sessionId}`,
    });
  } catch (error) {
    console.error('Readiness API Error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

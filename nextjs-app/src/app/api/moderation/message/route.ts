import { NextResponse } from 'next/server';
import { geminiService } from '@/services/geminiService';

/**
 * AI Moderation Message Handler
 * POST /api/moderation/message
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { sessionId, userId, content, history, user1Name, user2Name, stage } = body;

    if (!sessionId || !userId || !content) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Call actual Gemini Service
    const aiResponse = await geminiService.getModeratorResponse(
      user1Name || 'User1',
      user2Name || 'User2',
      stage || 'icebreakers',
      content,
      history || []
    );

    return NextResponse.json({
      messageId: `msg_${Date.now()}`,
      moderatorMessage: aiResponse.moderator_message,
      questionTo: aiResponse.question_to,
      detectedSentiment: aiResponse.detected_sentiment,
      stage: aiResponse.stage_recommendation,
      safetyFlag: aiResponse.safety_flag,
    });
  } catch (error) {
    console.error('Moderation API Error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

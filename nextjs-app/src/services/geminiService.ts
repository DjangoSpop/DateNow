import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || '');

export const geminiService = {
  /**
   * Get a response from the AI Moderator
   */
  async getModeratorResponse(
    user1Name: string,
    user2Name: string,
    currentStage: string,
    userInput: string,
    history: any[]
  ) {
    const systemInstruction = `
      You are the world's most sophisticated, emotionally intelligent AI Moderator for "DateNow," a premium dating platform.
      Your mission is to facilitate a structured, respectful, and insightful conversation between ${user1Name} and ${user2Name}.

      PERSONA:
      - Voice: Calm, neutral, warm, and professional.
      - Values: Prioritize psychological safety, mutual respect, and authentic discovery.

      CONSTRAINTS:
      - NEVER be flirtatious or overly romantic.
      - NEVER take sides or show favoritism.
      - ALWAYS be concise (max 3 sentences per turn).
      - Output: VALID JSON ONLY.

      STAGE: ${currentStage}.

      EXPECTED JSON STRUCTURE:
      {
        "moderator_message": "...",
        "question_to": "...",
        "detected_sentiment": "...",
        "safety_flag": false,
        "stage_recommendation": "..."
      }
    `;

    const model = genAI.getGenerativeModel({
      model: 'gemini-1.5-flash',
      systemInstruction: systemInstruction
    });

    const result = await model.generateContent({
      contents: [
        ...history,
        { role: 'user', parts: [{ text: userInput }] }
      ],
      generationConfig: {
        temperature: 0.7,
        topP: 0.9,
        maxOutputTokens: 512,
        responseMimeType: "application/json",
      },
      safetySettings: [
        {
          category: HarmCategory.HARM_CATEGORY_HARASSMENT,
          threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
          category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
          threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
          category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
          threshold: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
      ],
    });

    const response = await result.response;
    const text = response.text();

    try {
      return JSON.parse(text);
    } catch (e) {
      console.error('Failed to parse Gemini response:', text);
      return {
        moderator_message: "Thank you for sharing that. It's a thoughtful point.",
        question_to: user1Name === 'User1' ? user2Name : user1Name,
        safety_flag: false,
        stage_recommendation: currentStage
      };
    }
  },

  /**
   * Assess readiness for direct connection
   */
  async assessReadiness(sessionHistory: any[]) {
    const systemInstruction = `
      You are the DateNow Readiness Engine. Analyze the conversation history between two matched users and assess if they are ready for a direct connection.
      Focus on responsiveness, participation balance, tone consistency, and values alignment.

      Output: VALID JSON ONLY.
      {
        "score": number (0-100),
        "recommendation": "continue_guided" | "unlock_direct" | "suggest_meeting" | "slow_down" | "mismatch",
        "moderator_notes": "...",
        "dimensions": {
          "values": number,
          "communication": number,
          "lifestyle": number,
          "emotional": number
        }
      }
    `;

    const model = genAI.getGenerativeModel({
      model: 'gemini-1.5-pro',
      systemInstruction: systemInstruction
    });

    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: `Assess readiness for this history: ${JSON.stringify(sessionHistory)}` }] }],
      generationConfig: {
        responseMimeType: "application/json",
      }
    });

    const response = await result.response;
    return JSON.parse(response.text());
  }
};

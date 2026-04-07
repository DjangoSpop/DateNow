# DateNow: Example API / JSON Contracts

## P. Example API / JSON Contracts

### POST `/api/moderation/message`
Submit a user's response to the AI moderator.

**Request Body:**
```json
{
  "sessionId": "UUID-123",
  "userId": "USER-456",
  "content": "I really value honesty and a good sense of humor in a partner.",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Response Body:**
```json
{
  "messageId": "MSG-789",
  "moderatorMessage": "That's a very insightful point, Sarah. Honesty is such a strong foundation.",
  "questionTo": "John",
  "nextQuestion": "John, how do you typically build trust in a new connection?",
  "detectedSentiment": "warm",
  "stage": "values",
  "safetyFlag": false
}
```

### GET `/api/match/readiness/[sessionId]`
Get the final readiness summary for a session.

**Response Body:**
```json
{
  "sessionId": "UUID-123",
  "status": "ready_for_direct_chat",
  "score": 82,
  "confidence": 0.9,
  "recommendation": "unlock_direct",
  "compatibilityDimensions": {
    "values": 85,
    "communication": 78,
    "lifestyle": 72,
    "emotional": 88
  },
  "moderatorNotes": "Both Sarah and John demonstrate high levels of mutual respect and clear, honest communication. Their values around family and career are well-aligned.",
  "suggestedNextSteps": [
    "Share a recent favorite memory.",
    "Discuss your ideal weekend routine.",
    "Ready for direct messaging!"
  ],
  "shareableCardUrl": "https://datenow.app/share/UUID-123"
}
```

### POST `/api/user/invite`
Invite a friend or a match to a guided session.

**Request Body:**
```json
{
  "inviterId": "USER-456",
  "inviteeEmail": "friend@example.com",
  "type": "guided_connection",
  "customMessage": "I thought you'd love trying this AI-guided connection with me!"
}
```

**Response Body:**
```json
{
  "inviteId": "INVITE-ABC",
  "inviteUrl": "https://datenow.app/invite/INVITE-ABC",
  "status": "pending"
}
```

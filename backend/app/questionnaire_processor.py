"""
Process questionnaire responses and calculate psychological scores
"""
from typing import Dict, Any


def calculate_big_five_score(responses: Dict[str, Any], trait: str) -> float:
    """
    Calculate Big Five trait score from questionnaire responses

    Args:
        responses: Dictionary of question_id -> answer mappings
        trait: The trait to calculate (openness, conscientiousness, extraversion, agreeableness, neuroticism)

    Returns:
        Score from 0-100
    """
    trait_questions = {
        'extraversion': {
            'bf_1': False, 'bf_2': True, 'bf_3': False, 'bf_4': True,
            'bf_5': False, 'bf_6': True, 'bf_7': False, 'bf_8': True
        },
        'agreeableness': {
            'bf_9': True, 'bf_10': False, 'bf_11': True, 'bf_12': False,
            'bf_13': True, 'bf_14': False, 'bf_15': True, 'bf_16': False,
            'bf_17': False, 'bf_18': False
        },
        'conscientiousness': {
            'bf_19': False, 'bf_20': True, 'bf_21': False, 'bf_22': True,
            'bf_23': False, 'bf_24': True, 'bf_25': False, 'bf_26': True,
            'bf_27': False, 'bf_28': False
        },
        'neuroticism': {
            'bf_29': False, 'bf_30': True, 'bf_31': False, 'bf_32': True,
            'bf_33': False, 'bf_34': False, 'bf_35': False, 'bf_36': False
        },
        'openness': {
            'bf_37': False, 'bf_38': True, 'bf_39': False, 'bf_40': True,
            'bf_41': False, 'bf_42': True, 'bf_43': False, 'bf_44': False
        }
    }

    if trait not in trait_questions:
        return 0.0

    questions = trait_questions[trait]
    total_score = 0
    count = 0

    for q_id, is_reverse in questions.items():
        if q_id in responses:
            answer = responses[q_id]
            if isinstance(answer, (int, float)):
                # Reverse scoring if needed
                score = (6 - answer) if is_reverse else answer
                total_score += score
                count += 1

    if count == 0:
        return 0.0

    # Convert to 0-100 scale
    avg_score = total_score / count
    return (avg_score / 5) * 100


def calculate_value_score(responses: Dict[str, Any], value: str) -> float:
    """Calculate value score from questionnaire responses"""
    value_questions = {
        'family_orientation': ['val_1', 'val_6'],
        'career_ambition': ['val_2'],
        'adventure_seeking': ['val_3'],
        'social_consciousness': ['val_4'],
        'spiritual_religious': ['val_5']
    }

    if value not in value_questions:
        return 0.0

    questions = value_questions[value]
    scores = []

    for q_id in questions:
        if q_id in responses:
            answer = responses[q_id]
            if isinstance(answer, (int, float)):
                scores.append((answer / 5) * 100)
            elif isinstance(answer, str):
                # Handle string responses (choice questions)
                choice_scores = {
                    'Definitely': 100,
                    'Probably': 75,
                    'Not sure': 50,
                    'Probably not': 25,
                    'Definitely not': 0
                }
                scores.append(choice_scores.get(answer, 50))

    return sum(scores) / len(scores) if scores else 0.0


def calculate_love_language_score(responses: Dict[str, Any], language: str) -> float:
    """Calculate love language score"""
    language_questions = {
        'words': ['ll_1'],
        'acts': ['ll_2'],
        'gifts': ['ll_3'],
        'time': ['ll_4'],
        'touch': ['ll_5']
    }

    if language not in language_questions:
        return 0.0

    questions = language_questions[language]
    scores = []

    for q_id in questions:
        if q_id in responses:
            answer = responses[q_id]
            if isinstance(answer, (int, float)):
                scores.append((answer / 5) * 100)

    return sum(scores) / len(scores) if scores else 0.0


def determine_communication_style(responses: Dict[str, Any]) -> str:
    """Determine communication style from responses"""
    if 'comm_1' in responses:
        return responses['comm_1']
    return 'diplomatic'


def determine_conflict_resolution(responses: Dict[str, Any]) -> str:
    """Determine conflict resolution style"""
    if 'comm_2' in responses:
        answer = responses['comm_2']
        if 'directly' in answer.lower():
            return 'direct'
        elif 'time' in answer.lower():
            return 'reflective'
        elif 'compromise' in answer.lower():
            return 'collaborative'
        elif 'avoid' in answer.lower():
            return 'avoidant'
    return 'collaborative'


def determine_attachment_style(responses: Dict[str, Any]) -> str:
    """Determine attachment style from responses"""
    # Simple scoring based on attachment questions
    if 'att_5' in responses:
        answer = responses['att_5']
        if 'very close' in answer.lower():
            return 'secure'
        elif 'independence' in answer.lower():
            return 'secure'
        elif 'distance' in answer.lower():
            return 'avoidant'
        else:
            return 'secure'

    # Fallback based on att_1-att_4 scores
    if 'att_1' in responses and 'att_2' in responses:
        close_comfort = responses.get('att_1', 3)
        abandon_worry = responses.get('att_2', 3)

        if close_comfort >= 4 and abandon_worry <= 2:
            return 'secure'
        elif close_comfort <= 2 and abandon_worry <= 2:
            return 'avoidant'
        elif close_comfort >= 4 and abandon_worry >= 4:
            return 'anxious'
        else:
            return 'fearful-avoidant'

    return 'secure'


def process_questionnaire(responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw questionnaire responses and return calculated psychological profile

    Args:
        responses: Dictionary of question_id -> answer mappings

    Returns:
        Dictionary with all psychological profile fields
    """
    return {
        # Big Five
        'openness': calculate_big_five_score(responses, 'openness'),
        'conscientiousness': calculate_big_five_score(responses, 'conscientiousness'),
        'extraversion': calculate_big_five_score(responses, 'extraversion'),
        'agreeableness': calculate_big_five_score(responses, 'agreeableness'),
        'neuroticism': calculate_big_five_score(responses, 'neuroticism'),

        # Values
        'family_orientation': calculate_value_score(responses, 'family_orientation'),
        'career_ambition': calculate_value_score(responses, 'career_ambition'),
        'adventure_seeking': calculate_value_score(responses, 'adventure_seeking'),
        'social_consciousness': calculate_value_score(responses, 'social_consciousness'),
        'spiritual_religious': calculate_value_score(responses, 'spiritual_religious'),

        # Communication
        'communication_style': determine_communication_style(responses),
        'conflict_resolution': determine_conflict_resolution(responses),

        # Love Languages
        'love_language_words': calculate_love_language_score(responses, 'words'),
        'love_language_acts': calculate_love_language_score(responses, 'acts'),
        'love_language_gifts': calculate_love_language_score(responses, 'gifts'),
        'love_language_time': calculate_love_language_score(responses, 'time'),
        'love_language_touch': calculate_love_language_score(responses, 'touch'),

        # Attachment
        'attachment_style': determine_attachment_style(responses),

        # Store raw responses
        'questionnaire_responses': responses
    }


def verify_authenticity(responses: Dict[str, Any]) -> tuple[bool, str]:
    """
    Verify user authenticity from verification questions

    Returns:
        (is_authentic, reason)
    """
    # Check if verification questions are answered
    if 'verify_1' not in responses or 'verify_2' not in responses:
        return (False, "Verification questions not answered")

    verify_1 = str(responses.get('verify_1', '')).strip()
    verify_2 = str(responses.get('verify_2', '')).strip()

    # Check minimum length
    if len(verify_1) < 20:
        return (False, "First verification answer too short")

    if len(verify_2) < 20:
        return (False, "Second verification answer too short")

    # Check for bot-like patterns (all caps, excessive repetition, etc.)
    if verify_1.isupper() or verify_2.isupper():
        return (False, "Suspicious formatting detected")

    # Check for meaningful content (basic heuristic)
    common_words = ['i', 'to', 'the', 'a', 'and', 'for', 'with', 'my', 'me', 'we']
    words_1 = verify_1.lower().split()
    words_2 = verify_2.lower().split()

    has_common_1 = any(word in words_1 for word in common_words)
    has_common_2 = any(word in words_2 for word in common_words)

    if not has_common_1 or not has_common_2:
        return (False, "Answers do not appear natural")

    return (True, "Verification successful")

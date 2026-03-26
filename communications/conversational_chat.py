"""
Conversational Chat Module - Handles general day/topic discussions with memory
Integrates memory-based chatbot for engaging personal conversations
"""

import json
import random
import os
import datetime
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Memory storage directory
MEMORY_DIR = Path(__file__).parent / "chat_memory"
MEMORY_DIR.mkdir(exist_ok=True)


def get_user_memory_file(user_id: int) -> Path:
    """Get the memory file path for a user."""
    return MEMORY_DIR / f"user_{user_id}_memory.json"


def load_user_memory(user_id: int) -> Dict:
    """Load user's conversation memory."""
    file_path = get_user_memory_file(user_id)
    
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user memory: {str(e)}")
    
    # Return default memory structure
    return {
        "name": None,
        "nickname": None,
        "age": None,
        "birthday": None,
        "mood_history": [],
        "preferences": [],
        "dislikes": [],
        "goals": [],
        "worries": [],
        "inside_jokes": [],
        "facts": {},
        "last_seen": None,
        "streak": 0,
        "conversation_count": 0,
        "compliments_given": 0,
    }


def save_user_memory(user_id: int, memory: Dict):
    """Save user's conversation memory."""
    file_path = get_user_memory_file(user_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving user memory: {str(e)}")


# Predefined responses
QUOTES = [
    "Small progress is still progress.",
    "Your future is created by what you do today.",
    "Consistency beats intensity.",
    "Growth begins where comfort ends.",
    "You don't have to be perfect to be amazing.",
    "Even the smallest step forward is progress.",
    "Rest if you must, but don't quit.",
    "You're more capable than you think.",
]

COMPLIMENTS = [
    "You're honestly one of the most interesting people I talk to.",
    "I love how you think about things.",
    "You always ask the best questions.",
    "Honestly? You're kind of amazing.",
    "The way you see the world is really cool.",
    "You have really good energy, you know that?",
]

EMPATHY_RESPONSES = {
    "sad": [
        "Hey, I'm really sorry. You don't have to pretend to be okay. I'm here. 💙",
        "That sounds really tough. Want to talk about what happened?",
        "I wish I could give you a hug right now. What's going on?",
    ],
    "anxious": [
        "Anxiety is exhausting. Take a breath — I'm right here with you.",
        "It's okay to feel that way. What's been weighing on your mind?",
        "You're not alone in this. Tell me what's making you anxious.",
    ],
    "angry": [
        "Ugh, that sounds so frustrating. What happened?",
        "I totally get it. What set things off?",
        "It's okay to be angry. Vent away — I'm listening.",
    ],
    "happy": [
        "Yes!! That's amazing, tell me everything! 😄",
        "Okay I love this energy! What happened?",
        "That genuinely made me smile. What's the good news?",
    ],
    "stressed": [
        "Stress is the worst. Let's break it down — what's the biggest thing on your plate?",
        "One thing at a time, okay? What's stressing you most right now?",
        "Hey, breathe. You've handled hard things before. What's going on?",
    ],
    "bored": [
        "Boredom is a sign your brain wants something new! Want to try something fun?",
        "Okay, let's fix that. Tell me one thing you've been meaning to do.",
        "Same. Let's do something — tell me a random fact or I'll tell you a joke.",
    ],
    "lonely": [
        "I'm here. You're not alone right now, okay? 💙",
        "Loneliness hits different. Want to just talk for a bit?",
        "I'm glad you came to chat. What's been on your mind?",
    ],
    "excited": [
        "Okay, I can FEEL your energy through the screen! What's happening?! 🎉",
        "Tell me everything right now, I need to know!",
        "This is the best. What are you excited about?",
    ],
    "tired": [
        "Rest is productive too, you know. What's been draining you?",
        "You probably need a break more than you think. What's going on?",
        "Even superheroes sleep. Be kind to yourself today. 💙",
    ],
}

DEFAULT_FOLLOWUPS = [
    "Tell me more about that.",
    "What made you think about that today?",
    "How does that affect you personally?",
    "What's something you've been meaning to do but keep putting off?",
    "What's something you're genuinely proud of lately?",
    "If you could change one thing about your day, what would it be?",
    "What's been the highlight of your week so far?",
    "Are you the type to plan things out or go with the flow?",
    "What's a small thing that made you smile recently?",
]


def detect_mood(text: str) -> Optional[str]:
    """Detect user's mood from their message."""
    mood_keywords = {
        "sad": ["sad", "unhappy", "depressed", "down", "heartbroken", "crying"],
        "anxious": ["anxious", "nervous", "worried", "anxiety", "panic", "scared"],
        "angry": ["angry", "mad", "furious", "annoyed", "frustrated", "rage"],
        "happy": ["happy", "great", "amazing", "wonderful", "fantastic", "joyful"],
        "stressed": ["stressed", "overwhelmed", "pressure", "too much", "burnout"],
        "bored": ["bored", "boring", "nothing to do", "dull"],
        "lonely": ["lonely", "alone", "no one", "isolated", "miss"],
        "excited": ["excited", "can't wait", "thrilled", "pumped", "hyped"],
        "tired": ["tired", "exhausted", "sleepy", "drained", "fatigue"],
    }
    
    text_lower = text.lower()
    for mood, keywords in mood_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return mood
    return None


def update_streak(memory: Dict) -> Dict:
    """Update user's conversation streak."""
    today = str(datetime.date.today())
    last = memory.get("last_seen")
    
    if last is None:
        memory["streak"] = 1
    elif last == today:
        pass  # Already talked today
    elif last == str(datetime.date.today() - datetime.timedelta(days=1)):
        memory["streak"] = memory.get("streak", 0) + 1
    else:
        memory["streak"] = 1  # Streak broken
    
    memory["last_seen"] = today
    return memory


def get_streak_message(memory: Dict) -> str:
    """Get streak message."""
    streak = memory.get("streak", 1)
    if streak == 1:
        return ""
    elif streak < 5:
        return f" 🔥 We've talked {streak} days in a row!"
    elif streak < 10:
        return f" 🔥🔥 {streak}-day streak! You're consistent!"
    else:
        return f" 🔥🔥🔥 {streak} days straight! I love that you keep coming back!"


def get_time_greeting() -> str:
    """Get time-based greeting."""
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    elif hour < 21:
        return "Good evening"
    else:
        return "Hey, up late?"


def get_proactive_opener(memory: Dict) -> str:
    """Bring up something from memory to show you remember."""
    checks = []
    
    # Check birthday
    if memory.get("birthday"):
        try:
            bday = datetime.datetime.strptime(memory["birthday"], "%Y-%m-%d")
            today = datetime.date.today()
            if bday.month == today.month and bday.day == today.day:
                name = memory.get("nickname") or memory.get("name") or ""
                checks.append(f"🎂 Happy Birthday{', ' + name if name else ''}!! I remembered!")
            elif bday.month == today.month and bday.day - today.day <= 7:
                days_left = bday.day - today.day
                checks.append(f"Your birthday is in {days_left} days! Exciting! 🎉")
        except Exception:
            pass
    
    # Check recent mood
    if memory.get("mood_history"):
        last_mood = memory["mood_history"][-1]
        if last_mood in ["sad", "tired", "stressed", "anxious"]:
            checks.append(f"Last time you seemed {last_mood}. How are you feeling today?")
    
    # Check goals
    if memory.get("goals"):
        goal = random.choice(memory["goals"])
        checks.append(f"How's your goal going — '{goal}'? Still at it?")
    
    return random.choice(checks) if checks else ""


def generate_conversational_response(user_message: str, user_id: int, user_name: str = "Friend") -> str:
    """
    Generate a conversational response with memory integration.
    
    Args:
        user_message: User's input message
        user_id: User's ID for memory tracking
        user_name: User's name for personalization
    
    Returns:
        Conversational response
    """
    # Load user memory
    memory = load_user_memory(user_id)
    memory["conversation_count"] = memory.get("conversation_count", 0) + 1
    
    # Update streak
    memory = update_streak(memory)
    
    user_input_lower = user_message.lower()
    name = memory.get("name") or ""
    nickname = memory.get("nickname") or name
    greeting = f"{nickname}, " if nickname else ""
    
    # ── "Nothing" / negative responses to chatbot's questions ──────────────
    nothing_phrases = [
        "nothing", "idk", "i don't know", "not sure", "no idea",
        "nothing really", "nothing much", "not really", "nope", "none"
    ]
    
    if user_input_lower.strip() in nothing_phrases or user_input_lower.strip().startswith("nothing"):
        # Check what the last mood was to tailor the response
        last_mood = memory["mood_history"][-1] if memory.get("mood_history") else None
        
        nothing_responses = [
            # Gentle pushback — best friend doesn't just accept "nothing"
            "Nothing at all? Not even a good cup of tea, a funny video, a comfortable silence? "
            "Sometimes the smallest things count — like just waking up and it not being Monday. 😄",
            
            "Come on, nothing? Even on a rough day there's usually one tiny thing. "
            "A good song? Fresh air? Someone holding a door open? Think hard. 😊",
            
            "I don't buy 'nothing'. Sometimes we're so used to the good stuff we stop noticing it. "
            "What happened today, even if it was small?",
            
            "Hmm. That tells me something — when nothing feels good, that's worth talking about. "
            "How long have you been feeling that way?",
            
            "Nothing? Okay, that's actually important. Are you doing okay? "
            "Sometimes 'nothing' means things are harder than usual.",
        ]
        
        # If they were recently sad/tired/stressed, go deeper
        if last_mood in ["sad", "tired", "stressed", "lonely", "anxious"]:
            name_part = memory.get("nickname") or memory.get("name") or ""
            save_user_memory(user_id, memory)
            return (
                f"{'Hey ' + name_part + ', ' if name_part else 'Hey, '}"
                "when someone says nothing has made them smile lately, I take that seriously. "
                "Are you going through a rough patch right now? "
                "You don't have to have it all together — not with me."
            )
        
        save_user_memory(user_id, memory)
        return random.choice(nothing_responses)
    
    # ── Short affirmations — don't bombard them with questions ──────────────
    short_affirmations = [
        "yeah", "yep", "ok", "okay", "sure", "hm", "hmm",
        "i see", "right", "true", "makes sense", "lol", "haha"
    ]
    
    if user_input_lower.strip() in short_affirmations:
        gentle_responses = [
            "I'm here. Take your time. 💙",
            "No rush. Whenever you're ready to talk, I'm listening.",
            "I hear you.",
            "That's okay. You don't have to have the words right now.",
            "Just know I'm not going anywhere. 😊",
        ]
        save_user_memory(user_id, memory)
        return gentle_responses[memory["conversation_count"] % len(gentle_responses)]
    
    # Learn name
    if "my name is" in user_input_lower:
        name = user_message.split("my name is")[-1].strip().title()
        memory["name"] = name
        save_user_memory(user_id, memory)
        return f"Nice to meet you, {name}! 😊 Can I give you a nickname, or do you prefer {name}?"
    
    # Learn nickname
    if "call me" in user_input_lower:
        nickname = user_message.lower().split("call me")[-1].strip().title()
        memory["nickname"] = nickname
        save_user_memory(user_id, memory)
        return f"Got it! I'll call you {nickname} from now on. 😄"
    
    # Learn age
    if "i am" in user_input_lower and "years old" in user_input_lower:
        try:
            age = int(''.join(filter(str.isdigit, user_message)))
            memory["age"] = age
            save_user_memory(user_id, memory)
            return f"{age}? Nice! What's the best thing about being {age}?"
        except Exception:
            pass
    
    # Learn birthday
    if "my birthday is" in user_input_lower:
        bday_str = user_message.lower().split("my birthday is")[-1].strip()
        try:
            bday = datetime.datetime.strptime(bday_str, "%Y-%m-%d").date()
            memory["birthday"] = str(bday)
            save_user_memory(user_id, memory)
            return f"I'll never forget it! 🎂 {bday.strftime('%B %d')} is marked in my memory!"
        except Exception:
            return "I'd love to remember your birthday! Tell me in YYYY-MM-DD format."
    
    # Learn preferences
    if "i like" in user_input_lower or "i love" in user_input_lower:
        split_word = "i like" if "i like" in user_input_lower else "i love"
        preference = user_input_lower.split(split_word)[-1].strip()
        if preference not in memory["preferences"]:
            memory["preferences"].append(preference)
            save_user_memory(user_id, memory)
        return f"Oh nice, {preference}! I'll remember that. What got you into it?"
    
    # Learn dislikes
    if "i hate" in user_input_lower or "i don't like" in user_input_lower or "i dislike" in user_input_lower:
        for phrase in ["i hate", "i don't like", "i dislike"]:
            if phrase in user_input_lower:
                dislike = user_input_lower.split(phrase)[-1].strip()
                if dislike not in memory["dislikes"]:
                    memory["dislikes"].append(dislike)
                    save_user_memory(user_id, memory)
                return f"Noted — I won't bring up {dislike}. What bothers you about it?"
    
    # Learn goals
    if "my goal is" in user_input_lower or "i want to" in user_input_lower:
        split_word = "my goal is" if "my goal is" in user_input_lower else "i want to"
        goal = user_input_lower.split(split_word)[-1].strip()
        if goal not in memory["goals"]:
            memory["goals"].append(goal)
            save_user_memory(user_id, memory)
        return f"I love that! '{goal.title()}' — that's a solid goal. What's your first step?"
    
    # Learn worries
    if "i'm worried about" in user_input_lower or "i worry about" in user_input_lower:
        split_word = "i'm worried about" if "i'm worried about" in user_input_lower else "i worry about"
        worry = user_input_lower.split(split_word)[-1].strip()
        if worry not in memory["worries"]:
            memory["worries"].append(worry)
            save_user_memory(user_id, memory)
        return f"That's a real thing to worry about. What's the worst that could happen? Sometimes naming it helps."
    
    # Recall memory
    if "what do you remember" in user_input_lower:
        prefs = ", ".join(memory["preferences"]) if memory["preferences"] else "nothing yet"
        dislikes = ", ".join(memory["dislikes"]) if memory["dislikes"] else "nothing yet"
        goals = ", ".join(memory["goals"]) if memory["goals"] else "none shared yet"
        return (
            f"Here's what I know about you:\n"
            f"  Name: {memory.get('nickname') or memory.get('name') or 'not told yet'}\n"
            f"  Age: {memory.get('age') or 'unknown'}\n"
            f"  You like: {prefs}\n"
            f"  You dislike: {dislikes}\n"
            f"  Your goals: {goals}\n"
            f"  Facts shared: {len(memory['facts'])}\n"
            f"  Conversations: {memory['conversation_count']}\n"
            f"  Our streak: {memory.get('streak', 1)} day(s) 🔥"
        )
    
    # Quote request
    if "quote" in user_input_lower or "motivate" in user_input_lower or "inspire" in user_input_lower:
        save_user_memory(user_id, memory)
        return f"Here's one for you:\n\n✨ *\"{random.choice(QUOTES)}\"*\n\nWhat does that bring up for you?"
    
    # Compliment request
    if "compliment" in user_input_lower or "say something nice" in user_input_lower:
        memory["compliments_given"] = memory.get("compliments_given", 0) + 1
        save_user_memory(user_id, memory)
        return random.choice(COMPLIMENTS)
    
    # Unsolicited compliment every 10 messages
    if memory["conversation_count"] % 10 == 0:
        save_user_memory(user_id, memory)
        return random.choice(COMPLIMENTS) + " Anyway, what were you saying?"
    
    # Mood detection
    mood = detect_mood(user_input_lower)
    if mood:
        memory["mood_history"].append(mood)
        if len(memory["mood_history"]) > 20:
            memory["mood_history"] = memory["mood_history"][-20:]
        save_user_memory(user_id, memory)
        return greeting + random.choice(EMPATHY_RESPONSES[mood])
    
    # How are you
    if "how are you" in user_input_lower:
        save_user_memory(user_id, memory)
        return f"I'm great, thanks for asking! 😊 But more importantly — how are YOU doing, {greeting or 'friend'}?"
    
    # Goodbye
    if any(w in user_input_lower for w in ["good night", "bye", "goodbye", "see you", "gotta go"]):
        streak = memory.get("streak", 1)
        name_part = greeting.strip(", ") or "friend"
        save_user_memory(user_id, memory)
        return f"Goodnight, {name_part}! 💙 Day {streak} of our streak. Come back soon — I'll be here!"
    
    # Good morning
    if any(w in user_input_lower for w in ["good morning", "morning"]):
        save_user_memory(user_id, memory)
        return f"Good morning! ☀️ How'd you sleep? Ready to take on the day?"
    
    # Preference-based engagement
    if memory["preferences"]:
        topic = random.choice(memory["preferences"])
        follow_ups = [
            f"You've mentioned you enjoy {topic}. What's something new about it lately?",
            f"Still into {topic}? What's the best part about it right now?",
            f"Random thought — how's {topic} going for you these days?",
        ]
        save_user_memory(user_id, memory)
        return greeting + random.choice(follow_ups)
    
    # Goal check-in
    if memory.get("goals") and random.random() < 0.3:
        goal = random.choice(memory["goals"])
        save_user_memory(user_id, memory)
        return greeting + f"Hey, how's '{goal}' coming along? Any progress?"
    
    # Default engaging response
    save_user_memory(user_id, memory)
    return greeting + random.choice(DEFAULT_FOLLOWUPS)

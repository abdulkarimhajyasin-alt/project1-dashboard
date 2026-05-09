from urllib.parse import quote

from app.config import get_settings


PLATFORM_NAME = get_settings().app_name or "NovaHash"
PLATFORM_TAGLINE = "Daily Mining Network"


def build_referral_share_context(referral_url: str) -> dict[str, str]:
    telegram_text = f"""🚀 بدأت الآن على {PLATFORM_NAME}

منصة تعدين يومي بنظام إحالات ذكي متعدد المستويات.

💎 ابدأ دورة التعدين اليومية الخاصة بك.
👥 ابنِ شبكتك واربح من نشاط فريقك.
📈 كلما كبر فريقك، ارتفعت رتبتك وزادت قوة شبكتك.

ابدأ الآن من رابط الدعوة الخاص بي 👇"""

    invite_message = f"{telegram_text}\n{referral_url}"

    encoded_message = quote(invite_message, safe="")
    encoded_referral_url = quote(referral_url, safe="")
    encoded_telegram_text = quote(telegram_text, safe="")
    encoded_facebook_quote = quote(invite_message, safe="")

    return {
        "invite_message": invite_message,
        "whatsapp_share_url": f"https://wa.me/?text={encoded_message}",
        "telegram_share_url": f"https://t.me/share/url?url={encoded_referral_url}&text={encoded_telegram_text}",
        "facebook_share_url": (
            f"https://www.facebook.com/sharer/sharer.php?u={encoded_referral_url}"
            f"&quote={encoded_facebook_quote}"
        ),
    }

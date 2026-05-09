from app.config import get_settings


PLATFORM_NAME = get_settings().app_name or "NovaHash"
PLATFORM_TAGLINE = "Daily Mining Network"


def build_referral_messages(referral_url: str) -> dict[str, str]:
    full_message = f"""🚀 انضم إلى {PLATFORM_NAME} وابدأ دورة التعدين اليومية الخاصة بك الآن.

💎 احصل على أرباح يومية من التعدين النشط.
👥 ابنِ شبكتك الخاصة واربح من نشاط فريقك عبر نظام الإحالات متعدد المستويات.
⚡ كل شخص تدعوه يزيد من قوة شبكتك ودخلك اليومي.

🔗 رابط الدعوة الخاص بي:
{referral_url}

⏳ كلما بدأت مبكراً، بنيت شبكة أكبر ووصلت إلى رتب أعلى داخل المنصة."""

    short_message = f"""🔥 بدأت الآن على {PLATFORM_NAME}.

المنصة تعتمد على التعدين اليومي وبناء شبكة إحالات ذكية متعددة المستويات ⚡

💰 كل شخص ينضم من خلالك ويبدأ التعدين يضيف دخلاً متراكماً لشبكتك.
📈 كلما كبر فريقك، ارتفعت رتبتك وزادت قوة أرباحك.

ابدأ الآن وابنِ شبكتك قبل الجميع 👇

🔗 {referral_url}"""

    return {
        "full": full_message,
        "short": short_message,
    }

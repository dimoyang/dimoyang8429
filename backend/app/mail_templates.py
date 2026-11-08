"""重置密码邮件的多语言模板：HTML + 纯文本双版本。

语言取自用户 `preferred_language`，未知值（含 `zh-CN` 这类地区变体）会归一到
支持的主语言，仍不认识则回退英文。模板只包含固定文案与一次性链接，
不拼接任何用户可控的富文本，HTML 中的链接统一做转义。
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

SUPPORTED_MAIL_LANGUAGES = ("en", "zh", "de", "fr")


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


_TEMPLATES: dict[str, dict[str, str]] = {
    "en": {
        "subject": "Reset your MediTour password",
        "heading": "Reset your password",
        "intro": (
            "We received a request to reset the password for your "
            "MediTour account."
        ),
        "cta": "Reset password",
        "expiry": (
            "This link expires in {minutes} minutes and can only be "
            "used once."
        ),
        "ignore": (
            "If you did not request a password reset, you can safely "
            "ignore this email."
        ),
        "footer": "MediTour will never ask you for your password by email.",
    },
    "zh": {
        "subject": "重置你的 MediTour 密码",
        "heading": "重置密码",
        "intro": "我们收到了重置你的 MediTour 账户密码的请求。",
        "cta": "重置密码",
        "expiry": "该链接将在 {minutes} 分钟后失效，且只能使用一次。",
        "ignore": "如果这不是你本人的操作，可以忽略这封邮件，密码不会改变。",
        "footer": "MediTour 不会通过邮件索取你的密码。",
    },
    "de": {
        "subject": "MediTour-Passwort zurücksetzen",
        "heading": "Passwort zurücksetzen",
        "intro": (
            "Wir haben eine Anfrage erhalten, das Passwort für dein "
            "MediTour-Konto zurückzusetzen."
        ),
        "cta": "Passwort zurücksetzen",
        "expiry": (
            "Dieser Link ist {minutes} Minuten gültig und kann nur "
            "einmal verwendet werden."
        ),
        "ignore": (
            "Wenn du dies nicht angefordert hast, kannst du diese "
            "E-Mail ignorieren."
        ),
        "footer": (
            "MediTour fragt dich niemals per E-Mail nach deinem Passwort."
        ),
    },
    "fr": {
        "subject": "Réinitialiser votre mot de passe MediTour",
        "heading": "Réinitialiser votre mot de passe",
        "intro": (
            "Nous avons reçu une demande de réinitialisation du mot de "
            "passe de votre compte MediTour."
        ),
        "cta": "Réinitialiser le mot de passe",
        "expiry": (
            "Ce lien expire dans {minutes} minutes et ne peut être "
            "utilisé qu'une seule fois."
        ),
        "ignore": (
            "Si vous n'êtes pas à l'origine de cette demande, ignorez "
            "cet e-mail."
        ),
        "footer": (
            "MediTour ne vous demandera jamais votre mot de passe "
            "par e-mail."
        ),
    },
}


def normalize_mail_language(language: str | None) -> str:
    """`zh-CN` / `de_DE` 归一到 `zh` / `de`；不认识的回退 `en`。"""
    candidate = (language or "").strip().lower().replace("_", "-").split("-")[0]
    return candidate if candidate in _TEMPLATES else "en"


def render_password_reset(
    language: str | None, reset_url: str, minutes: int
) -> RenderedEmail:
    lang = normalize_mail_language(language)
    strings = _TEMPLATES[lang]
    expiry = strings["expiry"].format(minutes=minutes)

    text = "\n".join(
        [
            strings["intro"],
            "",
            f"{strings['cta']}: {reset_url}",
            "",
            expiry,
            "",
            strings["ignore"],
            "",
            strings["footer"],
            "",
        ]
    )

    safe_url = escape(reset_url, quote=True)
    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(strings['subject'])}</title>
</head>
<body style="margin:0;padding:24px;background:#f5f6f8;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:#1f2933;">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:8px;padding:28px;">
    <p style="margin:0 0 8px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#6b7280;">MediTour</p>
    <h1 style="margin:0 0 16px;font-size:22px;">{escape(strings['heading'])}</h1>
    <p style="margin:0 0 20px;line-height:1.6;">{escape(strings['intro'])}</p>
    <p style="margin:0 0 24px;">
      <a href="{safe_url}" style="display:inline-block;padding:12px 20px;background:#0f766e;color:#ffffff;border-radius:6px;text-decoration:none;font-weight:600;">{escape(strings['cta'])}</a>
    </p>
    <p style="margin:0 0 12px;line-height:1.6;color:#4b5563;">{escape(expiry)}</p>
    <p style="margin:0 0 12px;line-height:1.6;color:#4b5563;">{escape(strings['ignore'])}</p>
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
    <p style="margin:0;font-size:12px;line-height:1.6;color:#6b7280;">{escape(strings['footer'])}</p>
    <p style="margin:12px 0 0;font-size:12px;line-height:1.6;color:#9ca3af;word-break:break-all;">{safe_url}</p>
  </div>
</body>
</html>
"""
    return RenderedEmail(subject=strings["subject"], text=text, html=html)

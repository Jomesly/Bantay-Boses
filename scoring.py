"""Combines rule-layer and LLM results into a final verdict.

combine(rule_result, llm_result) -> {
    "level": "red"|"yellow"|"green",
    "score": 0-100,
    "flags": [...],
    "explanation": str,
    "what_to_do": str,
    "llm_used": bool,
}
"""
from __future__ import annotations

# Flags that must never produce a green verdict (forced to at least yellow)
FORCE_YELLOW = {
    "otp_request", "lookalike_domain", "fake_subdomain_link",
    "ip_address_link", "disguised_link_text", "displayed_url_mismatch",
    "display_name_spoof", "lookalike_sender_domain", "reply_to_mismatch",
    "http_credential_page", "risky_attachment", "punycode_domain",
    "job_scam", "legal_threat",
}

REDFLAG_EXPLANATIONS = {
    "otp_request":
        "Hiningi ang iyong OTP/PIN/password — hindi kailanman hinihingi ito ng "
        "lehitimong bangko o app.",
    "lookalike_domain":
        "Peke ang link — mukhang sikat na brand pero iba ang totoong domain nito.",
    "fake_subdomain_link":
        "Nakatago ang pekeng site sa loob ng link (brand sa harap, ibang domain sa dulo).",
    "disguised_link_text":
        "Iba ang nakasulat sa link kung saan talaga ito pupunta.",
    "displayed_url_mismatch":
        "Ipinapakita ang isang address ngunit ang totoong link ay iba.",
    "display_name_spoof":
        "Ang pangalan ng sender ay mukhang brand, pero hindi tugma ang sender domain.",
    "lookalike_sender_domain":
        "Peke ang sender domain — mukhang totoo pero may mali sa spelling.",
    "reply_to_mismatch":
        "Iba ang Reply-To sa From address — klasikong taktika ng phishing.",
    "ip_address_link":
        "Direktang IP address ang link sa halip na opisyal na website.",
    "http_credential_page":
        "Naka-http (hindi secure) ang link na humihingi ng account details.",
    "risky_attachment":
        "May mapanganib na attachment (maaaring maglaman ng virus).",
    "punycode_domain":
        "Gamit ang punycode ang link — maaaring pekeng bersyon ng totoong site.",
    "otp_request_share": "",
    "urgency":
        "May urgency at pressure tactics — ginagawa ito para hindi ka makapag-isip.",
    "fake_prize":
        "Masyadong maganda para maging totoo — pekeng premyo o reward.",
    "job_scam":
        "Kilalang pattern ng job scam (per task / daily payout / registration fee).",
    "shortened_link":
        "Naka-shorten ang link — hindi mo makikita kung saan ka pupunta.",
    "brand_name_mismatch":
        "Nabanggit ang brand sa mensahe pero hindi tugma ang domain ng link.",
    "risky_tld":
        "Bahagyang panganib ang TLD ng link (.xyz, .top, atbp.) na madalas sa scam.",
    "generic_greeting_verify":
        "Pangkalahatang greeting + hinihingiang i-verify ang account — hindi gawaan ng "
        "lehitimong kumpanya.",
    "risky_domain_tld": "",
    "click_request":
        "Hinihiking pindutin o tawagan agad — tipikal na scam move.",
    "obfuscated_url":
        "Sinasadyang binago ang URL (hxxp, [.] ) para makaiwas sa filter.",
    "plain_http_link":
        "Walang HTTPS ang link — hindi secure na koneksyon.",
    "payment_request":
        "Hinihingiang magbayad o magpadala ng pera — kilalang scam tactic.",
    "money_transfer":
        "Hinihingiang magpadala ng pera o load sa numero/GCash — karaniwan itong "
        "modus lalo na sa mga pekeng tulong o pa-premyo.",
    "legal_threat":
        "Paggamit ng takot (kaso, warrant) para pilitin kang magpadala ng pera "
        "agad — hindi gawaan ng totoong ahensya.",
}

WHAT_TO_DO_BY_FLAG = {
    "otp_request": ("red",
        "I-delete agad. HUWAG kailanman magpadala ng OTP/PIN sa sinuman — kahit "
        "nagpapakilala silang bangko. Tatawag ang totoong bangko para sa support, "
        "hindi hihingi ng code via text."),
    "lookalike_domain": ("red",
        "Huwag i-click ang link. Buksan ang opisyal na app ng iyong bangko/wallet "
        "nang hiwalay, o i-type mismo ang opisyal na website."),
    "fake_subdomain_link": ("red",
        "Huwag i-click. Peke ang link kahit mukhang kilalang brand."),
    "disguised_link_text": ("red",
        "Huwag i-click — iba ang totoong pinupuntahan ng link kaysa sa nakasulat."),
    "displayed_url_mismatch": ("red",
        "Huwag i-click — iba ang totoong link sa ipinapakitang address."),
    "display_name_spoof": ("red",
        "Huwag mag-reply. Mag-login sa opisyal na app/website nang hiwalay para "
        "i-check ang totoong status ng account mo."),
    "reply_to_mismatch": ("red",
        "Huwag mag-reply sa Reply-To address. Ang sagot mo ay mapupunta sa iba."),
    "ip_address_link": ("red",
        "Huwag i-click — hindi ito opisyal na website ng kahit anong brand."),
    "risky_attachment": ("red",
        "Huwag i-download o i-open ang attachment. Burahin ang email."),
    "otp_request_force": ("red", ""),
    "generic_greeting_verify": ("yellow",
        "I-verify sa opisyal na app kung totoong may problema sa account mo. "
        "Huwag mag-click ng link sa mensahe."),
    "urgency": ("yellow",
        "Huwag magmadali. Tingnan muna sa opisyal na app kung totoo ang babala."),
    "fake_prize": ("yellow",
        "Masyadong maganda para maging totoo. Huwag magbigay ng personal na detalye "
        "para sa 'premyo'."),
    "job_scam": ("yellow",
        "Huwag magbayad ng registration fee. Tunay na trabaho ay hindi hihingi ng "
        "pera mula sa iyo."),
    "payment_request": ("yellow",
        "Huwag magpadala ng pera base sa mensahe na ito. I-verify muna sa opisyal "
        "na channel kung totoo ang utang o bayarin."),
    "money_transfer": ("red",
        "Huwag magpadala ng pera o OTP. Totoong ahensya at kumpanya ay hindi "
        "humihingi ng padala via text o GCash."),
    "legal_threat": ("red",
        "Huwag magpadala ng pera. Ang totoong korte o ahensya ay hindi nagbabanta "
        "o humihingi ng bayad via text. Kung may alanganin, tumawag sa opisyal na "
        "hotline o sa pulisya."),
    "shortened_link": ("yellow",
        "Ilagay muna ang link sa isang checker o iwasan — hindi mo alam kung saan "
        "ito pupunta."),
    "risky_tld": ("yellow",
        "Mag-ingat sa link na ito. Buksan lang ang opisyal na site mismo."),
}

DEFAULT_WHAT_TO_DO = ("yellow",
    "Huwag mag-click ng link o magbigay ng personal na impormasyon. I-verify muna "
    "sa opisyal na app o tumawag sa opisyal na hotline ng bangko/app.")


def _rule_fallback_explanation(flags: list[dict]) -> str:
    lines = []
    for f in flags[:3]:
        line = REDFLAG_EXPLANATIONS.get(f["name"])
        if line:
            lines.append(line)
    if not lines:
        return ("Walang nakitang malinaw na scam pattern sa mensahe, pero mag-ingat "
                "pa rin at i-verify sa opisyal na channel.")
    return " ".join(lines)


def _what_to_do(flags: list[dict]) -> str:
    priority = {"red": 0, "yellow": 1, "green": 2}
    best: tuple[int, str] | None = None
    for f in flags:
        entry = WHAT_TO_DO_BY_FLAG.get(f["name"])
        if entry:
            level, action = entry
            if priority[level] < (best[0] if best else 9):
                best = (priority[level], action)
    if best is None:
        if flags:
            level, action = DEFAULT_WHAT_TO_DO
            return action
        return ("Walang kailangang gawin — mukhang lehitimo ang mensahe. "
                "Mag-ingat pa rin sa pag-click ng mga link.")
    return best[1]


def combine(rule_result: dict, llm_result: dict | None) -> dict:
    flags = list((rule_result or {}).get("flags", []))
    score = int((rule_result or {}).get("score", 0))

    llm_used = False
    explanation = ""
    if llm_result:
        llm_used = True
        verdict = llm_result.get("verdict")
        score += {"scam": 40, "suspicious": 20, "safe": 0}.get(verdict, 0)
        if verdict == "safe" and score <= 5:
            score = max(0, score - 10)  # confident clean bills stay green
        explanation = llm_result.get("explanation", "")

    score = max(0, min(100, score))

    level = "green"
    if score >= 70:
        level = "red"
    elif score >= 35:
        level = "yellow"

    # hard floor: severe flags never get a green verdict
    if any(f["name"] in FORCE_YELLOW for f in flags) and level == "green":
        level = "yellow"
        score = max(score, 35)

    if not explanation:
        explanation = _rule_fallback_explanation(flags)

    return {
        "level": level,
        "score": score,
        "flags": flags,
        "explanation": explanation,
        "what_to_do": _what_to_do(flags),
        "llm_used": llm_used,
    }

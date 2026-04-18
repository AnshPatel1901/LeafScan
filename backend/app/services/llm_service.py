"""
LLM Service — generates disease explanation and precautions.

Uses Groq LLM (llama-3.1-70b-versatile) as primary backend.
Falls back to Gemini Flash on failure.
Supports multilingual responses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.tts_service import get_tts_service

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)

# Supported language codes
SUPPORTED_LANGUAGES = {
    "en", "hi", "ta", "te", "mr", "bn", "gu", "kn", "ml", "pa",
    "fr", "es", "de", "zh", "ar", "pt", "it", "ja", "ko"
}


# ── Data contract ─────────────────────────────────────────────────────────────


@dataclass
class LLMResult:
    """Result of LLM generation with optional audio output."""
    precautions_text: str
    audio_url: Optional[str] = None


# ── Service ───────────────────────────────────────────────────────────────────


class LLMService:
    """
    Generates agronomic explanations and precautions for detected diseases.

    Features:
        • Primary: Groq LLM (llama-3.1-70b-versatile) for better quality
        • Fallback: Gemini Flash on Groq failure
        • Multilingual: Supports 19+ languages
        • Dynamic Generation: Fresh content every request (no caching)
        • Error Handling: Comprehensive logging and error recovery
    """

    def __init__(
        self,
        groq_api_key: str = settings.GROQ_API_KEY,
        groq_model: str = settings.GROQ_MODEL,
        groq_api_url: str = settings.GROQ_API_URL,
        gemini_api_key: str = settings.GEMINI_API_KEY,
        gemini_model: str = settings.GEMINI_MODEL,
        gemini_api_url: str = settings.GEMINI_API_URL,
    ) -> None:
        self._groq_api_key = groq_api_key
        self._groq_model = groq_model
        self._groq_api_url = groq_api_url
        self._gemini_api_key = gemini_api_key
        self._gemini_model = gemini_model
        self._gemini_api_url = gemini_api_url
        self._tts_service = get_tts_service()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_precautions(
        self,
        plant_name: str,
        disease_name: str,
        language: str = "en",
    ) -> LLMResult:
        """
        Generate disease explanation and precautions in selected language.

        Parameters
        ----------
        plant_name : str
            Name of the plant (e.g., "Tomato", "Potato")
        disease_name : str
            Name of the detected disease
        language : str
            ISO 639-1 language code (default: "en")

        Returns
        -------
        LLMResult
            Precautions text in requested language

        Notes
        -----
        Uses 3-tier fallback:
        1. Groq LLM (primary) - Best quality, fast
        2. Gemini Flash (secondary) - Fallback if Groq fails
        3. Static text (final) - Offline advisory if both fail
        """
        # Validate and normalize language
        language = language.lower().strip() if language else "en"
        if language not in SUPPORTED_LANGUAGES:
            logger.warning("Unsupported language %s, falling back to English", language)
            language = "en"

        # Attempt Groq first (primary LLM)
        try:
            text = await self._call_groq_llm(
                plant_name=plant_name,
                disease_name=disease_name,
                language=language,
            )
            logger.info(
                "Groq LLM generation success | plant=%s disease=%s | language=%s | text_len=%d",
                plant_name, disease_name, language, len(text)
            )
            return LLMResult(precautions_text=text, audio_url=None)

        except ExternalServiceError as exc:
            logger.warning("Groq LLM failed (%s); trying Gemini fallback", exc)

        # Fallback to Gemini
        try:
            text = await self._call_gemini_llm(
                plant_name=plant_name,
                disease_name=disease_name,
                language=language,
            )
            logger.info(
                "Gemini LLM fallback success | plant=%s disease=%s | language=%s | text_len=%d",
                plant_name, disease_name, language, len(text)
            )
            return LLMResult(precautions_text=text, audio_url=None)

        except ExternalServiceError as exc:
            logger.warning("Gemini LLM also failed (%s); using static fallback", exc)

        # Final fallback to static text
        text = LLMService._static_fallback(plant_name, disease_name, language)
        logger.info(
            "Using static fallback | plant=%s disease=%s | language=%s",
            plant_name, disease_name, language
        )
        return LLMResult(precautions_text=text, audio_url=None)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_language_name(self, language: str) -> str:
        """Get full language name for system prompt."""
        language_names = {
            "en": "English",
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "mr": "Marathi",
            "bn": "Bengali",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "zh": "Chinese",
            "ar": "Arabic",
            "pt": "Portuguese",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
        }
        return language_names.get(language, "English")

    def _build_prompt(
        self, plant_name: str, disease_name: str, language: str
    ) -> str:
        """Build LLM prompt for disease precautions with comprehensive treatment instructions."""
        language_name = self._get_language_name(language)

        if disease_name.lower() == "healthy":
            return (
                f"Respond in {language_name}.\n\n"
                f"The {plant_name} plant appears HEALTHY and disease-free.\n\n"
                f"Provide comprehensive plant care advice with this structure:\n\n"
                f"**Daily Care Tips:** (4-5 practical daily maintenance steps)\n\n"
                f"**Watering Schedule:** (specific recommendations for optimal watering)\n\n"
                f"**Nutrient Management:** (fertilizer and nutrient requirements)\n\n"
                f"**Disease Prevention:** (preventive measures to keep plant healthy)\n\n"
                f"**Environmental Conditions:** (light, temperature, humidity requirements)\n\n"
                f"Use clear, actionable advice. Respond entirely in {language_name}."
            )

        return (
            f"Respond ENTIRELY in {language_name}.\n\n"
            f"PLANT: {plant_name}\n"
            f"DISEASE: {disease_name}\n\n"
            f"Generate COMPREHENSIVE disease treatment and management advice:\n\n"
            f"**🔍 Disease Identification:** (2-3 sentences: what is this disease, how it spreads, which plant parts it affects)\n\n"
            f"**⚠️ Symptoms & Signs:** (bullet list of 4-5 specific symptoms to recognize)\n\n"
            f"**🚨 Immediate Treatment Actions:** (4-5 urgent steps to prevent disease spread)\n\n"
            f"**💊 Treatment Methods:**\n"
            f"  • Organic/Biological solutions (2-3 methods with application rates)\n"
            f"  • Chemical treatments (2-3 options with dosage and frequency)\n"
            f"  • Home remedies (1-2 cost-effective solutions)\n\n"
            f"**⏰ Treatment Timeline:** (step-by-step schedule for 1-4 weeks)\n\n"
            f"**🛡️ Prevention & Control:** (5-6 preventive measures for future protection)\n\n"
            f"**⚡ Urgent Precautions:** (3-4 critical actions to take immediately)\n\n"
            f"**✅ Best Practices:** (3-4 agronomic practices for healthy crops)\n\n"
            f"**📋 Cost-Effective Tips:** (budget-friendly solutions and DIY options)\n\n"
            f"IMPORTANT: Make the response:\n"
            f"• Practical and actionable for farmers\n"
            f"• Specific with quantities and timelines\n"
            f"• Written entirely in {language_name}\n"
            f"• Include both organic and chemical options\n"
            f"• Focused on rapid disease control"
        )

    async def _call_groq_llm(
        self, plant_name: str, disease_name: str, language: str
    ) -> str:
        """
        Call Groq API (primary LLM) to generate precautions.
        
        Uses llama-3.1-70b-versatile model for better quality responses.
        """
        if not self._groq_api_key:
            raise ExternalServiceError("GROQ_API_KEY not configured")

        prompt = self._build_prompt(plant_name, disease_name, language)

        payload = {
            "model": self._groq_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are an EXPERT AGRICULTURAL EXTENSION OFFICER with 20+ years experience in crop disease management.\n\n"
                        f"YOUR EXPERTISE:\n"
                        f"• Plant pathology and disease identification\n"
                        f"• Integrated Pest Management (IPM) strategies\n"
                        f"• Organic and chemical treatment protocols\n"
                        f"• Cost-effective farming solutions\n"
                        f"• Regional crop practices and best methods\n\n"
                        f"YOUR RESPONSE MUST:\n"
                        f"1. Provide DETAILED, COMPREHENSIVE treatment advice\n"
                        f"2. Include SPECIFIC quantities, concentrations, and application rates\n"
                        f"3. Cover BOTH organic and chemical solutions\n"
                        f"4. Give CLEAR TIMELINE and frequency of treatments\n"
                        f"5. Include PRACTICAL HOME REMEDIES where applicable\n"
                        f"6. Respond ENTIRELY in {self._get_language_name(language)} language\n"
                        f"7. Make advice suitable for both smallholder and commercial farmers\n\n"
                        f"ALWAYS focus on: rapid disease control, cost-effectiveness, and sustainable practices."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {self._groq_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(self._groq_api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            # Extract text from Groq response
            response_text = data["choices"][0]["message"]["content"].strip()
            logger.debug("Groq API response: %d characters", len(response_text))
            return response_text

        except httpx.HTTPStatusError as exc:
            logger.error("Groq API HTTP error: %s", exc.response.text)
            raise ExternalServiceError(f"Groq API error ({exc.response.status_code}): {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("Groq API request failed: %s", exc)
            raise ExternalServiceError(f"Groq API request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected Groq response structure: %s", exc)
            raise ExternalServiceError(
                f"Unexpected Groq response structure: {exc}"
            ) from exc

    async def _call_gemini_llm(
        self, plant_name: str, disease_name: str, language: str
    ) -> str:
        """
        Call Gemini API (fallback LLM) to generate precautions.
        
        Only used if Groq fails.
        """
        if not self._gemini_api_key:
            raise ExternalServiceError("GEMINI_API_KEY not configured")

        prompt = self._build_prompt(plant_name, disease_name, language)
        language_name = self._get_language_name(language)

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"You are an EXPERT AGRICULTURAL EXTENSION OFFICER with extensive crop disease management experience.\n\n"
                                f"YOUR EXPERTISE: Plant pathology, IPM strategies, organic/chemical treatments, cost-effective solutions.\n\n"
                                f"PROVIDE:\n"
                                f"• DETAILED comprehensive treatment advice\n"
                                f"• SPECIFIC quantities and application rates\n"
                                f"• BOTH organic and chemical solutions\n"
                                f"• CLEAR TIMELINE for treatments\n"
                                f"• PRACTICAL HOME REMEDIES\n\n"
                                f"RESPOND ENTIRELY IN {language_name}.\n\n"
                                f"{prompt}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            },
        }

        url = f"{self._gemini_api_url}/{self._gemini_model}:generateContent?key={self._gemini_api_key}"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.debug("Gemini API response: %d characters", len(response_text))
            return response_text

        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API HTTP error: %s", exc.response.text)
            raise ExternalServiceError(f"Gemini API error ({exc.response.status_code}): {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("Gemini API request failed: %s", exc)
            raise ExternalServiceError(f"Gemini API request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected Gemini response structure: %s", exc)
            raise ExternalServiceError(
                f"Unexpected Gemini response structure: {exc}"
            ) from exc

    @staticmethod
    def _static_fallback(plant_name: str, disease_name: str, language: str) -> str:
        """
        Return a practical offline advisory when all LLMs fail.
        
        Provides multilingual fallback text with 10-15 line disease management plans.
        Supports: English, Hindi, Gujarati, Tamil, and fallback languages.
        """
        disease = disease_name.strip()
        disease_lower = disease.lower()

        # English fallback
        if language == "en":
            if disease_lower == "healthy":
                return (
                    f"✓ Your {plant_name} plant looks healthy.\n\n"
                    "**Disease Prevention Tips:**\n"
                    "1. Water at soil level early morning to keep foliage dry\n"
                    "2. Maintain 6-12 inches spacing between plants for air circulation\n"
                    "3. Scout plants 2-3 times per week for early symptoms\n"
                    "4. Remove dead leaves and debris promptly from fields\n"
                    "5. Use clean, sanitized tools when pruning or harvesting\n"
                    "6. Rotate crops yearly to break disease cycles\n"
                    "7. Apply neem oil spray monthly as preventive measure"
                )
            else:
                return (
                    f"⚠ Disease detected: **{disease}** on {plant_name}\n\n"
                    "**Immediate Action Plan:**\n"
                    "1. Isolate affected plants from healthy ones immediately\n"
                    "2. Remove all infected leaves using sterilized pruning tools\n"
                    "3. Dispose infected material away from field (do not compost)\n"
                    "4. Avoid overhead irrigation; use drip irrigation only\n"
                    "5. Reduce plant density to improve air flow\n"
                    "6. Apply fungicide/neem oil every 7-10 days\n"
                    "7. Monitor weather conditions closely\n"
                    "8. Consult local agronomist for approved chemical treatments\n"
                    "9. Keep detailed records of symptoms and treatments\n"
                    "10. Limit field activities during wet weather to prevent spread"
                )

        # Hindi fallback
        elif language == "hi":
            if disease_lower == "healthy":
                return (
                    f"✓ आपका {plant_name} पौधा स्वस्थ दिख रहा है।\n\n"
                    "**रोग निवारण सुझाव:**\n"
                    "1. सुबह जल्दी जड़ों को पानी दें, पत्तियां सूखी रहें\n"
                    "2. पौधों के बीच 6-12 इंच की दूरी हवा के लिए रखें\n"
                    "3. साप्ताहिक 2-3 बार रोग के शुरुआती संकेत देखें\n"
                    "4. मृत पत्तियों और कचरे को तुरंत हटाएं\n"
                    "5. छंटाई के समय साफ उपकरणों का उपयोग करें\n"
                    "6. हर साल फसल बदलें रोग चक्र तोड़ने के लिए\n"
                    "7. महीने में एक बार नीम का तेल छिड़कें"
                )
            else:
                return (
                    f"⚠ {plant_name} में **{disease}** रोग पाया गया है\n\n"
                    "**तुरंत कार्रवाई योजना:**\n"
                    "1. प्रभावित पौधों को स्वस्थ पौधों से तुरंत अलग करें\n"
                    "2. संक्रमित पत्तियां स्वच्छ कलम से हटाएं\n"
                    "3. संक्रमित सामग्री को खेत से दूर फेंकें (खाद में न डालें)\n"
                    "4. ऊपर से पानी बिल्कुल न डालें, ड्रिप विधि अपनाएं\n"
                    "5. पौधों की घनતા कम करें हवा प्रवाह बढ़ाने के लिए\n"
                    "6. हर 7-10 दिन कवकनाशी/नीમ का तेल छिड़कें\n"
                    "7. मौसम की स्थिति पर ध्यान दें\n"
                    "8. स्थानीय कृषि विशेषज्ञ से सलाह लें\n"
                    "9. रोग के विवरण और उपचार का रिकॉर्ड रखें\n"
                    "10. बारिश में खेत में काम कम करें"
                )

        # Gujarati fallback - COMPREHENSIVE DISEASE MANAGEMENT
        elif language == "gu":
            if disease_lower == "healthy":
                return (
                    f"✓ તમારો {plant_name} છોડ સ્વસ્થ દેખાય છે।\n\n"
                    "**રોગ નિવારણ સૂચનાઓ:**\n"
                    "1. વિહાણે જલ્દી જડ પાસે પાણી આપો, પાંદડા સુકા રાખો\n"
                    "2. છોડ વચ્ચે 6-12 ઇંચ અંતર હવા માટે રાખો\n"
                    "3. હર અઠવાડિયે 2-3 વાર રોગના ચિહ્નો જુઓ\n"
                    "4. મરેલી પાંદડા અને કચરો તરત હટાવો\n"
                    "5. કાપતી વખતે સાફ સાધનો વાપરો\n"
                    "6. સાલમાં એક વાર ફસલ બદલો રોગ રોકવા માટે\n"
                    "7. મહિનામાં એક વાર નીમનું તેલ છાંટો"
                )
            else:
                return (
                    f"⚠ {plant_name} પર **{disease}** રોગ મળ્યો છે\n\n"
                    "**તાત્કાલિક પગલાં લેવાની પરિકલ્પના:**\n"
                    "1. સંક્રમિત છોડને સ્વસ્થ છોડથી તરત આલગ કરો\n"
                    "2. સ્વચ્છ કીંતણ વાપરીને સંક્રમિત પાંદડા હટાવો\n"
                    "3. સંક્રમિત સામગ્રી ખેતરથી દૂર ફેંકો (ખાદમાં ન મૂકો)\n"
                    "4. ઉપરથી પાણી આપશો નહીં, ડ્રીપ પધ્ધતિ વાપરો\n"
                    "5. છોડની ઘનતા ઘટાવો હવા પ્રવાહ માટે\n"
                    "6. દર 7-10 દિવસે ફૌન્જીસાઈડ/નીમનું તેલ છાંટો\n"
                    "7. આબોહવાની પરિસ્થિતિ ધ્યાનથી અવલોકન કરો\n"
                    "8. સ્થાનિક કૃષિ નિષ્ણાતથી માર્ગદર્શન લો\n"
                    "9. રોગ અને સારવારનો વિગતવાર રેકોર્ડ રાખો\n"
                    "10. ભારે વરસાદમાં ખેતમાં ઓછું કામ કરો\n"
                    "11. સતત નિરીક્ષણ બહુ જરૂરી છે સફળતા માટે"
                )


        # Tamil fallback
        elif language == "ta":
            if disease_lower == "healthy":
                return (
                    f"✓ உங்கள் {plant_name} செடி ஆரோக்கியமாக உள்ளது।\n\n"
                    "**நோய் தடுப்பு குறிப்புகள்:**\n"
                    "1. காலையில் நீர் வேர்களுக்கு தரவும் இலைகள் உலர்ந்திருக்க\n"
                    "2. செடிகளுக்கு 6-12 இஞ்ச் இடைவெளி வான்கட்ட\n"
                    "3. வாரத்துக்கு 2-3 முறை நோய் அறிகுறி பார்க்கவும்\n"
                    "4. இறந்த இலைகள் உடனே அகற்றவும்\n"
                    "5. கத்தி கொண்டு வெட்டும்போது சுத்தம் வாங்கவும்\n"
                    "6. ஆண்டுக்கு ஒரு முறை பயிர் மாற்றவும்\n"
                    "7. மாத மாதம் நீம் எண்ணை தெளிக்கவும்"
                )
            else:
                return (
                    f"⚠ {plant_name} இல் **{disease}** நோய் இருக்கிறது\n\n"
                    "**உடனடி நடவடிக்கை திட்டம்:**\n"
                    "1. பாதிக்கப்பட்ட செடிகளை ஆரோக்கியமான செடிகளிலிருந்து પ્રிக்கவும்\n"
                    "2. தொற்றிய இலைகளை சுத்தமான கத்தி கொண்டு அகற்றவும்\n"
                    "3. தொற்றிய பொருட்களை நிலத்திலிருந்து வெளியே எறிக்கவும்\n"
                    "4. மேலிருந்து தண்ணீர் விடாதீர்கள், ட்ரிப் நீர் பாய்ச்சல் பயன்படுத்தவும்\n"
                    "5. செடிகளுக்கு இடைவெளி விட்டு செய்யவும் காற்றோட்டத்துக்கு\n"
                    "6. 7-10 நாட்களுக்கு ஒரு முறை உளுந்து மூலிகை நீர் தெளிக்கவும்\n"
                    "7. வானிலை மாற்றத்தை கவனமாக கவனிக்கவும்\n"
                    "8. விவசாய அறிவியலாளரிடம் ஆலோசனை பெறவும்\n"
                    "9. நோய் மற்றும் சிகிச்சையின் விவரங்களைப் பதிவுசெய்க\n"
                    "10. மழை நேரத்தில் வயல் பணி செயல்பாடுகளைக் குறைக்கவும்"
                )

        # Tamil fallback
        elif language == "ta":
            if disease_lower == "healthy":
                return (
                    f"✓ உங்கள் {plant_name} செடி ஆரோக்கியமாக உள்ளது।\n\n"
                    "**நோய் தடுப்பு குறிப்புகள்:**\n"
                    "1. காலையில் நீர் வேர்களுக்கு தரவும் இலைகள் உலர்ந்திருக்க\n"
                    "2. செடிகளுக்கு 6-12 இஞ்ச் இடைவெளி வான்கட்ட\n"
                    "3. வாரத்துக்கு 2-3 முறை நோய் அறிகுறி பார்க்கவும்\n"
                    "4. இறந்த இலைகள் உடனே அகற்றவும்\n"
                    "5. கத்தி கொண்டு வெட்டும்போது சுத்தம் வாங்கவும்\n"
                    "6. ஆண்டுக்கு ஒரு முறை பயிர் மாற்றவும்\n"
                    "7. மாத மாதம் நீம் எண்ணை தெளிக்கவும்"
                )
            else:
                return (
                    f"⚠ {plant_name} இல் **{disease}** நோய் இருக்கிறது\n\n"
                    "**உடனடி நடவடிக்கை திட்டம்:**\n"
                    "1. பாதிக்கப்பட்ட செடிகளை ஆரோக்கியமான செடிகளிலிருந்து பிரிக்கவும்\n"
                    "2. தொற்றிய இலைகளை சுத்தமான கத்தி கொண்டு அகற்றவும்\n"
                    "3. தொற்றிய பொருட்களை நிலத்திலிருந்து வெளியே எறிக்கவும்\n"
                    "4. மேலிருந்து தண்ணீர் விடாதீர்கள், ட்ரிப் நீர் பாய்ச்சல் பயன்படுத்தவும்\n"
                    "5. செடிகளுக்கு இடைவெளி விட்டு செய்யவும் காற்றோட்டத்துக்கு\n"
                    "6. 7-10 நாட்களுக்கு ஒரு முறை உளுந்து மூலிகை நீர் தெளிக்கவும்\n"
                    "7. வானிலை மாற்றத்தை கவனமாக கவனிக்கவும்\n"
                    "8. விவசாய அறிவியலாளரிடம் ஆலோசனை பெறவும்\n"
                    "9. நோய் மற்றும் சிகிச்சையின் விவரங்களைப் பதிவுசெய்க\n"
                    "10. மழை நேரத்தில் வயல் பணி செயல்பாடுகளைக் குறைக்கவும்"
                )

        # Telugu, Marathi, Bengali, Kannada, Malayalam, Punjabi, French, Spanish, German, Chinese, Arabic, Portuguese, Italian, Japanese, Korean
        # Telugu
        elif language == "te":
            return (
                f"✓ విజయవంతమైన సంరక్షణ కోసం కృषిశాస్త్రవేత్తను సంప్రదించండి।\n\n"
                f"**{plant_name} - {disease}** పర్యవేక్షణ అవసరం.\n\n"
                "సాధారణ సలహాలు:\n"
                "1. సరిగ్గా ఛాయ ఇవ్వండి\n"
                "2. నుండీ నూనె ఉపయోగించండి\n"
                "3. సంక్రమిత భాగాలను తీసివేయండి"
            )
        # Marathi
        elif language == "mr":
            return (
                f"✓ यशस्वी संरक्षणासाठी कृषिशास्त्रज्ञाशी संपर्क साधा।\n\n"
                f"**{plant_name} - {disease}** निरीक्षण आवश्यक.\n\n"
                "सामान्य सूचना:\n"
                "1. योग्य सावधी ठेवा\n"
                "2. नीम तेल वापरा\n"
                "3. संक्रमित भाग काढा"
            )
        # Bengali
        elif language == "bn":
            return (
                f"✓ সফল সুরক্ষার জন্য কৃষিবিদের সাথে যোগাযোগ করুন।\n\n"
                f"**{plant_name} - {disease}** পর্যবেক্ষণ প্রয়োজন।\n\n"
                "সাধারণ পরামর্শ:\n"
                "1. যথাযথ যত্ন নিন\n"
                "2. নিম তেল ব্যবহার করুন\n"
                "3. সংক্রমিত অংশ অপসারণ করুন"
            )
        # Kannada
        elif language == "kn":
            return (
                f"✓ ಯಶಸ್ವಿ ರಕ್ಷಣೆಗಾಗಿ ಕೃಷಿ ಪರಿಣತರನ್ನು ಸಂಪರ್ಕಿಸಿ।\n\n"
                f"**{plant_name} - {disease}** ಪರ್ಯವೇಕ್ಷಣೆ ಅಗತ್ಯ.\n\n"
                "ಸಾಮಾನ್ಯ ಸಲಹೆ:\n"
                "1. ಸರಿಯಾದ ಯತ್ನ ತೆಗೆದುಕೊಳ್ಳಿ\n"
                "2. ನೀಮ್ ತೈಲ ಬಳಸಿ\n"
                "3. ಸೋಂಕಿತ ಭಾಗ ತೆಗೆದುಹಾಕಿ"
            )
        # Malayalam
        elif language == "ml":
            return (
                f"✓ വിജയകരമായ സംരക്ഷണത്തിനായി കൃഷി വിദഗ്ധരുമായി സംപര്ക്കം സാധിക്കുക।\n\n"
                f"**{plant_name} - {disease}** നിരീക്ഷണം ആവശ്യമാണ്.\n\n"
                "സാധാരണ നിര്ദ്ദേശങ്ങള്:\n"
                "1. ശരിയായ ശ്രദ്ധ എടുക്കുക\n"
                "2. നീം എണ്ണ ഉപയോഗിക്കുക\n"
                "3. രോഗബാധിത ഭാഗം നീക്കം ചെയ്യുക"
            )
        # Punjabi
        elif language == "pa":
            return (
                f"✓ ਸਫਲ ਸੁਰੱਖਿਆ ਲਈ ਕ ਰਿਸ਼ ਮਾਹਿਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।\n\n"
                f"**{plant_name} - {disease}** ਨਿਰੀਖਣ ਜ਼ਰੂਰੀ.\n\n"
                "ਆਮ ਸਲਾਹ:\n"
                "1. ਸਹੀ ਸਵਾਲ ਲਓ\n"
                "2. ਨੀਮ ਤੇਲ ਵਰਤੋ\n"
                "3. ਸੰਕ੍ਰਮਿਤ ਹਿੱਸਾ ਹਟਾਓ"
            )
        # French
        elif language == "fr":
            return (
                f"✓ Pour une protection réussie, consultez un agronome.\n\n"
                f"**{plant_name} - {disease}** Surveillance recommandée.\n\n"
                "Conseils généraux:\n"
                "1. Prenez les précautions appropriées\n"
                "2. Utilisez l'huile de neem\n"
                "3. Retirez les parties infectées"
            )
        # Spanish
        elif language == "es":
            return (
                f"✓ Para una protección exitosa, consulte a un agrónomo.\n\n"
                f"**{plant_name} - {disease}** Vigilancia recomendada.\n\n"
                "Consejos generales:\n"
                "1. Tome las precauciones apropiadas\n"
                "2. Use aceite de neem\n"
                "3. Retire las partes infectadas"
            )
        # German
        elif language == "de":
            return (
                f"✓ Für einen erfolgreichen Schutz wenden Sie sich an einen Agronomen.\n\n"
                f"**{plant_name} - {disease}** Überwachung empfohlen.\n\n"
                "Allgemeine Tipps:\n"
                "1. Treffen Sie angemessene Vorsichtsmaßnahmen\n"
                "2. Neemöl verwenden\n"
                "3. Befallene Teile entfernen"
            )
        # Chinese
        elif language == "zh":
            return (
                f"✓ 为了成功保护,请咨询农学家。\n\n"
                f"**{plant_name} - {disease}** 需要监测。\n\n"
                "一般建议:\n"
                "1. 采取适当的预防措施\n"
                "2. 使用印楝油\n"
                "3. 去除感染部分"
            )
        # Arabic
        elif language == "ar":
            return (
                f"✓ للحماية الناجحة، استشر أخصائي زراعي.\n\n"
                f"**{plant_name} - {disease}** المراقبة موصى بها.\n\n"
                "نصائح عامة:\n"
                "1. اتخذ الاحتياطات المناسبة\n"
                "2. استخدم زيت النيم\n"
                "3. أزل الأجزاء المصابة"
            )
        # Portuguese
        elif language == "pt":
            return (
                f"✓ Para uma proteção bem-sucedida, consulte um agrônomo.\n\n"
                f"**{plant_name} - {disease}** Monitoramento recomendado.\n\n"
                "Dicas gerais:\n"
                "1. Tome as precauções apropriadas\n"
                "2. Use óleo de neem\n"
                "3. Remova as partes infectadas"
            )
        # Italian
        elif language == "it":
            return (
                f"✓ Per una protezione riuscita, consultare un agronomo.\n\n"
                f"**{plant_name} - {disease}** Monitoraggio consigliato.\n\n"
                "Consigli generali:\n"
                "1. Prendi le precauzioni appropriate\n"
                "2. Usa olio di neem\n"
                "3. Rimuovi le parti infette"
            )
        # Japanese
        elif language == "ja":
            return (
                f"✓ 成功した保護のために、農学者に相談してください。\n\n"
                f"**{plant_name} - {disease}** 監視が推奨されます。\n\n"
                "一般的なヒント:\n"
                "1. 適切な予防措置を取る\n"
                "2. ニーム油を使用\n"
                "3. 感染した部分を除去"
            )
        # Korean
        elif language == "ko":
            return (
                f"✓ 성공적인 보호를 위해 농학자와 상담하세요.\n\n"
                f"**{plant_name} - {disease}** 모니터링 권장.\n\n"
                "일반적인 팁:\n"
                "1. 적절한 예방 조치 취하기\n"
                "2. 님 오일 사용\n"
                "3. 감염된 부분 제거"
            )

        # Default fallback for unsupported languages
        else:
            if disease_lower == "healthy":
                return (
                    f"{plant_name} plant is healthy.\n\n"
                    "**Care Tips:**\n"
                    "- Water at soil level in early morning\n"
                    "- Maintain proper plant spacing for air circulation\n"
                    "- Scout regularly for early disease detection\n"
                    "- Keep field clean and remove dead leaves\n"
                    "- Use sanitized tools for pruning and harvesting"
                )
            else:
                return (
                    f"Disease detected: **{disease}** on {plant_name}\n\n"
                    "**Action Plan:**\n"
                    "1. Isolate affected plants immediately\n"
                    "2. Remove infected leaves using sterilized tools\n"
                    "3. Dispose infected material away from field\n"
                    "4. Use drip irrigation to keep foliage dry\n"
                    "5. Improve plant spacing for better air flow\n"
                    "6. Apply fungicide spray every 7-10 days\n"
                    "7. Monitor weather and field conditions\n"
                    "8. Consult with local agricultural expert\n"
                    "9. Keep detailed records of disease and treatments\n"
                    "10. Reduce field activities during wet weather"
                )

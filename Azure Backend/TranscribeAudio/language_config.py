"""
Language and country configuration for speech recognition and translation.
Maps countries to their corresponding Azure Speech locale and translation source language.
"""

from typing import Dict, NamedTuple
from dataclasses import dataclass

@dataclass
class LanguageConfig:
    """Configuration for a country's language settings"""
    country_name: str
    country_code: str
    speech_locale: str  # Azure Speech recognition locale
    translate_from: str  # Source language code for translation
    translate_to: str = "en"  # Target language (default to English)
    language_name: str = ""  # Human-readable language name

# Language configuration lookup table
LANGUAGE_CONFIGS: Dict[str, LanguageConfig] = {
    "india": LanguageConfig(
        country_name="India",
        country_code="IN",
        speech_locale="hi-IN",
        translate_from="hi",
        language_name="Hindi"
    ),
    "usa": LanguageConfig(
        country_name="United States",
        country_code="US",
        speech_locale="en-US",
        translate_from="en",
        language_name="English"
    ),
    "spain": LanguageConfig(
        country_name="Spain",
        country_code="ES",
        speech_locale="es-ES",
        translate_from="es",
        language_name="Spanish"
    ),
    "france": LanguageConfig(
        country_name="France",
        country_code="FR",
        speech_locale="fr-FR",
        translate_from="fr",
        language_name="French"
    ),
    "germany": LanguageConfig(
        country_name="Germany",
        country_code="DE",
        speech_locale="de-DE",
        translate_from="de",
        language_name="German"
    ),
    "italy": LanguageConfig(
        country_name="Italy",
        country_code="IT",
        speech_locale="it-IT",
        translate_from="it",
        language_name="Italian"
    ),
    "japan": LanguageConfig(
        country_name="Japan",
        country_code="JP",
        speech_locale="ja-JP",
        translate_from="ja",
        language_name="Japanese"
    ),
    "china": LanguageConfig(
        country_name="China",
        country_code="CN",
        speech_locale="zh-CN",
        translate_from="zh",
        language_name="Chinese (Simplified)"
    ),
    "brazil": LanguageConfig(
        country_name="Brazil",
        country_code="BR",
        speech_locale="pt-BR",
        translate_from="pt",
        language_name="Portuguese (Brazil)"
    ),
    "russia": LanguageConfig(
        country_name="Russia",
        country_code="RU",
        speech_locale="ru-RU",
        translate_from="ru",
        language_name="Russian"
    )
}

def get_language_config(country: str) -> LanguageConfig:
    """
    Get language configuration for a given country.
    
    Args:
        country: Country name (case-insensitive) or country code
        
    Returns:
        LanguageConfig object for the country
        
    Raises:
        ValueError: If country is not supported
    """
    country_lower = country.lower()
    
    # Try exact match first
    if country_lower in LANGUAGE_CONFIGS:
        return LANGUAGE_CONFIGS[country_lower]
    
    # Try matching by country code
    for config in LANGUAGE_CONFIGS.values():
        if config.country_code.lower() == country_lower:
            return config
    
    # Try partial match on country name
    for config in LANGUAGE_CONFIGS.values():
        if country_lower in config.country_name.lower():
            return config
    
    supported_countries = [config.country_name for config in LANGUAGE_CONFIGS.values()]
    raise ValueError(f"Unsupported country: {country}. Supported countries: {', '.join(supported_countries)}")

def get_supported_countries() -> list[str]:
    """Get list of all supported country names"""
    return [config.country_name for config in LANGUAGE_CONFIGS.values()]

def get_supported_country_codes() -> list[str]:
    """Get list of all supported country codes"""
    return [config.country_code for config in LANGUAGE_CONFIGS.values()]

# Example usage and testing
if __name__ == "__main__":
    # Test the lookup functionality
    test_countries = ["India", "USA", "Spain", "IN", "US", "ES"]
    
    for country in test_countries:
        try:
            config = get_language_config(country)
            print(f"{country}: {config.country_name} - {config.language_name} ({config.speech_locale})")
        except ValueError as e:
            print(f"Error for {country}: {e}")
    
    print(f"\nSupported countries: {get_supported_countries()}") 
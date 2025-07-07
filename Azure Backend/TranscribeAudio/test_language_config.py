#!/usr/bin/env python3
"""
Test script for language configuration functionality.
Run this to see how the country-to-language mapping works.
"""

from language_config import get_language_config, get_supported_countries, get_supported_country_codes

def test_language_config():
    """Test the language configuration lookup functionality"""
    
    print("=== Language Configuration Test ===\n")
    
    # Test 1: Get all supported countries
    print("1. Supported Countries:")
    countries = get_supported_countries()
    for i, country in enumerate(countries, 1):
        print(f"   {i}. {country}")
    
    print(f"\n2. Supported Country Codes:")
    codes = get_supported_country_codes()
    for i, code in enumerate(codes, 1):
        print(f"   {i}. {code}")
    
    print("\n3. Language Configuration Examples:")
    
    # Test different ways to look up countries
    test_inputs = [
        "India", "india", "IN", "in",
        "USA", "usa", "US", "us", "United States",
        "Spain", "spain", "ES", "es",
        "France", "france", "FR", "fr",
        "Germany", "germany", "DE", "de"
    ]
    
    for test_input in test_inputs:
        try:
            config = get_language_config(test_input)
            print(f"   '{test_input}' → {config.country_name} ({config.language_name})")
            print(f"      Speech Locale: {config.speech_locale}")
            print(f"      Translation: {config.translate_from} → {config.translate_to}")
        except ValueError as e:
            print(f"   '{test_input}' → Error: {e}")
    
    print("\n4. Example API Request:")
    print("""
    POST /api/TranscribeAudio
    {
        "file_url": "https://example.com/audio.mp4",
        "country": "spain"
    }
    
    This would:
    - Use Spanish speech recognition (es-ES)
    - Translate from Spanish (es) to English (en)
    
    Required fields:
    - file_url: URL of the audio file to transcribe
    - country: Source country for language detection
    
    Error responses include supported countries list:
    {
        "error": "Unsupported country: invalid_country. Supported countries: India, United States, Spain, France, Germany, Italy, Japan, China, Brazil, Russia",
        "supported_countries": ["India", "United States", "Spain", "France", "Germany", "Italy", "Japan", "China", "Brazil", "Russia"]
    }
    """)
    
    print("\n5. Error Handling Example:")
    try:
        config = get_language_config("nonexistent")
    except ValueError as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_language_config() 
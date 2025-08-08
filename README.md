# ONOW Audio Transcription Service

A serverless Azure Functions application that provides real-time audio transcription, translation, polishing, and summarization capabilities. This service processes audio files from various languages and converts them to polished English transcripts with summaries.

## 🚀 Features

- **Multi-language Audio Transcription**: Supports audio files in multiple languages (Hindi, English, Spanish, French, German, Italian, Japanese, Chinese, Portuguese, Russian)
- **Intelligent Translation**: Automatically translates non-English audio to English
- **Text Polishing**: Uses Azure OpenAI to clean and improve transcript quality
- **Smart Summarization**: Generates concise summaries highlighting key points and action items
- **Blob Storage Integration**: Securely stores all transcript versions with SAS token access
- **Bubble CRM Integration**: Sends processed data directly to Bubble webhook
- **Error Handling & Retry Logic**: Robust error handling with exponential backoff

## 📋 Prerequisites

- **Azure Account** with access to:
  - Azure Functions
  - Azure Storage Account
  - Azure Cognitive Services (Speech Services)
  - Azure Translator
  - Azure OpenAI Service
- **Python 3.8+**
- **Azure Functions Core Tools**
- **FFmpeg** (for local development)

## 🛠️ Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd ONOW-Translator/Azure Backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create or update `local.settings.json` with your Azure service credentials:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "<your-storage-connection-string>",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_STORAGE_CONNECTION_STRING": "<your-storage-connection-string>",
    "AZURE_STORAGE_CONTAINER": "audio",
    "AZURE_TRANSLATOR_KEY": "<your-translator-key>",
    "AZURE_TRANSLATOR_REGION": "eastus",
    "AZURE_SPEECH_REGION": "eastus",
    "AZURE_SPEECH_KEY": "<your-speech-key>",
    "BUBBLE_WEBHOOK_URL": "<your-bubble-webhook-url>",
    "AZURE_OPENAI_KEY": "<your-openai-key>",
    "AZURE_OPENAI_ENDPOINT": "<your-openai-endpoint>",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-35-turbo",
    "OPENAI_API_VERSION": "2024-01-01"
  }
}
```

### 4. Local Development
```bash
func start
```

## 📡 API Documentation

### Endpoint
```
POST /api/TranscribeAudio
```

### Request Body
```json
{
  "file_url": "https://example.com/audio.mp4",
  "country": "India"
}
```

### Parameters
- `file_url` (required): Direct URL to the audio file (MP4 format)
- `country` (optional): Source country for language detection. Defaults to "India"

### Supported Countries
- **India** (Hindi)
- **United States** (English)
- **Spain** (Spanish)
- **France** (French)
- **Germany** (German)
- **Italy** (Italian)
- **Japan** (Japanese)
- **China** (Chinese)
- **Brazil** (Portuguese)
- **Russia** (Russian)

### Response Format

#### Success Response (200)
```json
{
  "file_id": "uuid-string",
  "message": "Audio processing completed successfully.",
  "polished_text": "The polished English transcript...",
  "summary_text": "Summary of the transcript..."
}
```

#### Error Response (400/500)
```json
{
  "error": "Error description",
  "supported_countries": ["India", "United States", ...]
}
```

## 🔄 Processing Pipeline

1. **Audio Download**: Downloads the MP4 file from the provided URL
2. **Format Conversion**: Converts MP4 to WAV using FFmpeg
3. **Blob Upload**: Uploads WAV file to Azure Blob Storage
4. **Speech-to-Text**: Uses Azure Speech Services for transcription
5. **Text Cleaning**: Removes filler words and improves grammar
6. **Translation**: Translates non-English text to English
7. **Polishing**: Uses Azure OpenAI to enhance text quality
8. **Summarization**: Generates concise summary with key points
9. **Storage**: Saves all transcript versions to blob storage
10. **Webhook**: Sends processed data to Bubble CRM

## 📁 File Structure

```
Azure Backend/
├── TranscribeAudio/
│   ├── __init__.py          # Main function logic
│   ├── function.json        # Function configuration
│   ├── language_config.py   # Language support configuration
│   └── ffmpeg/             # FFmpeg binaries (for Azure deployment)
├── local.settings.json      # Local environment variables
├── requirements.txt         # Python dependencies
├── test.py                 # Local testing script
├── host.json               # Azure Functions host configuration
└── README.md               # This file
```

## 🧪 Testing

### Local Testing
Use the provided `test.py` script:

```python
import requests

url = "http://localhost:7071/api/TranscribeAudio"
payload = {
    "file_url": "https://example.com/audio.mp4",
    "country": "India"
}

response = requests.post(url, json=payload)
print("Status code:", response.status_code)
print("Response:", response.text)
```

### Testing with ManyChat
Configure ManyChat webhook to point to your deployed function URL:
```
https://your-function-app.azurewebsites.net/api/TranscribeAudio
```

## 🚀 Deployment

### 1. Deploy to Azure
```bash
func azure functionapp publish <your-function-app-name>
```

### 2. Configure Application Settings
In Azure Portal, add the same environment variables from `local.settings.json` to your Function App's Application Settings.

### 3. Update ManyChat Webhook
Update your ManyChat webhook URL to point to the deployed function.

## 🔧 Configuration

### Language Configuration
Supported languages are defined in `TranscribeAudio/language_config.py`. Each language includes:
- Speech recognition locale
- Translation source/target languages
- Language display name

### Storage Configuration
- **Container**: `audio` (for audio files)
- **Blob Path**: `transcripts/{file_id}_{type}.txt`
- **SAS Token**: 24-hour expiry for transcript access

### Bubble Integration
The service sends the following data to your Bubble webhook:
- `file_id`: Unique identifier
- `transcript_url`: SAS-protected blob URL
- `polished_text`: Cleaned English transcript
- `summary_text`: Generated summary
- `timestamp`: Processing timestamp

## 🐛 Troubleshooting

### Common Issues

1. **FFmpeg Not Found** (Local Development)
   - Install FFmpeg on your system
   - Ensure it's in your PATH

2. **Azure OpenAI Errors**
   - Verify API key and endpoint
   - Check deployment name matches your Azure OpenAI resource

3. **Translation Failures**
   - Verify Azure Translator key and region
   - Check supported language pairs

4. **Blob Storage Errors**
   - Verify connection string
   - Ensure container exists and is accessible

### Logging
The function uses Azure Functions logging. Check logs in:
- **Local**: Terminal output
- **Azure**: Function App logs in Azure Portal

## 📊 Monitoring

Monitor your function's performance through:
- Azure Portal Function App metrics
- Application Insights (if configured)
- Custom logging statements in the code

## 🔒 Security

- All Azure service keys are stored as environment variables
- Blob storage uses SAS tokens with limited permissions
- Function uses function-level authentication
- No sensitive data is logged

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Add your license information here]

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review Azure Functions documentation
- Contact the development team

---

**Note**: This service is designed for production use with ManyChat integration and Bubble CRM. Ensure all Azure services are properly configured and monitored for optimal performance. 
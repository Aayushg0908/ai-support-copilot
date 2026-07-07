from google import genai

# Replace this with your actual Gemini API key
API_KEY = "AQ.Ab8RN6LCtB-Y9ZWN7gZOtxuQbsMFn2T-QRUC556NPaHK7fUvHg"

try:
    # Initialize the client
    client = genai.Client(api_key=API_KEY)

    # Send a simple prompt
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Hello! Please introduce yourself in 3 sentences."
    )

    print("=" * 50)
    print("✅ API Key is working!")
    print("=" * 50)
    print(response.text)

except Exception as e:
    print("=" * 50)
    print("❌ Error occurred")
    print("=" * 50)
    print(type(e).__name__)
    print(e)
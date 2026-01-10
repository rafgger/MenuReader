import os
import base64
import requests
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dotenv import load_dotenv
# rendering on https://photo.maira.rascasone.dev/

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

# OpenRouter configuration
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "openai/gpt-5.1"  # Pred tim, levnější OpenAI GPT-4 Mini model via OpenRouter
prompt = """
Analyzuj POUZE aktuálně viditelná rizika na pracovišti podle principů BOZP (Bezpečnost a ochrana zdraví při práci).
DŮLEŽITÉ: Zaměř se PRIORITNĚ na objekty a situace v POPŘEDÍ obrázku - ty jsou nejdůležitější a nejlépe viditelné. NEVYMÝŠLEJ rizika, která se mohou projevit v budoucnu nebo která tam nejsou vidět.

PRIORITA ANALÝZY:
1. POPŘEDÍ - objekty, stroje, osoby, nástroje v popředí obrázku (nejvyšší priorita)
2. STŘEDNÍ PLÁN - pouze pokud jsou jasně viditelné významné problémy
3. POZADÍ - ignoruj, pokud není něco zjevně nebezpečného

Identifikuj pouze konkrétní problémy, které jsou v POPŘEDÍ přímo viditelné:
- Úniky kapalin v popředí, které jsou jasně vidět
- Poškozené části strojů v popředí, které jsou vidět
- Chybějící bezpečnostní prvky u objektů v popředí
- Překážky v popředí, které jsou vidět
- Nesprávné zacházení s nástroji nebo materiály v popředí

NEZAHRNUJ:
- Objekty v pozadí, které nejsou jasně viditelné
- Rizika, která se "mohou" stát v budoucnu
- Rizika, která "by mohla" nastat
- Preventivní opatření pro situace, které nejsou aktuálně problémem
- Obecná doporučení pro údržbu

Rizika seřaď od nejdůležitějšího po nejméně důležité.
Dávej pouze specifická doporučení vztahující se ke konkrétnímu obrázku. Detailně popiš co vidíš v POPŘEDÍ obrázku a jaká konkrétní rizika z toho vyplývají.
Zmiň pouze nejduležitější rizika (maximálně 2).

Pro každé AKTUÁLNĚ VIDITELNÉ riziko uveď:
- Konkrétní popis toho, co je na obrázku špatně TEĎKA
- Jaký druh nebezpečí to představuje
- Koho nebo co může ohrozit
- Jak závažné je toto riziko
- Konkrétní opatření pro odstranění tohoto aktuálního problému
- Relevantní právní odkazy pro toto riziko

Výsledek strukturovaně uveď v JSON formátu:
{
  "rizika": [
    {
      "popis_rizika": {
        "co_je_spatne": "konkrétní popis toho, co je na obrázku aktuálně špatně",
        "druh_nebezpeci": "typ nebezpečí",
        "ohrozeni": "koho nebo co může ohrozit",
        "zavaznost": "míra závažnosti rizika"
      },
      "opatreni": [
        "konkrétní opatření 1 pro odstranění tohoto aktuálního problému",
        "konkrétní opatření 2 pro odstranění tohoto aktuálního problému"
      ],
      "odkazy": [
        "relevantní zákon/vyhláška/norma 1 pro toto riziko",
        "relevantní zákon/vyhláška/norma 2 pro toto riziko"
      ]
    }
  ],
  "poznámky": "další relevantní informace o aktuální situaci na obrázku"
}
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return send_from_directory('.', 'auto_test.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        image = request.files['image']
        if image.filename == '':
            return jsonify({'error': 'No image selected'}), 400
            
        # Convert image to base64
        img_bytes = image.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Prepare OpenRouter API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image.mimetype};base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 2048
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({'result': result['choices'][0]['message']['content']})
        else:
            return jsonify({'error': f'OpenRouter API error: {response.status_code} - {response.text}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/example/<filename>')
def example_image(filename):
    return send_from_directory('example_images', filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

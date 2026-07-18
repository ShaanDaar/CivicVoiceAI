import os
from gtts import gTTS

def generate_audio_samples():
    """
    Generates synthetic, clean audio clips in Hindi, Marathi, and Kannada
    specifically for pipeline intake testing.
    """
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_audio")
    os.makedirs(output_dir, exist_ok=True)
    
    samples = [
        {
            "filename": "hi_complaint.mp3",
            "text": "हमारे मोहल्ले में कचरा तीन दिनों से जमा है, जिससे बहुत बदबू आ रही है और बीमारियां फैलने का खतरा है।",
            "lang": "hi",
            "description": "Hindi Sanitation: Expected Waste Management, Urgency 4/5"
        },
        {
            "filename": "mr_complaint.mp3",
            "text": "रस्त्यावरील विजेचा खांब वाकला आहे आणि जिवंत तारा लटकत आहेत, मोठी दुर्घटना होऊ शकते.",
            "lang": "mr",
            "description": "Marathi Electricity Safety: Expected Electricity & Power, Urgency 5/5"
        },
        {
            "filename": "kn_complaint.mp3",
            "text": "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್ ಒಡೆದು ಹೋಗಿ ನೀರು ವ್ಯರ್ಥವಾಗುತ್ತಿದೆ, ದಯವಿಟ್ಟು ಸರಿಪಡಿಸಿ.",
            "lang": "kn",
            "description": "Kannada Water Waste: Expected Water & Sanitation, Urgency 4/5"
        }
    ]
    
    print("=====================================================================")
    print("        CIVICVOICE AI - SYNTHETIC CLEAN AUDIO SAMPLE GENERATION      ")
    print("=====================================================================")
    
    for sample in samples:
        dest_path = os.path.join(output_dir, sample["filename"])
        print(f"Generating {sample['filename']} ({sample['lang']}) ...")
        print(f"  Script: '{sample['text']}'")
        
        try:
            tts = gTTS(text=sample["text"], lang=sample["lang"])
            tts.save(dest_path)
            print(f"  Saved to: {dest_path}")
        except Exception as e:
            print(f"  Error generating {sample['filename']}: {e}")
            
    print("\nGeneration process complete.")

if __name__ == "__main__":
    generate_audio_samples()

"""
Audio Transcription Test
Upload a real audio file and get it transcribed + analyzed
Requires: ASSEMBLYAI_API_KEY or OPENAI_API_KEY in .env file
"""

import httpx
import asyncio
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"


async def test_audio_file(audio_path: str):
    """
    Test audio transcription with a real audio file.
    Requires API key configured.
    """
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        print(f"   Please provide full path to audio file")
        print(f"   Example: python test_audio.py C:\\Users\\shans\\Downloads\\call.mp3")
        return
    
    print(f"\n{'='*60}")
    print(f"🎤 AUDIO TRANSCRIPTION TEST")
    print(f"{'='*60}")
    print(f"📁 File: {audio_path}")
    print(f"{'='*60}\n")
    
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            # Open and upload the audio file
            with open(audio_path, 'rb') as f:
                files = {'file': (os.path.basename(audio_path), f, 'audio/mpeg')}
                
                print("🔄 Uploading and transcribing audio...")
                resp = await client.post(
                    f"{BASE_URL}/analyze/audio",
                    files=files,
                    params={
                        'client_id': 'audio_test_001',
                        'domain': 'auto',
                        'include_resolution_prediction': True
                    }
                )
            
            if resp.status_code == 200:
                data = resp.json()
                a = data["analysis"]
                
                print("\n✅ TRANSCRIPTION SUCCESSFUL\n")
                
                # Show transcription details
                proc = data.get("processing_info", {})
                if proc:
                    print(f"📊 Transcription Info:")
                    print(f"   • Input: {proc.get('input_type')}")
                    print(f"   • Confidence: {proc.get('transcription_confidence', 0)*100:.1f}%")
                    print(f"   • Speakers: {proc.get('speakers_detected')}")
                    print(f"   • Duration: {proc.get('conversation_duration')}")
                    print(f"\n📝 TRANSCRIPT:")
                    print("-" * 60)
                    transcript = proc.get('raw_transcript', '')
                    print(transcript[:500] + ("..." if len(transcript) > 500 else ""))
                    print("-" * 60)
                
                # Analysis results
                print(f"\n🌐 Language: {a['language_analysis']['language_name']}")
                print(f"😤 Customer sentiment: {a['sentiment_analysis']['overall_customer_sentiment']:.2f}")
                print(f"🎭 Agent tone arc: {a['sentiment_analysis']['agent_tone_arc']}")
                print(f"🚨 Violations: {a['compliance']['critical_count']} critical, {a['compliance']['high_count']} high")
                print(f"⚠️  Risk: {a['risk_assessment']['risk_level'].upper()} ({a['risk_assessment']['overall_risk_score']:.2f})")
                print(f"👤 Agent grade: {a['agent_performance']['grade']} ({a['agent_performance']['overall_score']:.2f})")
                
                # Save result
                output_file = "test_results/audio_test_result.json"
                os.makedirs("test_results", exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Saved to: {output_file}")
                
            else:
                print(f"❌ Error {resp.status_code}:")
                print(resp.text[:500])
                
    except Exception as e:
        print(f"❌ Failed: {str(e)}")


async def main():
    """
    Show instructions for using real audio transcription.
    """
    print("\n🎯 AUDIO TRANSCRIPTION TEST")
    print("="*60)
    print("This tool transcribes REAL audio files.")
    print("="*60)
    
    print("\n⚙️  REQUIREMENTS:")
    print("   1. API key in .env file (AssemblyAI or OpenAI)")
    print("   2. Real audio file (mp3, wav, m4a, etc.)")
    
    print("\n📝 USAGE:")
    print("   python test_audio.py <path_to_audio_file>")
    print("\n   Examples:")
    print("   python test_audio.py call.mp3")
    print("   python test_audio.py C:\\Users\\shans\\Downloads\\recording.wav")
    
    print("\n🔑 SETUP API KEY:")
    print("   1. Get key from: https://www.assemblyai.com/")
    print("   2. Add to .env: ASSEMBLYAI_API_KEY=your_key_here")
    print("   3. Restart server: python main.py")
    
    print("\n📋 SUPPORTED FORMATS:")
    print("   mp3, wav, m4a, webm, flac, ogg")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    import sys
    
    # Check if audio file path provided
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        asyncio.run(test_audio_file(audio_path))
    else:
        # Run mock test by default
        asyncio.run(main())

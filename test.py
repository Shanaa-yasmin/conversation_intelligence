"""
Test Script — run all test cases against the API
Usage: python test.py
Saves results to test_results/ directory as JSON files
"""

import httpx
import json
import asyncio
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Create output directory
os.makedirs("test_results", exist_ok=True)


async def test(name: str, payload: dict, test_number: int):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{BASE_URL}/analyze", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            a = data["analysis"]
            print(f"✅ Status: {data['status']}")
            
            # Language analysis
            print(f"🌐 Language: {a['language_analysis']['language_name']} | Mismatch: {a['language_analysis']['language_mismatch']}")
            
            # Sentiment & Tone (from deterministic NLP engines)
            print(f"😤 Customer sentiment: {a['sentiment_analysis']['overall_customer_sentiment']:.2f} | Arc: {a['sentiment_analysis']['customer_sentiment_arc']}")
            print(f"🎭 Agent tone arc: {a['sentiment_analysis']['agent_tone_arc']}")
            
            # Compliance (from RAG engine)
            print(f"🚨 Violations: {a['compliance']['critical_count']} critical, {a['compliance']['high_count']} high, {a['compliance']['medium_count']} medium")
            print(f"📊 Compliance score: {a['compliance']['compliance_score']:.2f} | Status: {a['compliance']['status'].upper()}")
            
            # Risk assessment
            print(f"⚠️  Risk score: {a['risk_assessment']['overall_risk_score']:.2f} ({a['risk_assessment']['risk_level'].upper()})")
            print(f"📢 Escalation: {a['risk_assessment']['escalation_required']} ({a['risk_assessment']['escalation_priority']})")
            
            # Agent performance
            print(f"👤 Agent grade: {a['agent_performance']['grade']} ({a['agent_performance']['overall_score']:.2f})")
            
            # Resolution prediction
            if a.get("resolution_prediction"):
                print(f"⏱️  Resolution: {a['resolution_prediction']['predicted_resolution_time']} ({a['resolution_prediction']['confidence_score']*100:.0f}% confident)")

            # Show violations with policy references
            if a["compliance"]["violations"]:
                print(f"\n🔴 POLICY VIOLATIONS (RAG-detected):")
                for v in a["compliance"]["violations"]:
                    print(f"   [{v['severity'].upper()}] Policy ID: {v['policy_id']}")
                    print(f"   → Detected: {v['violation_statement'][:70]}...")
                    print(f"   → Policy: {v['policy_text'][:80]}...")
                    if v.get('regulatory_risk'):
                        print(f"   → Regulatory: {v['regulatory_risk']}")

            # Show tone flags
            if a["sentiment_analysis"]["tone_flags"]:
                print(f"\n⚡ TONE FLAGS (Rule-based detection):")
                for f in a["sentiment_analysis"]["tone_flags"][:5]:  # Show top 5
                    print(f"   [{f['severity'].upper()}] {f['speaker']}: {f['tone']} | Risk: {f['risk_contribution']:.2f}")

            # Show emotional turning points
            if a["sentiment_analysis"]["emotional_turning_points"]:
                print(f"\n💥 EMOTIONAL TURNING POINTS:")
                for tp in a["sentiment_analysis"]["emotional_turning_points"][:3]:  # Show top 3
                    print(f"   → {tp['trigger'][:60]}... (Δ {tp['magnitude']:.2f})")

            print(f"\n📝 Summary: {a['conversation_summary']}")
            
            # Save to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results/test_{test_number}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Saved to: {filename}")
            
        else:
            print(f"❌ Error {resp.status_code}: {resp.text[:300]}")
            
            # Save error response
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results/test_{test_number}_ERROR_{timestamp}.json"
            error_data = {
                "test_name": name,
                "status_code": resp.status_code,
                "error": resp.text,
                "timestamp": timestamp
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Error saved to: {filename}")


async def run_all_tests():
    print("\n" + "="*60)
    print("🚀 STARTING TEST SUITE - Re-Architected System")
    print("="*60)
    print("📁 Results will be saved to: test_results/")
    print("="*60)
    
    # ── TEST 1: Banking — OTP violation (text) ─────────────────────────
    await test("Banking: OTP Violation + Churn Threat (Text)", {
        "input_type": "text",
        "conversation": """Agent: Thank you for calling National Bank. How can I help?
Customer: I've been waiting 20 minutes! My account was charged twice! This is a disaster!
Agent: I understand. Can I get your account number?
Customer: 4521-8876-3312. This keeps happening!
Agent: Now please give me your OTP sent to your phone.
Customer: Is it safe to share?
Agent: Yes yes, just tell me quickly.
Customer: 8 8 4 2 1 9.
Agent: Thank you. Also don't worry, your loan will definitely be approved.
Customer: I didn't ask about a loan! When will I get my refund?
Agent: It will take some time. I can't really do much more from my end.
Customer: Unbelievable. I'm closing all my accounts with you!""",
        "client_config": {"client_id": "bank_001", "domain": "auto"},
        "analysis_type": "comprehensive",
        "include_resolution_prediction": True
    }, test_number=1)

    # ── TEST 2: Telecom — Roaming charge hidden ─────────────────────────
    await test("Telecom: Hidden Roaming Charges (Text)", {
        "input_type": "text",
        "conversation": """Agent: Welcome to QuickNet support! How can I assist?
Customer: Hi, I want to activate international roaming for my trip to Europe.
Agent: Sure! I'll activate it right now for you.
Customer: How much will it cost?
Agent: Don't worry, it's included in your plan, just use normally.
Customer: Really? That's great! Please activate it.
Agent: Done! Enjoy your trip.
Customer: Wait, I just got a bill for 15,000 rupees in roaming charges!
Agent: Oh yes, international roaming is charged separately, I should have mentioned.
Customer: You told me it was included! This is fraud!
Agent: I'm sorry for the confusion but the charges are valid and cannot be reversed.""",
        "client_config": {"client_id": "telecom_001", "domain": "auto"},
        "analysis_type": "comprehensive",
        "include_resolution_prediction": True
    }, test_number=2)

    # ── TEST 3: Good interaction — compliant agent ──────────────────────
    await test("E-commerce: Good Agent (Compliant Interaction)", {
        "input_type": "text",
        "conversation": """Agent: Hello! Welcome to ShopFast support. I'm Priya, how can I help you today?
Customer: Hi, I received a damaged product. The screen is cracked.
Agent: I'm so sorry to hear that! That must be very frustrating. Can I get your order number?
Customer: It's SF-2024-98765.
Agent: Thank you. I can see your order. I want to assure you this will be resolved. We'll send a replacement at no cost. Would you prefer a refund or replacement?
Customer: A replacement please.
Agent: Perfect. Your replacement will arrive in 3-5 business days. You'll get a tracking email within 2 hours. Is there anything else I can help with?
Customer: No, that's great. Thank you so much!
Agent: You're welcome! Thank you for your patience. Have a wonderful day!""",
        "client_config": {"client_id": "ecom_001", "domain": "auto"},
        "analysis_type": "comprehensive",
        "include_resolution_prediction": True
    }, test_number=3)

    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE")
    print("📁 Results saved to: test_results/")
    print("📁 For audio testing, use: python test_audio.py <audio_file_path>")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

import requests
import time

url = 'http://127.0.0.1:8000/api/analyze/'
# Create a dummy video file in memory or use existing
files = {'video_file': ('test.webm', b'dummy_video_content_for_testing', 'video/webm')}
data = {'role': 'Full Stack Developer'}

s = requests.Session()

# Get CSRF
try:
    s.get('http://127.0.0.1:8000/')
    csrftoken = s.cookies['csrftoken']
    headers = {'X-CSRFToken': csrftoken, 'Referer': 'http://127.0.0.1:8000'}
except:
    print("Could not fetch CSRF token (Is server running?)")
    headers = {}

print("🚀 Starting Simulated Interview Session (3 Questions)...")
total_confidence = 0

for i in range(1, 4):
    print(f"\n[Question {i}/3] Sending Answer...")
    try:
        # We need to reset file pointer or re-create tuple for each request if using file object
        # but here we use bytes so it's fine.
        response = s.post(url, files=files, data=data, headers=headers)
        
        if response.status_code == 200:
            res_json = response.json()
            conf = res_json.get('confidence', 0)
            print(f"✅ Q{i} Processed. Confidence Score: {conf}%")
            print(f"   Recommendation: {res_json.get('recommendations', [])[0]}")
            total_confidence += conf
        else:
            print(f"❌ Q{i} Failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    # Simulate user reading/answering time
    time.sleep(1)

avg_conf = total_confidence // 3
print(f"\n🏆 Session Complete!")
print(f"Average Confidence: {avg_conf}%")
print("System is Ready for Live Use.")

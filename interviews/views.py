from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Community, Post
from django.views.decorators.csrf import ensure_csrf_cookie
import random
import time
import os
from django.conf import settings

@ensure_csrf_cookie
def index(request):
    return render(request, 'interviews/index.html')

from django.views.decorators.csrf import csrf_exempt

def test_connection(request):
    return JsonResponse({'status': 'ok', 'message': 'Connection Successful!'})

@csrf_exempt
def analyze_interview(request):
    try:
        if request.method == 'POST' and request.FILES.get('video_file'):
            video = request.FILES['video_file']
            role = request.POST.get('role', 'General')
            
            # Paths
            save_path = os.path.join(settings.MEDIA_ROOT, 'uploads', video.name)
            wav_path = os.path.join(settings.MEDIA_ROOT, 'uploads', 'temp_audio.wav')
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Save Upload
            with open(save_path, 'wb+') as destination:
                for chunk in video.chunks():
                    destination.write(chunk)
                    
            # Real AI: Transcription
            try:
                import speech_recognition as sr
                from pydub import AudioSegment
                
                # Convert WebM to WAV (Requires ffmpeg)
                if os.path.exists(wav_path): os.remove(wav_path)
                
                audio = AudioSegment.from_file(save_path)
                audio.export(wav_path, format="wav")
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    transcript = recognizer.recognize_google(audio_data)
                
            except Exception as e:
                print(f"ML Error (Fallback to Mock): {e}")
                transcript = "Could not transcribe audio. (Ensure ffmpeg is installed)"
                confidence_score = random.randint(70, 98)

            # --- SMART ANALYSIS ENGINE ---
            recommendations = []
            
            # 1. Voice Capability (Word Count & Confidence)
            word_count = len(transcript.split()) if transcript else 0
            if word_count < 5:
                # Still give a fair score for testing, but warn
                confidence_score = 75 
                recommendations.append("⚠️ Answer very short. Try to elaborate more.")
            else:
                 # Check Keywords based on Role
                keywords = {
                    'Full Stack Developer': ['component', 'react', 'node', 'express', 'database', 'sql', 'nosql', 'api', 'http', 'css', 'dom', 'redux', 'hook', 'async', 'await'],
                    'Data Scientist': ['regression', 'classification', 'clustering', 'neural', 'pandas', 'numpy', 'accuracy', 'precision', 'recall', 'overfitting', 'bias', 'variance'],
                    'AI Engineer': ['transformer', 'attention', 'gradient', 'loss', 'optimization', 'backpropagation', 'cnn', 'rnn', 'lstm', 'bert', 'gpt', 'token', 'embedding', 'inference'],
                    'Backend Developer': ['cache', 'redis', 'db', 'migration', 'index', 'queue', 'kafka', 'rabbitmq', 'docker', 'kubernetes', 'microservice', 'security', 'auth'],
                    'Frontend Developer': ['flex', 'grid', 'responsive', 'accessibility', 'aria', 'hook', 'lifecycle', 'performance', 'bundle', 'webpack', 'vite']
                }
                
                role_kw = keywords.get(role, [])
                # Simple keyword matching
                matched = [w for w in transcript.lower().split() if w in role_kw]
                
                if matched:
                    confidence_score = min(98, 60 + (len(matched) * 10))
                    recommendations.append(f"✅ Good use of technical terms: {', '.join(list(set(matched))[:3])}")
                else:
                    confidence_score = 65
                    recommendations.append(f"💡 Tip: Try to include more {role}-specific terminology (e.g., {', '.join(role_kw[:3])}).")

                # Pace Analysis
                pace_val = max(100, min(160, int(word_count * 60 / 5))) # Approx 5 sec clip
                if pace_val > 150:
                    recommendations.append("⚡ You are speaking a bit fast. Take pauses.")
                elif pace_val < 110:
                    recommendations.append("🐢 A bit slow. Try to maintain a steady flow.")
                else:
                    recommendations.append("✅ Great speaking pace!")

            recommendations.append(f"🗣️ Transcribed: \"{transcript[:60]}...\"")

            analysis_data = {
                'confidence': confidence_score,
                'clarity': 'High' if confidence_score > 80 else 'Medium',
                'pace': f"{pace_val if 'pace_val' in locals() else 0} wpm",
                'tone': 'Professional',
                'recommendations': recommendations
            }
            
            return JsonResponse(analysis_data)
        
        return JsonResponse({'error': 'Invalid request: No file'}, status=400)

    except Exception as e:
        import traceback
        print(f"CRITICAL BACKEND ERROR: {e}")
        return JsonResponse({'error': str(e), 'trace': traceback.format_exc()}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def community_detail(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        file = request.FILES.get('file')
        if content or image or file:
            Post.objects.create(
                community=community,
                user=request.user,
                content=content or '',
                image=image,
                file=file
            )
            return redirect('community_detail', slug=slug)
    
    posts = community.posts.all()
    return render(request, 'interviews/community.html', {
        'community': community,
        'posts': posts
    })

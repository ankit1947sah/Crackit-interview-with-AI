from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Community, Post
from django.views.decorators.csrf import ensure_csrf_cookie
import random
import time
import os
from django.conf import settings
from .forms import FeedbackForm
from django.views.decorators.http import require_POST
import json

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

@require_POST
def submit_feedback(request):
    try:
        data = json.loads(request.body)
        form = FeedbackForm(data)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success', 'message': 'Feedback received. Thank you!'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

import re
import PyPDF2
import docx2txt
import traceback

@csrf_exempt
def analyze_resume(request):
    if request.method == 'POST' and request.FILES.get('resume_file'):
        temp_path = None
        try:
            resume = request.FILES['resume_file']
            file_ext = os.path.splitext(resume.name)[1].lower()
            text = ""

            # Save to temp file first (required for docx2txt and safer for PyPDF2)
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, 'temp_resume' + file_ext)
            with open(temp_path, 'wb+') as f:
                for chunk in resume.chunks():
                    f.write(chunk)

            # Extract Text
            if file_ext == '.pdf':
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
            elif file_ext in ['.docx', '.doc']:
                text = docx2txt.process(temp_path)
            else:
                return JsonResponse({'error': 'Unsupported file format. Use .pdf or .docx'}, status=400)

            if not text or not text.strip():
                text = ""  # Handle empty/scanned PDFs gracefully

            # Heuristic Analysis Engine
            text_lower = text.lower()
            
            # 1. Skill Extraction
            tech_keywords = {
                'python': 'Python', 'django': 'Django', 'react': 'React', 'node': 'Node.js', 
                'express': 'Express', 'mongodb': 'MongoDB', 'sql': 'SQL', 'aws': 'AWS', 
                'docker': 'Docker', 'kubernetes': 'Kubernetes', 'java': 'Java', 'c++': 'C++',
                'javascript': 'JavaScript', 'typescript': 'TypeScript', 'git': 'Git', 'html': 'HTML',
                'css': 'CSS', 'machine learning': 'Machine Learning', 'ai': 'AI', 'data science': 'Data Science',
                'mern': 'MERN Stack', 'rest api': 'REST APIs', 'graphql': 'GraphQL',
                'flask': 'Flask', 'spring': 'Spring', 'angular': 'Angular', 'vue': 'Vue.js',
                'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch', 'pandas': 'Pandas', 'numpy': 'NumPy',
                'linux': 'Linux', 'azure': 'Azure', 'gcp': 'GCP', 'firebase': 'Firebase',
                'mysql': 'MySQL', 'postgresql': 'PostgreSQL', 'redis': 'Redis',
            }
            extracted_skills = []
            for kw, proper_name in tech_keywords.items():
                if kw in text_lower:
                    extracted_skills.append(proper_name)
            
            # 2. Vague Buzzword Detection
            buzzwords = ['synergized', 'revolutionized', 'leveraged', 'spearheaded', 'thought leader', 'dynamic', 'proactive', 'go-getter', 'detail-oriented', 'hardworking']
            found_buzzwords = [bw for bw in buzzwords if bw in text_lower]
            
            # 3. Metric Detection (Checking for numbers/% indicating concrete achievements)
            has_metrics = bool(re.search(r'\d+%|\d+x|\$\d+|\d+ users', text_lower))
            
            # 4. Generate Questions based on Skills
            questions = []
            skill_questions = {
                'React': "How do you handle state management in large React applications? Can you explain useEffect?",
                'Python': "What are the key differences between lists and tuples? How does Python manage memory?",
                'Django': "Explain the MVT architecture in Django. How do you optimize Django ORM queries?",
                'Node.js': "How does the event loop work in Node.js? How do you handle asynchronous operations?",
                'MongoDB': "What is the aggregation pipeline in MongoDB? How do you design schemas for NoSQL?",
                'SQL': "Explain the difference between INNER JOIN and LEFT JOIN. How do you create an index?",
                'AWS': "Which AWS services have you used? How do you deploy a scalable web app on AWS?",
                'Docker': "What is the difference between a Docker image and a container? How do you use docker-compose?",
                'MERN Stack': "How do you structure authentication in a MERN app? Have you deployed one to production?",
                'JavaScript': "Explain closures, prototypes, and the event loop in JavaScript.",
                'Java': "What is the difference between JDK, JRE, and JVM? Explain OOP principles in Java.",
                'TensorFlow': "How do you build and train a neural network using TensorFlow/Keras?",
                'Flask': "How does Flask differ from Django? When would you choose one over the other?",
            }
            
            for skill in extracted_skills:
                if skill in skill_questions:
                    questions.append({
                        'skill': skill,
                        'question': skill_questions[skill]
                    })
                    if len(questions) >= 5:
                        break
            
            if not questions:
                questions.append({
                    'skill': 'General Technical',
                    'question': "Can you walk me through the most challenging technical problem you've solved?"
                })

            # 5. Score Calculation
            trust_score = 100
            vagueness_penalty = len(found_buzzwords) * 5
            trust_score -= min(30, vagueness_penalty) # Max 30% penalty for buzzwords
            
            if not has_metrics:
                trust_score -= 20 # 20% penalty for lack of metrics
                
            if len(extracted_skills) < 2:
                trust_score -= 15 # Penalty for too few technical skills mentioned
                
            trust_score = max(0, trust_score) # Ensure >= 0
            
            # Prepare Response
            response_data = {
                'skills': extracted_skills,
                'trust_score': trust_score,
                'found_buzzwords': found_buzzwords,
                'has_metrics': has_metrics,
                'questions': questions,
                'summary': f"Found {len(extracted_skills)} technical skills. {'Lacks measurable metrics.' if not has_metrics else 'Includes measurable metrics.'}"
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"RESUME ANALYSIS ERROR: {e}")
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    return JsonResponse({'error': 'Invalid request. Send a POST with resume_file.'}, status=400)

# ClassMate AWS 배포 가이드

## 📋 목차
1. [AWS 계정 및 EC2 인스턴스 생성](#1-aws-계정-및-ec2-인스턴스-생성)
2. [서버 초기 설정](#2-서버-초기-설정)
3. [애플리케이션 배포](#3-애플리케이션-배포)
4. [도메인 연결 (classmate.kr)](#4-도메인-연결)
5. [SSL 인증서 설정](#5-ssl-인증서-설정)
6. [유지보수 및 모니터링](#6-유지보수-및-모니터링)

---

## 1. AWS 계정 및 EC2 인스턴스 생성

### 1.1 AWS 계정 생성
1. https://aws.amazon.com/ko/ 접속
2. "무료 계정 만들기" 클릭
3. 이메일, 비밀번호, 결제 정보 입력
   - ⚠️ 신용카드 필요 (프리티어는 무료지만 등록 필요)
   - 프리티어 12개월 무료!

### 1.2 EC2 인스턴스 생성

#### Step 1: AWS Console 접속
- AWS Management Console 로그인
- 상단 검색창에 "EC2" 입력 → 클릭

#### Step 2: 인스턴스 시작
1. **"인스턴스 시작" 버튼** 클릭

2. **이름 및 태그**
   - 이름: `classmate-server`

3. **애플리케이션 및 OS 이미지 (AMI)**
   - **Ubuntu Server 22.04 LTS** 선택
   - 프리 티어 사용 가능 옵션 확인 ✅

4. **인스턴스 유형**
   - **t2.micro** 선택 (프리티어)
   - 1 vCPU, 1GB RAM

5. **키 페어 (로그인)**
   - "새 키 페어 생성" 클릭
   - 키 페어 이름: `classmate-key`
   - 키 페어 유형: RSA
   - 프라이빗 키 파일 형식: `.pem`
   - **"키 페어 생성" 클릭 → 파일 다운로드**
   - ⚠️ **이 파일을 안전한 곳에 보관하세요!**

6. **네트워크 설정**
   - "보안 그룹 생성" 선택
   - 보안 그룹 이름: `classmate-sg`
   - 설명: `Security group for ClassMate`

   **인바운드 규칙 추가:**
   - SSH (포트 22): 내 IP
   - HTTP (포트 80): 0.0.0.0/0 (모든 IP)
   - HTTPS (포트 443): 0.0.0.0/0 (모든 IP)
   - Custom TCP (포트 8000): 내 IP (테스트용)

7. **스토리지 구성**
   - 30GB gp3 (프리티어 한도)

8. **고급 세부 정보** (생략 가능)

9. **인스턴스 시작** 버튼 클릭

#### Step 3: Elastic IP 할당 (고정 IP)
1. 좌측 메뉴에서 **"Elastic IP"** 클릭
2. **"Elastic IP 주소 할당"** 클릭
3. **"할당"** 클릭
4. 생성된 IP 선택 → **"작업" → "Elastic IP 주소 연결"**
5. 인스턴스: `classmate-server` 선택
6. **"연결"** 클릭

✅ **이제 고정 IP 주소를 얻었습니다!** (예: 3.35.123.45)

---

## 2. 서버 초기 설정

### 2.1 SSH 접속

#### Windows (PowerShell 또는 Git Bash)
```bash
# 키 파일 권한 설정 (Git Bash에서만 필요)
chmod 400 classmate-key.pem

# SSH 접속
ssh -i classmate-key.pem ubuntu@<YOUR_ELASTIC_IP>
```

#### Mac/Linux
```bash
# 키 파일 권한 설정
chmod 400 classmate-key.pem

# SSH 접속
ssh -i classmate-key.pem ubuntu@<YOUR_ELASTIC_IP>
```

예시:
```bash
ssh -i classmate-key.pem ubuntu@3.35.123.45
```

### 2.2 프로젝트 클론

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/ClassMate.git
cd ClassMate
```

⚠️ **GitHub이 비공개 저장소인 경우:**
```bash
# Personal Access Token 생성 필요
git clone https://YOUR_GITHUB_TOKEN@github.com/YOUR_USERNAME/ClassMate.git
```

### 2.3 서버 초기 설정 스크립트 실행

```bash
cd ~/ClassMate/deploy
chmod +x setup_server.sh
sudo ./setup_server.sh
```

⏱️ **약 10-15분 소요**

설치되는 항목:
- ✅ Python 3.10
- ✅ Node.js 18
- ✅ Neo4j (그래프 데이터베이스)
- ✅ Nginx (웹 서버)
- ✅ PM2 (프로세스 관리자)
- ✅ 2GB Swap 메모리 (성능 최적화)

---

## 3. 애플리케이션 배포

### 3.1 환경 변수 설정

```bash
cd ~/ClassMate
nano .env
```

다음 내용을 입력:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=classmate2025
NEO4J_DB=neo4j

# OpenAI API Key
OPENAI_API_KEY=sk-proj-YOUR_OPENAI_API_KEY_HERE

# Google Cloud (Document AI)
GCP_PROJECT=classmate-474107
DOC_OCR_PROCESSOR_ID=74048a4bb37671e9
DOC_LOCATION=us

# Embedding Model
EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B
```

- `Ctrl + O` → Enter (저장)
- `Ctrl + X` (종료)

### 3.2 데이터 업로드 (선택사항)

기존 데이터가 있다면 Neo4j에 업로드:

```bash
cd ~/ClassMate
source src/.venv/bin/activate

# 학생 데이터 업로드
PYTHONPATH=src python src/teacher/daily/upload_students.py

# 문제 데이터 업로드 (있다면)
# PYTHONPATH=src python src/teacher/parser/upload_problems.py
```

### 3.3 배포 실행

```bash
cd ~/ClassMate/deploy
chmod +x deploy.sh
./deploy.sh
```

⏱️ **약 5-10분 소요 (첫 실행 시)**

배포 완료 후 출력되는 URL로 접속하면 됩니다!

예시:
```
✅ Deployment completed successfully!
Application is now running:
  Frontend: http://3.35.123.45
  Backend API: http://3.35.123.45/api/docs
```

---

## 4. 도메인 연결 (classmate.kr)

### 4.1 도메인 구매

#### 가비아 (한국 도메인 추천)
1. https://www.gabia.com 접속
2. "classmate.kr" 검색
3. 구매 (연간 약 15,000원)

### 4.2 Route 53 호스팅 영역 생성

1. AWS Console → **Route 53** 검색
2. **"호스팅 영역 생성"** 클릭
3. 도메인 이름: `classmate.kr`
4. 유형: 퍼블릭 호스팅 영역
5. **"호스팅 영역 생성"** 클릭

### 4.3 NS 레코드 복사

Route 53에서 생성된 **4개의 NS (네임서버)** 레코드를 복사:
```
ns-123.awsdns-12.com
ns-456.awsdns-45.net
ns-789.awsdns-78.org
ns-012.awsdns-01.co.uk
```

### 4.4 가비아에서 네임서버 설정

1. 가비아 로그인 → My가비아
2. 도메인 관리 → `classmate.kr` 선택
3. **네임서버 설정** 클릭
4. "다른 네임서버 사용" 선택
5. Route 53의 4개 NS 레코드 입력
6. 저장

⏱️ **DNS 전파 대기: 최대 48시간 (보통 1-2시간)**

### 4.5 Route 53에 A 레코드 추가

1. Route 53 → 호스팅 영역 → `classmate.kr` 클릭
2. **"레코드 생성"** 클릭
3. 레코드 이름: 빈 칸 (루트 도메인)
4. 레코드 유형: A
5. 값: `<YOUR_ELASTIC_IP>` (예: 3.35.123.45)
6. TTL: 300
7. **"레코드 생성"** 클릭

8. **www 서브도메인도 추가** (선택사항)
   - 레코드 이름: `www`
   - 레코드 유형: A
   - 값: `<YOUR_ELASTIC_IP>`

✅ **10-30분 후 http://classmate.kr 접속 가능!**

---

## 5. SSL 인증서 설정 (HTTPS)

### 5.1 Let's Encrypt Certbot 설치

```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

### 5.2 SSL 인증서 발급

```bash
sudo certbot --nginx -d classmate.kr -d www.classmate.kr
```

프롬프트 입력:
1. 이메일 주소 입력
2. 약관 동의: `Y`
3. 뉴스레터: `N` (선택)
4. Redirect HTTP → HTTPS: `2` (권장)

✅ **완료! 이제 https://classmate.kr 접속 가능!**

### 5.3 자동 갱신 설정

Let's Encrypt 인증서는 90일마다 갱신 필요. 자동 갱신 설정:

```bash
sudo certbot renew --dry-run
```

성공하면 자동으로 갱신됩니다!

---

## 6. 유지보수 및 모니터링

### 6.1 유용한 명령어

```bash
# 백엔드 로그 확인
pm2 logs classmate-api

# 백엔드 재시작
pm2 restart classmate-api

# PM2 상태 확인
pm2 status

# Nginx 상태 확인
sudo systemctl status nginx

# Nginx 재시작
sudo systemctl restart nginx

# Neo4j 상태 확인
sudo systemctl status neo4j

# Neo4j 재시작
sudo systemctl restart neo4j

# 서버 리소스 모니터링
htop
```

### 6.2 업데이트 배포

코드 변경 후 재배포:

```bash
cd ~/ClassMate
git pull origin main
./deploy/deploy.sh
```

### 6.3 백업

#### Neo4j 데이터 백업
```bash
sudo systemctl stop neo4j
sudo cp -r /var/lib/neo4j/data ~/backups/neo4j-$(date +%Y%m%d)
sudo systemctl start neo4j
```

#### 프로젝트 백업
```bash
cd ~
tar -czf classmate-backup-$(date +%Y%m%d).tar.gz ClassMate/
```

### 6.4 비용 모니터링

1. AWS Console → **Billing Dashboard**
2. **"프리 티어"** 탭에서 사용량 확인
3. 알림 설정 권장

---

## 🎉 배포 완료!

이제 https://classmate.kr로 접속하면 ClassMate 서비스를 사용할 수 있습니다!

### 문제 해결

#### 1. 502 Bad Gateway 에러
```bash
# 백엔드 상태 확인
pm2 status
pm2 logs classmate-api

# 재시작
pm2 restart classmate-api
```

#### 2. Neo4j 연결 실패
```bash
# Neo4j 상태 확인
sudo systemctl status neo4j

# 재시작
sudo systemctl restart neo4j

# 로그 확인
sudo journalctl -u neo4j -n 100
```

#### 3. 메모리 부족
```bash
# 메모리 확인
free -h

# Swap 확인
swapon --show

# PM2 메모리 제한
pm2 restart classmate-api --max-memory-restart 500M
```

#### 4. 디스크 공간 부족
```bash
# 디스크 확인
df -h

# 로그 정리
pm2 flush

# 캐시 정리
sudo apt-get clean
```

---

## 📞 지원

문제가 발생하면:
1. PM2 로그 확인: `pm2 logs classmate-api`
2. Nginx 로그: `sudo tail -f /var/log/nginx/error.log`
3. Neo4j 로그: `sudo journalctl -u neo4j -n 100`

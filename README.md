# video crawler for KOOC
24년 6월 서비스 종료하는 KOOC 강의 영상을 백업하기 위한 스크립트 (개인 학습용)

## requirements
- HLS 조각을 합치는데 `ffmpeg` 를 사용합니다.
- SSO 가 아닌 email 로 가입한 계정을 사용합니다.

## how to use it
```
pip install -e .
python crawl.py {email} {password}
```

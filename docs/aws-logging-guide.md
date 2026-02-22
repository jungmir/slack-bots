# AWS CloudWatch Logs 운영 가이드

이 문서는 PyCon Slack Bot을 ECS에 배포한 뒤 CloudWatch Logs와 연동하여
로그를 조회하고 알림을 설정하는 방법을 안내합니다.

---

## 1. ECS 태스크 정의 설정

ECS 태스크 정의에서 `awslogs` 드라이버를 사용하면 컨테이너 stdout이
자동으로 CloudWatch Logs에 전송됩니다.

```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/pycon-slack-bot",
      "awslogs-region": "ap-northeast-2",
      "awslogs-stream-prefix": "bot"
    }
  }
}
```

> **참고**: `LOG_JSON=true` (기본값) 설정 시 모든 로그가 JSON 형식으로
> 출력되어 CloudWatch Logs Insights에서 구조화 쿼리가 가능합니다.

---

## 2. CloudWatch Logs Insights 쿼리 예시

### 2.1 최근 에러 로그 조회

```
fields @timestamp, event, request_id, exc_info
| filter @message like /"level":"error"/
| sort @timestamp desc
| limit 50
```

### 2.2 특정 사용자의 요청 추적 (Request ID 기반)

```
fields @timestamp, event, level, request_id
| filter request_id = "550e8400-e29b-41d4-a716-446655440000"
| sort @timestamp asc
```

### 2.3 Slack 사용자별 활동 조회

```
fields @timestamp, event, command, slack_user_id
| filter slack_user_id = "U0123ABCDEF"
| sort @timestamp desc
| limit 100
```

### 2.4 슬래시 커맨드 사용 빈도 분석

```
fields command
| filter ispresent(command)
| stats count(*) as cnt by command
| sort cnt desc
```

### 2.5 에러율 추이 (15분 간격)

```
fields @timestamp
| filter @message like /"level":"error"/
| stats count(*) as error_count by bin(15m)
| sort @timestamp
```

### 2.6 Dooray API 호출 추적

```
fields @timestamp, event, method, path, request_id
| filter event = "dooray_api_request"
| sort @timestamp desc
| limit 50
```

### 2.7 응답 시간이 긴 요청 (느린 요청 분석)

```
fields @timestamp, event, request_id, duration_ms
| filter ispresent(duration_ms) and duration_ms > 3000
| sort duration_ms desc
| limit 20
```

---

## 3. CloudWatch Alarm 설정

### 3.1 Metric Filter: 에러 로그 카운트

CloudWatch Logs → Log Group → **Metric Filter** 생성:

- **Filter Pattern**: `{ $.level = "error" }`
- **Metric Namespace**: `PyCon/SlackBot`
- **Metric Name**: `ErrorCount`
- **Metric Value**: `1`
- **Default Value**: `0`

### 3.2 Alarm: 에러 급증 감지

CloudWatch Alarms → **Create Alarm**:

| 항목 | 값 |
|------|-----|
| Metric | `PyCon/SlackBot` → `ErrorCount` |
| Statistic | Sum |
| Period | 5분 |
| Threshold | >= 10 |
| Datapoints to alarm | 1 out of 1 |
| Action | SNS Topic → Slack/Email 알림 |

### 3.3 Alarm: 헬스체크 실패 감지

ECS 서비스에서 ALB Target Group을 사용하는 경우:

| 항목 | 값 |
|------|-----|
| Metric | `AWS/ApplicationELB` → `UnHealthyHostCount` |
| Target Group | 봇 서비스 Target Group |
| Threshold | >= 1 |
| Period | 1분 |
| Action | SNS → 즉시 알림 |

---

## 4. ECS 헬스체크 설정

### 4.1 ALB Target Group 헬스체크

```
Health Check Path: /healthz
Health Check Port: 8080
Healthy Threshold: 2
Unhealthy Threshold: 3
Timeout: 5 seconds
Interval: 30 seconds
```

### 4.2 ECS 태스크 정의 헬스체크

```json
{
  "healthCheck": {
    "command": ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"],
    "interval": 30,
    "timeout": 5,
    "retries": 3,
    "startPeriod": 10
  }
}
```

### 4.3 Readiness Probe

`/readyz` 엔드포인트를 ALB의 readiness check에 사용할 수 있습니다.
향후 DB 연결 상태 등 추가적인 준비 상태 확인이 필요한 경우
`_handle_readyz` 메서드를 확장하면 됩니다.

---

## 5. 환경 변수 요약

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LOG_JSON` | `true` | JSON 구조화 로깅 활성화 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) |
| `SENTRY_DSN` | (없음) | Sentry DSN (비어있으면 비활성화) |
| `SENTRY_ENVIRONMENT` | `dev` | Sentry 환경 태그 |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | Sentry 성능 모니터링 샘플링 비율 |
| `HEALTHCHECK_PORT` | `8080` | 헬스체크 HTTP 서버 포트 |

---

## 6. 로그 JSON 구조 예시

모든 로그는 다음과 같은 JSON 형식으로 출력됩니다:

```json
{
  "event": "dooray_api_request",
  "level": "debug",
  "timestamp": "2025-02-23T00:15:30.123456Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "slack_user_id": "U0123ABCDEF",
  "channel_id": "C0123ABCDEF",
  "command": "/dooray",
  "method": "GET",
  "path": "/project/v1/projects/123/posts"
}
```

이 구조 덕분에 CloudWatch Logs Insights에서 JSON 필드 기반
쿼리가 가능합니다.

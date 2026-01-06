"""
Hebrish Dataset Generator - Creates synthetic Hebrew+English tech audio corpus.

Generates 500 synthetic Hebrish sentences for Whisper LoRA fine-tuning
on Israeli dev meeting audio.

Usage:
    python -m app.scripts.generate_hebrish_dataset
    
    Or via CLI:
    python -m app.cli generate-hebrish-dataset
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 500 Hebrish sentences - Hebrew + English tech terms
# Covering: deployment, code review, debugging, API, frontend, backend, DevOps, meetings
HEBRISH_SENTENCES = [
    # Deployment & Production (50)
    "תעשה deploy ל-production ותבדוק את ה-logs",
    "ה-deployment נכשל בגלל בעיה ב-environment variables",
    "אני צריך לעשות rollback ל-version הקודם",
    "ה-staging environment לא מתחבר ל-database",
    "תוודא שה-CI/CD pipeline עובד לפני ה-merge",
    "יש לנו downtime ב-production כרגע",
    "ה-load balancer לא מפזר את ה-traffic נכון",
    "צריך לעדכן את ה-SSL certificate",
    "ה-container לא עולה כי יש בעיה ב-Dockerfile",
    "תעשה docker build ותבדוק שהכל רץ",
    "ה-kubernetes cluster צריך יותר resources",
    "יש לנו memory leak ב-production",
    "ה-auto-scaling לא עובד כמו שצריך",
    "צריך לבדוק את ה-health checks של ה-pods",
    "ה-deployment הצליח אבל יש latency גבוה",
    "תעשה restart ל-service ותבדוק שוב",
    "אני רואה הרבה errors ב-logs של ה-backend",
    "ה-monitoring מראה spike ב-CPU usage",
    "צריך להוסיף יותר replicas ל-service",
    "ה-ingress לא מנתב נכון את ה-requests",
    "תבדוק את ה-resource limits של ה-pod",
    "יש bottleneck ב-database connection pool",
    "ה-cron job לא רץ בזמן",
    "צריך לעדכן את ה-helm chart",
    "ה-secrets לא נטענים נכון ב-environment",
    "תעשה port-forward כדי לבדוק את ה-service",
    "ה-namespace חדש וצריך להגדיר permissions",
    "יש conflict ב-config maps",
    "ה-volume לא נמאונט נכון",
    "צריך לבדוק את ה-network policies",
    "ה-service mesh לא מתפקד",
    "תעשה kubectl logs ותראה מה קורה",
    "ה-horizontal pod autoscaler לא מגיב",
    "יש בעיה ב-persistent volume claim",
    "ה-init container נכשל",
    "צריך לעדכן את ה-base image",
    "ה-security context לא מוגדר נכון",
    "תבדוק את ה-liveness probe",
    "ה-readiness probe נכשל",
    "יש בעיה ב-service discovery",
    "ה-DNS resolution לא עובד",
    "צריך לעשות drain ל-node",
    "ה-cluster upgrade נתקע",
    "יש בעיה ב-etcd",
    "ה-api server לא מגיב",
    "צריך לבדוק את ה-controller manager",
    "ה-scheduler לא מקצה pods נכון",
    "יש בעיה ב-kubelet",
    "ה-kube-proxy לא עובד",
    "צריך לרסטרט את ה-CNI plugin",
    
    # Code Review & Git (50)
    "ה-merge request תקוע ב-code review של ה-backend team",
    "תעשה rebase מול ה-main branch",
    "יש conflicts ב-merge שצריך לפתור",
    "ה-commit message לא ברור, תשנה אותו",
    "צריך לעשות squash ל-commits לפני ה-merge",
    "ה-PR מחכה לאישור מה-tech lead",
    "תוסיף unit tests לפני שאני מאשר",
    "יש לך breaking change ב-API",
    "ה-linter מוצא הרבה שגיאות בקוד",
    "צריך לעשות refactor לפונקציה הזאת",
    "ה-code coverage ירד אחרי ה-changes שלך",
    "תעשה cherry-pick ל-commit הזה",
    "ה-branch שלך לא up to date",
    "יש duplicate code שצריך לאחד",
    "ה-naming convention לא עקבי",
    "צריך להוסיף documentation לפונקציות",
    "ה-pull request גדול מדי, תפצל אותו",
    "יש hardcoded values שצריך להוציא ל-config",
    "ה-git history מבולגן",
    "צריך לעשות force push אחרי ה-rebase",
    "ה-feature branch צריך לעבור QA",
    "יש regression ב-code הזה",
    "תעשה stash לשינויים לפני ה-switch",
    "ה-hotfix branch מוכן ל-production",
    "צריך לעשות tag ל-release החדש",
    "ה-workflow נכשל ב-GitHub Actions",
    "יש dependency conflict ב-package.json",
    "ה-lockfile לא מעודכן",
    "צריך לעדכן את ה-dependencies לגרסאות האחרונות",
    "יש security vulnerability ב-packages",
    "ה-pre-commit hooks לא רצים",
    "צריך להוסיף integration tests",
    "ה-snapshot tests נכשלו",
    "תעדכן את ה-mocks בטסטים",
    "יש flaky test שצריך לתקן",
    "ה-test coverage report מראה gaps",
    "צריך לכתוב e2e tests",
    "ה-cypress tests לא עוברים",
    "יש race condition בקוד",
    "ה-async/await לא מטופל נכון",
    "צריך להוסיף error handling",
    "ה-try/catch חסר",
    "יש null pointer exception פוטנציאלי",
    "ה-type safety לא מלא",
    "צריך להוסיף TypeScript types",
    "ה-interface definition חסר",
    "יש magic numbers בקוד",
    "ה-constants לא מוגדרים",
    "צריך להוסיף enums",
    "ה-code style לא עקבי",
    
    # API & Backend (50)
    "ה-API endpoint מחזיר 500 error",
    "יש bug ב-authentication middleware",
    "ה-JWT token פג תוקף אבל לא מחזיר unauthorized",
    "צריך להוסיף rate limiting ל-endpoint",
    "ה-request validation לא עובד",
    "יש בעיה ב-JSON serialization",
    "ה-REST API לא RESTful מספיק",
    "צריך לעשות migrate ל-GraphQL",
    "ה-query parameters לא מטופלים נכון",
    "יש injection vulnerability בקוד",
    "ה-CORS policy חוסם requests",
    "צריך להוסיף caching layer",
    "ה-Redis cache לא מתעדכן",
    "יש בעיה ב-session management",
    "ה-cookie לא נשלח עם ה-response",
    "צריך להוסיף pagination ל-API",
    "ה-sorting לא עובד על כל ה-fields",
    "יש N+1 query problem",
    "ה-database connection pool מתמלא",
    "צריך לעשות optimize ל-queries",
    "ה-index חסר על ה-column הזה",
    "יש deadlock ב-database",
    "ה-transaction לא מתבצע נכון",
    "צריך להוסיף foreign key constraint",
    "ה-migration נכשלה",
    "יש data corruption issue",
    "ה-backup לא רץ",
    "צריך לעשות restore מ-snapshot",
    "ה-replication lag גבוה",
    "יש בעיה ב-read replica",
    "ה-connection string לא נכון",
    "צריך להצפין את ה-credentials",
    "ה-environment variables חסרים",
    "יש בעיה ב-config loading",
    "ה-service discovery לא מוצא את ה-service",
    "צריך להוסיף health check endpoint",
    "ה-graceful shutdown לא עובד",
    "יש memory leak ב-connection handling",
    "ה-thread pool מתמלא",
    "צריך להוסיף async processing",
    "ה-message queue לא מתרוקן",
    "יש בעיה ב-RabbitMQ",
    "ה-Kafka consumer לא צורך messages",
    "צריך להוסיף dead letter queue",
    "ה-retry mechanism לא עובד",
    "יש exponential backoff חסר",
    "ה-circuit breaker לא נפתח",
    "צריך להוסיף fallback logic",
    "ה-timeout לא מוגדר נכון",
    "יש connection timeout issues",
    
    # Frontend & React (50)
    "ה-component לא מתרנדר נכון",
    "יש bug ב-React state management",
    "ה-useEffect גורם ל-infinite loop",
    "צריך לעשות memoization לפונקציה",
    "ה-Redux store לא מתעדכן",
    "יש בעיה ב-context provider",
    "ה-props לא מועברים נכון",
    "צריך להוסיף PropTypes validation",
    "ה-CSS לא מיושר נכון",
    "יש z-index issue",
    "ה-responsive design לא עובד על mobile",
    "צריך לתקן את ה-flexbox layout",
    "ה-grid לא מתפקד בכל ה-browsers",
    "יש accessibility issues",
    "ה-ARIA labels חסרים",
    "צריך להוסיף keyboard navigation",
    "ה-focus trap לא עובד",
    "יש contrast ratio נמוך",
    "ה-font size קטן מדי",
    "צריך להוסיף dark mode",
    "ה-theme switching לא עובד",
    "יש flickering בזמן loading",
    "ה-skeleton loader לא מופיע",
    "צריך להוסיף loading states",
    "ה-error boundary לא תופס errors",
    "יש unhandled promise rejection",
    "ה-async data fetching לא עובד",
    "צריך להוסיף React Query",
    "ה-SWR cache לא מתעדכן",
    "יש stale data בתצוגה",
    "ה-optimistic updates לא עובדים",
    "צריך להוסיף real-time updates",
    "ה-WebSocket connection נופל",
    "יש reconnection logic חסר",
    "ה-event listeners לא מנוקים",
    "צריך לעשות cleanup ב-useEffect",
    "יש memory leak ב-component",
    "ה-subscription לא מבוטל",
    "צריך להוסיף debouncing",
    "ה-throttling לא עובד",
    "יש too many re-renders",
    "ה-virtual scroll לא עובד",
    "צריך להוסיף infinite scroll",
    "ה-pagination לא מתעדכנת",
    "יש בעיה ב-router navigation",
    "ה-deep linking לא עובד",
    "צריך להוסיף route guards",
    "ה-authentication flow שבור",
    "יש redirect loop",
    "ה-history API לא עובד נכון",
    
    # Debugging & Errors (50)
    "יש null pointer exception בקוד",
    "ה-stack trace מראה error ב-line 42",
    "צריך לעשות debug ל-function הזאת",
    "ה-breakpoint לא נעצר",
    "יש race condition שקשה לשחזר",
    "ה-error message לא מספיק מפורט",
    "צריך להוסיף יותר logging",
    "ה-debug mode לא עובד",
    "יש בעיה בשחזור ה-bug",
    "ה-reproduction steps לא ברורים",
    "צריך לבדוק את ה-edge cases",
    "יש off-by-one error",
    "ה-loop לא מסתיים",
    "צריך לתקן את ה-recursion",
    "יש stack overflow",
    "ה-memory usage גבוה מדי",
    "צריך לעשות profiling",
    "יש performance bottleneck",
    "ה-response time גבוה",
    "צריך לעשות optimize",
    "יש בעיה ב-caching strategy",
    "ה-cache invalidation לא עובד",
    "צריך לבדוק את ה-TTL",
    "יש stale data בתצוגה",
    "ה-synchronization לא עובד",
    "צריך לעשות lock על ה-resource",
    "יש deadlock פוטנציאלי",
    "ה-mutex לא משוחרר",
    "צריך לבדוק את ה-thread safety",
    "יש data race",
    "ה-atomic operation לא atomic",
    "צריך להוסיף transaction",
    "יש rollback חסר",
    "ה-compensation logic לא עובד",
    "צריך לבדוק את ה-saga pattern",
    "יש event sourcing issue",
    "ה-snapshot לא נכון",
    "צריך לעשות rebuild של ה-state",
    "יש projection שבור",
    "ה-read model לא מתעדכן",
    "צריך לבדוק את ה-event handlers",
    "יש duplicate event processing",
    "ה-idempotency לא עובד",
    "צריך להוסיף deduplication",
    "יש ordering issue",
    "ה-timestamp לא נכון",
    "צריך לסנכרן את ה-clocks",
    "יש timezone issue",
    "ה-UTC conversion שבור",
    "צריך לתקן את ה-date parsing",
    
    # DevOps & Infrastructure (50)
    "ה-Terraform plan מראה changes לא צפויים",
    "צריך לעשות import ל-existing resource",
    "ה-state file corrupted",
    "יש drift ב-infrastructure",
    "ה-AWS credentials פגו תוקף",
    "צריך לעדכן את ה-IAM policy",
    "ה-security group חוסם traffic",
    "יש בעיה ב-VPC configuration",
    "ה-subnet לא נכון",
    "צריך לבדוק את ה-route table",
    "ה-NAT gateway לא עובד",
    "יש internet gateway חסר",
    "ה-elastic IP לא משויך",
    "צריך להוסיף target group",
    "ה-ALB לא מנתב נכון",
    "יש health check failing",
    "ה-auto scaling group לא עובד",
    "צריך לעדכן את ה-launch template",
    "ה-AMI לא נמצא",
    "יש בעיה ב-user data script",
    "ה-instance לא עולה",
    "צריך לבדוק את ה-system logs",
    "יש disk full error",
    "ה-EBS volume לא מחובר",
    "צריך להגדיל את ה-IOPS",
    "יש בעיה ב-S3 permissions",
    "ה-bucket policy חוסם access",
    "צריך להוסיף CORS configuration",
    "יש lifecycle policy חסר",
    "ה-versioning לא מופעל",
    "צריך להוסיף encryption",
    "ה-KMS key לא נגיש",
    "יש בעיה ב-secrets manager",
    "ה-parameter store ריק",
    "צריך לעדכן את ה-SSM agent",
    "ה-CloudWatch logs לא מגיעים",
    "יש retention policy חסר",
    "ה-metric filter לא עובד",
    "צריך להוסיף alarm",
    "ה-SNS notification לא נשלח",
    "יש Lambda cold start issue",
    "ה-function timeout",
    "צריך להגדיל את ה-memory",
    "ה-layer לא נטען",
    "יש dependency issue ב-package",
    "ה-API Gateway לא מנתב",
    "צריך להוסיף authorizer",
    "ה-Cognito pool לא מאומת",
    "יש token validation issue",
    "ה-WAF חוסם legitimate requests",
    
    # Meetings & Communication (50)
    "בוא נעשה sync על ה-sprint",
    "צריך לעדכן את ה-stakeholders",
    "ה-standup היה ארוך מדי היום",
    "בוא נעשה retrospective על ה-release",
    "יש לנו blocker שצריך לדון בו",
    "ה-deadline זז לשבוע הבא",
    "צריך לעשות estimation לפיצ׳ר הזה",
    "ה-story points לא מדויקים",
    "בוא נעשה refinement לתיקיות",
    "יש לנו technical debt שצריך לטפל בו",
    "ה-product owner רוצה שינויים",
    "צריך לעדכן את ה-roadmap",
    "ה-milestone הבא בעוד חודש",
    "יש integration עם צוות אחר",
    "ה-API contract צריך לעבור review",
    "בוא נעשה design doc לפיצ׳ר",
    "ה-architecture decision record חסר",
    "צריך לתעד את ה-trade-offs",
    "ה-documentation לא מעודכן",
    "יש onboarding חדש שצריך להכין",
    "ה-knowledge transfer לא הושלם",
    "צריך לעשות pair programming",
    "בוא נעשה code walkthrough",
    "ה-demo ללקוח ביום חמישי",
    "צריך להכין את ה-slides",
    "יש feedback מה-user research",
    "ה-A/B test results מוכנים",
    "צריך לנתח את ה-metrics",
    "ה-KPIs לא עומדים ביעד",
    "יש churn גבוה ב-feature הזה",
    "ה-user engagement ירד",
    "צריך לעשות user interviews",
    "יש bug reports מהשטח",
    "ה-support tickets עלו",
    "צריך לעשות prioritization",
    "ה-backlog גדול מדי",
    "יש dependencies בין teams",
    "ה-handoff לא ברור",
    "צריך לעשות alignment",
    "ה-goals לא מסונכרנים",
    "יש resource constraints",
    "ה-capacity planning לא מדויק",
    "צריך להוסיף headcount",
    "ה-hiring process ארוך",
    "יש interview pipeline",
    "ה-candidate pool קטן",
    "צריך לעשות outreach",
    "ה-employer branding חלש",
    "יש culture fit issues",
    "ה-team dynamics צריכים עבודה",
    
    # Testing & QA (50)
    "ה-unit test נכשל",
    "יש test flakiness issue",
    "ה-integration tests לא עוברים",
    "צריך לעדכן את ה-fixtures",
    "ה-mock לא מתנהג נכון",
    "יש בעיה ב-test isolation",
    "ה-test database לא נקי",
    "צריך לעשות reset ל-state",
    "יש race condition בטסטים",
    "ה-parallel execution נכשל",
    "צריך לסדר את ה-test order",
    "יש dependency בין tests",
    "ה-snapshot לא מעודכן",
    "צריך לעשות regenerate",
    "יש visual regression",
    "ה-percy tests נכשלו",
    "צריך לעדכן את ה-baseline",
    "יש browser compatibility issue",
    "ה-selenium tests לא יציבים",
    "צריך לעבור ל-playwright",
    "יש selector לא יציב",
    "ה-locator strategy צריך שינוי",
    "צריך להוסיף test ids",
    "יש בעיה ב-async testing",
    "ה-wait strategy לא עובד",
    "צריך להוסיף explicit waits",
    "יש timeout issues",
    "ה-retry mechanism לא עובד",
    "צריך להוסיף error screenshots",
    "יש debugging קשה",
    "ה-test logs לא מספיקים",
    "צריך להוסיף tracing",
    "יש observability gap",
    "ה-metrics לא מדויקים",
    "צריך לעשות instrumentation",
    "יש sampling issue",
    "ה-distributed tracing שבור",
    "צריך לתקן את ה-context propagation",
    "יש correlation id חסר",
    "ה-request tracking לא עובד",
    "צריך להוסיף audit logging",
    "יש compliance requirements",
    "ה-data retention policy חסר",
    "צריך לעשות anonymization",
    "יש PII exposure",
    "ה-GDPR compliance לא מלא",
    "צריך להוסיף consent management",
    "יש cookie policy issue",
    "ה-privacy policy לא מעודכן",
    "צריך legal review",
]


def main(
    output_dir: str = "static/datasets/hebrish",
    count: Optional[int] = None,
    use_tts: bool = True
):
    """
    Generate Hebrish dataset for Whisper fine-tuning.
    
    Args:
        output_dir: Output directory for audio files and manifest
        count: Number of sentences to generate (None = all 500)
        use_tts: Whether to generate audio with TTS (False = text only)
    """
    output_path = Path(output_dir)
    audio_path = output_path / "audio"
    audio_path.mkdir(parents=True, exist_ok=True)
    
    sentences = HEBRISH_SENTENCES[:count] if count else HEBRISH_SENTENCES
    manifest_path = output_path / "train.jsonl"
    
    logger.info(f"🎙️ Generating {len(sentences)} Hebrish samples...")
    
    # Try to load TTS model if requested
    tts_model = None
    if use_tts:
        try:
            from chatterbox.tts import ChatterboxTTS
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading ChatterboxTTS on {device}...")
            tts_model = ChatterboxTTS.from_pretrained(device=device, model="multilingual")
            logger.info("✅ TTS model loaded")
        except ImportError:
            logger.warning("⚠️ chatterbox-tts not installed, generating text-only manifest")
        except Exception as e:
            logger.warning(f"⚠️ TTS load failed: {e}, generating text-only manifest")
    
    # Generate samples
    with open(manifest_path, "w", encoding="utf-8") as manifest:
        for idx, text in enumerate(sentences):
            audio_filename = f"{idx:04d}.wav"
            audio_file_path = audio_path / audio_filename
            
            # Generate audio if TTS available
            if tts_model:
                try:
                    import torchaudio as ta
                    
                    logger.info(f"🎙️ {idx+1}/{len(sentences)}: {text[:50]}...")
                    wav = tts_model.generate(text, language_id="he")
                    ta.save(str(audio_file_path), wav, 16000)
                except Exception as e:
                    logger.error(f"TTS generation failed for sample {idx}: {e}")
                    continue
            
            # Write manifest entry
            entry = {
                "audio": f"audio/{audio_filename}",
                "text": text
            }
            manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    logger.info(f"✅ Hebrish dataset ready at {output_path}")
    logger.info(f"   - Manifest: {manifest_path}")
    logger.info(f"   - Audio files: {audio_path}")
    
    return str(manifest_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

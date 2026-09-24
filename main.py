"""Run a local receipt audit; email delivery is explicitly opt-in."""
import argparse
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
from app.agent.expense_agent import ExpenseAgent
from app.guardrails.policy_guardrails import PolicyGuardrailEvaluator
from app.services.email_service import EmailService


def run_pipeline_with_ocr():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='Use clearly labeled deterministic sample data')
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--employee-email', default='employee@example.com')
    parser.add_argument('--employee-name', default='Demo Employee')
    parser.add_argument('--purpose', default='Business Expense')
    parser.add_argument('--send-email', action='store_true')
    args = parser.parse_args()
    if not args.demo and (args.receipt is None or args.employee_email == 'employee@example.com' or args.employee_name == 'Demo Employee'):
        parser.error('Real OCR requires --receipt, --employee-email and --employee-name')
    agent = ExpenseAgent(demo=args.demo)
    report = agent.parse_receipt_image(
        image_bytes=args.receipt.read_bytes() if args.receipt else b'',
        mime_type=mimetypes.guess_type(str(args.receipt))[0] or 'application/octet-stream',
        employee_email=args.employee_email, employee_name=args.employee_name,
        purpose=('DEMO DATA: ' if args.demo else '') + args.purpose,
    )
    audit = PolicyGuardrailEvaluator().evaluate_report(report)
    if args.demo:
        print('DEMO DATA — no OCR performed')
    print(audit.model_dump_json(indent=2))
    if args.send_email:
        EmailService().send_audit_report(audit)


if __name__ == '__main__':
    run_pipeline_with_ocr()

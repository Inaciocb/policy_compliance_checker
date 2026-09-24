import unittest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from app.schemas.expense import ExpenseItem, EmployeeExpenseReport
from app.guardrails.policy_guardrails import PolicyGuardrailEvaluator
from app.agent.expense_agent import ExpenseAgent
from app.services.email_service import EmailService
from test_guardrails import test_guardrails_flag_prohibited_items


def item(amount='30', category='meal', **kwargs):
    return ExpenseItem(description='Purchase', amount=amount, category=category,
                       has_itemized_receipt=True, expense_date='2026-09-24', **kwargs)


def report(*items, **kwargs):
    return EmployeeExpenseReport(employee_name='<script>alert(1)</script>', employee_email='a@example.com',
                                 trip_or_purpose='Work', expenses=list(items), **kwargs)


class RegressionTests(unittest.TestCase):
    def test_original(self):
        test_guardrails_flag_prohibited_items()

    def test_invalid_money(self):
        for value in ['-1', 'NaN', 'Infinity', '1.001']:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                item(value)

    def test_empty_and_invalid_duration(self):
        with self.assertRaises(ValidationError):
            report()
        for days in [0, -1, None]:
            with self.assertRaises(ValidationError):
                report(item(), trip_duration_days=days)

    def test_daily_limit_not_averaged_over_trip(self):
        result = PolicyGuardrailEvaluator().evaluate_report(report(item(), item(), item(), trip_duration_days=3))
        self.assertEqual(result.total_compliant, 0)
        self.assertTrue(all('daily limit' in a.violations[-1] for a in result.itemized_audit))

    def test_separate_days(self):
        other = item('40'); other.expense_date = other.expense_date.replace(day=25)
        result = PolicyGuardrailEvaluator().evaluate_report(report(item('40'), item('40'), other))
        self.assertEqual(result.total_compliant, 120)

    def test_missing_date(self):
        meal = item(); meal.expense_date = None
        self.assertEqual(PolicyGuardrailEvaluator().evaluate_report(report(meal)).total_compliant, 0)

    def test_annual_history_and_accumulation(self):
        data = report(item('800', 'course'), item('700', 'course'))
        evaluator = PolicyGuardrailEvaluator()
        self.assertEqual(evaluator.evaluate_report(data).total_compliant, 0)
        self.assertEqual(evaluator.evaluate_report(data, course_spend_by_year={2026: 0}).total_compliant, 1500)
        self.assertEqual(evaluator.evaluate_report(data, course_spend_by_year={2026: 1}).total_compliant, 0)
        with self.assertRaises(ValidationError):
            evaluator.evaluate_report(data, course_spend_by_year={2026: -1})

    def test_boundaries_and_exact_totals(self):
        evaluator = PolicyGuardrailEvaluator()
        self.assertEqual(evaluator.evaluate_report(report(item('200', 'lodging'))).total_compliant, 200)
        self.assertEqual(evaluator.evaluate_report(report(item('200.01', 'lodging'))).total_compliant, 0)
        a = item('10', 'other'); a.has_itemized_receipt = False
        self.assertEqual(evaluator.evaluate_report(report(a)).total_compliant, 10)
        a.amount = Decimal('10.01')
        self.assertEqual(evaluator.evaluate_report(report(a)).total_compliant, 0)
        result = evaluator.evaluate_report(report(item('0.10'), item('0.20')))
        self.assertEqual(result.total_requested, Decimal('0.30'))

    def test_currency(self):
        self.assertEqual(PolicyGuardrailEvaluator().evaluate_report(report(item(currency='BRL'))).total_compliant, 0)

    def test_escape_html(self):
        a = item(); a.description = '<img src=x onerror=alert(1)>'
        html = EmailService()._build_html_email(PolicyGuardrailEvaluator().evaluate_report(report(a)))
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img', html)

    @patch.dict('os.environ', {}, clear=True)
    def test_credentials_and_explicit_key(self):
        with self.assertRaises(ValueError):
            ExpenseAgent()
        with patch('app.agent.expense_agent.OpenAI') as client:
            agent = ExpenseAgent(api_key='explicit-key')
            client.assert_called_once_with(api_key='explicit-key')
            parsed = report(item())
            message = MagicMock(refusal=None, parsed=parsed)
            agent.client.chat.completions.parse.return_value.choices = [MagicMock(message=message)]
            result = agent.parse_receipt_image(b'fake', 'image/png', 'trusted@example.com', 'Trusted')
            self.assertEqual(result.employee_email, 'trusted@example.com')
            self.assertEqual(result.employee_name, 'Trusted')
            message.parsed = None
            with self.assertRaises(ValueError):
                agent.parse_receipt_image(b'fake', 'image/png', 'a@example.com')
            with self.assertRaises(ValueError):
                agent.parse_receipt_image(b'%PDF', 'application/pdf', 'a@example.com')

    def test_demo_identity(self):
        parsed = ExpenseAgent(demo=True).parse_receipt_image(b'', '', 'a@example.com', 'Alice', 'Demo')
        self.assertEqual(parsed.employee_name, 'Alice')
        self.assertTrue(all('DEMO DATA' in i.description for i in parsed.expenses))


if __name__ == '__main__':
    unittest.main()

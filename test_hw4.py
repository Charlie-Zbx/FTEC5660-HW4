"""Focused contract and metamorphic tests, using invented source documents, no API."""
import ast
import unittest
from pathlib import Path
from unittest.mock import patch
import hw4 as hw


def report(company="Cedar Instruments Inc.", year=2025, cash="71.2", previous="63.4"):
    return f'''<html><body><h1>{company}</h1><p>Annual Report {year}</p>
    <p>Headquarters: Bristol</p><h2>Financial statements</h2><table>
    <caption>Balance sheet (USD millions)</caption>
    <thead><tr><th></th><th>{year}</th><th>{year-1}</th></tr></thead>
    <tbody><tr><th scope="row">Cash and cash equivalents</th><td>{cash}</td><td>{previous}</td></tr>
    <tr><th scope="row">Total assets</th><td>543.2</td><td>510.0</td></tr></tbody></table>
    <h2>Executive officers</h2><p>Elena Chen is Chief Financial Officer at 31 December {year}.</p>
    </body></html>'''


class Contracts(unittest.TestCase):
    def test_no_model_during_parsing_and_preserve_numbers(self):
        with patch.object(hw, "make_llm", side_effect=AssertionError("Model forbidden")):
            chunks = hw.chunk_document("renamed.html", report(cash="(1,234.50)"))
        self.assertTrue(chunks)
        self.assertTrue(all(len(c.page_content) <= 1500 for c in chunks))
        self.assertTrue(all(type(c.metadata["fiscal_year"]) is int for c in chunks))
        self.assertTrue(all(c.metadata["source"] == "renamed.html" for c in chunks))
        self.assertTrue(any("2025: (1,234.50)" in c.page_content for c in chunks))

    def test_multilevel_headers_and_sections(self):
        html = '''<table><caption>USD millions</caption><thead>
        <tr><th rowspan="2">Item</th><th colspan="2">Actual</th></tr>
        <tr><th>2025</th><th>2024</th></tr></thead><tbody>
        <tr><th colspan="3" scope="row">Assets</th></tr>
        <tr><th scope="row">Cash</th><td>12.3</td><td>9.0</td></tr></tbody></table>'''
        text = hw.table_to_text(html)
        self.assertIn("Cash | Actual / 2025: 12.3 | Actual / 2024: 9.0", text)
        self.assertIn("USD millions", text)
        self.assertIn("Assets", text)

    def test_query_entities_case_and_unknown_names(self):
        self.assertEqual(hw.parse_query("What was Cedar Instruments' operating income in FY2024?")["doc_type"], "annual_report")
        for name in ["Cedar Instruments", "cedar instruments inc.", "Cedar Instrument Systems"]:
            query = hw.parse_query(f"What was {name}'s revenue in FY2024, in USD millions?")
            self.assertEqual(query["companies"], [name.rstrip(".")])
            self.assertEqual(query["fiscal_year"], 2024)
        query = hw.parse_query("What FY2026 revenue does Silver Research forecast for Cedar Instruments, in USD millions?")
        self.assertEqual(query, {"companies": ["Cedar Instruments"], "fiscal_year": 2026,
                                 "doc_type": "research_report"})

    def test_prior_year_and_comparison(self):
        a = hw.chunk_document("a.html", report())
        b = hw.chunk_document("b.html", report("Cedar Payments Corp.", cash="23.1", previous="18.2"))
        index = hw.build_index(a + b)
        question = "Which company held more cash and cash equivalents at 31 December 2024: Cedar Instruments or Cedar Payments?"
        chunks = hw.retrieve(index, question)
        self.assertEqual({hw.company_key(c.metadata["company"]) for c in chunks}, {"cedar instruments", "cedar payments"})
        self.assertTrue(any("2024: 63.4" in c.page_content for c in chunks))
        self.assertTrue(any("2024: 18.2" in c.page_content for c in chunks))
        self.assertTrue(all(c in a + b for c in chunks))
        self.assertLessEqual(len(chunks), 5)
        reordered = hw.retrieve(hw.build_index(b + a), question)
        self.assertEqual({c.page_content for c in chunks}, {c.page_content for c in reordered})

    def test_abstention_and_corpus_isolation(self):
        first = hw.build_index(hw.chunk_document("a.html", report()))
        for question in ["What was Cedar Instrument Systems' revenue in FY2025?",
                         "What was Cedar Instruments' cash and cash equivalents in FY2020?",
                         "What was Cedar Instruments' lobbying expenditure in FY2025?"]:
            self.assertEqual(hw.retrieve(first, question), [], question)
        second = hw.build_index(hw.chunk_document("z.html", report("Amber Devices Inc.")))
        self.assertEqual(hw.retrieve(second, "How much cash and cash equivalents did Cedar Instruments hold at 31 December 2025?"), [])
        self.assertTrue(hw.retrieve(first, "How much cash and cash equivalents did Cedar Instruments hold at 31 December 2025?"))

    def test_headquarters_no_year_and_long_paragraph(self):
        chunks = hw.chunk_document("a.html", report().replace("</body>", "<p>" + "A detailed discussion. " * 200 + "</p></body>"))
        self.assertTrue(all(len(c.page_content) <= 1500 for c in chunks))
        question = "In which city is Cedar Instruments headquartered?"
        self.assertIsNone(hw.parse_query(question)["fiscal_year"])
        self.assertTrue(any("Bristol" in c.page_content for c in hw.retrieve(hw.build_index(chunks), question)))

    def test_empty_index_and_bad_document(self):
        self.assertEqual(hw.retrieve(hw.build_index([]), "Anything?"), [])
        with self.assertRaisesRegex(ValueError, "Missing company"):
            hw.chunk_document("empty.html", "")

    def test_quarter_and_quantity_words_do_not_cause_false_rejection(self):
        html = '''<h1>Cedar Instruments Inc. (EX: CI)</h1>
        <h2>Fourth Quarter and Full Year 2025 Earnings Conference Call</h2>
        <p>The board approved a share repurchase programme of up to USD 42 million.</p>'''
        index = hw.build_index(hw.chunk_document("call.html", html))
        question = "On its Q4 FY2025 earnings call, how large a share repurchase programme did Cedar Instruments announce, in USD millions?"
        self.assertTrue(any("42" in c.page_content for c in hw.retrieve(index, question)))

    def test_student_code_does_not_read_labels_or_create_clients(self):
        student = Path(hw.__file__).read_text(encoding="utf-8").split("# Provided code below.")[0]
        tree = ast.parse(student)
        forbidden = {"open", "read_text", "read_bytes", "load_json", "ChatDeepSeek", "OpenAI"}
        calls = {node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                 for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, (ast.Name, ast.Attribute))}
        self.assertFalse(calls & forbidden)


if __name__ == "__main__":
    unittest.main()

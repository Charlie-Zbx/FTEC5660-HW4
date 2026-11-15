"""Independent invented-company checks. Expected facts come from the HTML below."""
import unittest
from unittest.mock import patch
import hw4 as h


def annual(company='Juniper Devices Inc.', year=2025):
    return f'''<h1>{company}</h1><p>Annual Report {year}</p>
    <p>Headquarters: York</p><h2>Balance sheet</h2><table>
    <caption>Consolidated balance sheet (USD millions)</caption>
    <thead><tr><th>Metric</th><th>{year}</th><th>{year-1}</th></tr></thead>
    <tbody><tr><td>Cash and cash equivalents</td><td>81.3</td><td>62.1</td></tr>
    <tr><td>Total assets</td><td>911.2</td><td>850.4</td></tr>
    <tr><td>Revenue</td><td>1,804.7</td><td>1,600.2</td></tr>
    <tr><td>Total employees</td><td>712</td><td>680</td></tr></tbody></table>
    <h2>Letter to shareholders</h2><p>Revenue was about USD 1.8 billion.</p>
    <h2>Executive officers</h2><table><caption>Executive officers at 31 December {year}</caption>
    <thead><tr><th>Name</th><th>Title</th></tr></thead><tbody>
    <tr><td>Nora Lin</td><td>Chief Financial Officer</td></tr></tbody></table>
    <p>Nora Lin succeeded Adam Reed as Chief Financial Officer in March {year}.</p>
    <h2>Independent auditor</h2><p>Grant Dale LLP audited the financial statements for {year}.</p>
    <p>The previous auditor was Stowe Audit LLP.</p>
    <h2>Disclosures</h2><p>Lobbying expenses are not disclosed.</p>
    <p>Customer churn rate is not reported.</p>'''


def research():
    return '''<div class="broker">Pine Equity Research</div><h1>Juniper Devices Inc. (JDI)</h1>
    <h2>FY2025 results review: steady growth</h2><p>Rating: BUY</p>
    <h3>Estimate changes</h3><p>Our previous FY2026 revenue estimate was USD 1,850.0 million.
    The new FY2026 revenue estimate is USD 1,930.6 million.</p>
    <table><caption>Financial summary and Pine Equity Research estimates (USD millions)</caption>
    <thead><tr><th></th><th>FY2025A</th><th>FY2026E</th></tr></thead><tbody>
    <tr><td>Revenue</td><td>1,804.7</td><td>1,930.6</td></tr></tbody></table>
    <table><caption>Peer valuation</caption><thead><tr><th>Company</th><th>Revenue FY2026E</th></tr></thead>
    <tbody><tr><td>Juniper Payments Corp.</td><td>9,999.0</td></tr></tbody></table>'''


class Robustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs={'alpha.html':annual(), 'beta.html':annual('Juniper Payments Corp.').replace('81.3','25.6').replace('62.1','23.7'),
                  'gamma.html':research()}
        cls.chunks=[c for f,html in cls.docs.items() for c in h.chunk_document(f,html)]
        cls.index=h.build_index(cls.chunks)

    def check_question(self, question, names, year, fact, kind='annual_report'):
        parsed=h.parse_query(question)
        self.assertEqual({h.company_key(n) for n in parsed['companies']},set(names))
        self.assertEqual(parsed['fiscal_year'],year)
        self.assertEqual(parsed['doc_type'],kind)
        chunks=h.retrieve(self.index,question)
        self.assertTrue(any(fact in c.page_content for c in chunks),question)
        self.assertTrue(all(any(c is original for original in self.chunks) for c in chunks))
        self.assertLessEqual(len(chunks),5)

    def test_possessive_company_spellings(self):
        for name in ['juniper devices','JUNIPER DEVICES INC.','Juniper-Devices','Juniper Devices, Inc.']:
            with self.subTest(name=name):
                self.check_question(f"What was {name}'s cash and cash equivalents in FY2024?",{'juniper devices'},2024,'2024: 62.1')

    def test_simple_paraphrases(self):
        cases=[('What is the headcount of Juniper Devices in FY2025?', '712'),
               ('How many employees did Juniper Devices have at 31 December 2025?', '712'),
               ('What was the revenue of Juniper Devices in FY2025?', '1,804.7'),
               ("What was Juniper Devices’ revenue as of December 31, 2025?", '1,804.7')]
        for q,fact in cases:
            with self.subTest(q=q):self.check_question(q,{'juniper devices'},2025,fact)

    def test_comparisons_without_colon(self):
        for q in ['Between Juniper Devices and Juniper Payments, which company held more cash in FY2024?',
                  'Which company held more cash in FY2024, Juniper Devices or Juniper Payments?']:
            with self.subTest(q=q):
                self.check_question(q,{'juniper devices','juniper payments'},2024,'2024: 62.1')
                self.assertTrue(any('2024: 23.7' in c.page_content for c in h.retrieve(self.index,q)))

    def test_explicit_nondisclosure(self):
        for metric in ['lobbying expenses','customer churn rate']:
            with self.subTest(metric=metric):
                self.assertEqual(h.retrieve(self.index,f"What were Juniper Devices' {metric} in FY2025?"),[])
        mixed=annual().replace('Lobbying expenses are not disclosed.',
                               'Lobbying expenses are not disclosed. Revenue was USD 1,804.7 million in 2025.')
        index=h.build_index(h.chunk_document('mixed.html',mixed))
        self.assertTrue(h.retrieve(index,"What was Juniper Devices' revenue in FY2025?"))

    def test_company_name_containing_and(self):
        a=h.chunk_document('one.html',annual('Juniper and Sons Inc.'))
        b=h.chunk_document('two.html',annual('Maple Devices Ltd.').replace('62.1','18.9'))
        q='Which company held more cash in FY2024: Juniper and Sons or Maple Devices?'
        self.assertEqual(h.parse_query(q)['companies'],['Juniper and Sons','Maple Devices'])
        chunks=h.retrieve(h.build_index(a+b),q)
        self.assertEqual({h.company_key(c.metadata['company']) for c in chunks},{'juniper and sons','maple devices'})

    def test_forecast_and_personnel(self):
        self.check_question('What FY2026 revenue does Pine Equity Research forecast for Juniper Devices, in USD millions?',
                            {'juniper devices'},2026,'1,930.6','research_report')
        q="Who was Juniper Devices' Chief Financial Officer at the end of FY2025?"
        self.check_question(q,{'juniper devices'},2025,'Nora Lin')
        self.assertNotIn('Adam Reed',h.retrieve(self.index,q)[0].page_content)
        self.check_question("Which audit firm audited Juniper Devices' financial statements for FY2025?",
                            {'juniper devices'},2025,'Grant Dale LLP')

    def test_unknown_names_and_years(self):
        for q in ["What was Juniper Device Systems' revenue in FY2025?", "What was Juniper Devices' revenue in FY2021?"]:
            with self.subTest(q=q):
                self.assertTrue(h.parse_query(q)['companies'])
                self.assertEqual(h.retrieve(self.index,q),[])

    def test_filename_order_and_second_corpus(self):
        q="What was Juniper Devices' revenue in FY2025?"
        mutated=[c for i,html in enumerate(reversed(list(self.docs.values()))) for c in h.chunk_document(f'renamed_{i}.html',html)]
        self.assertEqual({c.page_content for c in h.retrieve(self.index,q)},
                         {c.page_content for c in h.retrieve(h.build_index(mutated),q)})
        other=h.build_index(h.chunk_document('alpha.html',annual('Maple Tools Ltd.')))
        self.assertEqual(h.retrieve(other,q),[])
        self.assertTrue(h.retrieve(self.index,q))

    def test_symbols_blank_cell_and_rowspan(self):
        html='''<table><caption>USD millions and %</caption><thead><tr><th>Item</th><th>2025</th><th>2024</th></tr></thead>
        <tbody><tr><td rowspan="2">Profit</td><td>(1,230.50)</td><td>—</td></tr>
        <tr><td></td><td>3.2%</td></tr></tbody></table>'''
        output=h.table_to_text(html)
        for text in ['Profit | 2025: (1,230.50) | 2024: —','Profit | 2024: 3.2%','USD millions and %']:
            self.assertIn(text,output)
        self.assertTrue(all(len(line)<=400 for line in output.splitlines()))

    def test_source_provenance_and_no_models(self):
        with patch.object(h,'make_llm',side_effect=AssertionError('Forbidden model call')), patch.object(h,'_chat',side_effect=AssertionError('Forbidden client')):
            for file,html in self.docs.items():
                soup=h.BeautifulSoup(html,'html.parser');table_text='\n'.join(h.table_to_text(str(t)) for t in soup.find_all('table'))
                original=h.squash(soup.get_text(' ',strip=True)+' '+table_text)
                for c in h.chunk_document(file,html):
                    self.assertLessEqual(len(c.page_content),1500)
                    self.assertIs(type(c.metadata['fiscal_year']),int)
                    self.assertEqual(c.metadata['source'],file)
                    self.assertEqual(c.metadata['company'], 'Juniper Payments Corp.' if file=='beta.html' else 'Juniper Devices Inc.')
                    for line in c.page_content.splitlines()[1:]:self.assertIn(h.squash(line),original)


if __name__=='__main__':unittest.main()

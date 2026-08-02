import os
import unittest

from parser import parse_resume


class ParserTests(unittest.TestCase):
    def test_parse_resume_handles_pdf_with_date_ranges(self):
        path = os.path.join("sample_data", "resumes", "Himanshu Sharma-Resume.pdf")
        resume = parse_resume(path)

        self.assertIn("filename", resume)
        self.assertTrue(resume["raw_text"].strip())
        self.assertIsInstance(resume["years_experience"], (int, float))


if __name__ == "__main__":
    unittest.main()

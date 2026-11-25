"""Failures that must stop an extract before it can reach the warehouse."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import source
from render_dashboard import render

class ContractTests(unittest.TestCase):
    def row(self):
        return dict(code_codice='ZUE',uic=8503000,jahr_annee_anno=2025,bahnhof_gare_stazione='Zürich HB',kt_ct_cantone='ZH',dtv_tjm_tgm=1,dwv_tmjo_tfm=1,dnwv_tmjno_tmgnl=1)

    def rejected(self, records, expected_count, message):
        with tempfile.TemporaryDirectory() as directory, patch.object(source,'ROOT',Path(directory)), patch.object(source,'get_json',side_effect=[{'metas':{'default':{'records_count':expected_count}}},records]):
            with self.assertRaisesRegex(ValueError,message):
                source.extract()
            self.assertFalse((Path(directory)/'runtime').exists())

    def test_partial_export_is_not_published(self):
        self.rejected([self.row()],2,'Incomplete source export')

    def test_schema_loss_is_not_published(self):
        row=self.row(); del row['dtv_tjm_tgm']
        self.rejected([row],1,'Required source fields missing')

    def test_duplicate_grain_is_not_published(self):
        self.rejected([self.row(),self.row()],2,'no longer unique')

    def test_source_text_cannot_close_json_script(self):
        html=render({'value':'</script><script>alert(1)</script>'}).decode()
        self.assertNotIn('</script><script>alert(1)',html)
        self.assertIn('\\u003c/script\\u003e',html)

if __name__=='__main__':
    unittest.main()

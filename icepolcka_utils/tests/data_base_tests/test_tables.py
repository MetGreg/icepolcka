"""Tests for the tables module"""
import unittest

from sqlalchemy.orm import session

from tests import utils as test_utils

from icepolcka_utils import utils
from icepolcka_utils.database import tables


class TablesTest(unittest.TestCase):
    """Tests for all functions in the tables module"""
    def setUp(self):
        self.db_path = utils.make_folder("db")

    def tearDown(self):
        test_utils.delete_content(self.db_path)

    def test_create_session_creates_sql_session(self):
        """Tests if the create_session function returns a sql session"""
        ses = tables.create_session(self.db_path + "test.db")
        self.assertTrue(isinstance(ses, session.Session), "Expected a sqlalchemy session")
        ses.close()

    def test_create_tables_creates_three_radars(self):
        """Test if the creates_tables function creates all three radar entries"""
        ses = tables.create_tables(self.db_path + "test.db")
        query = ses.query(tables.Radar).all()
        ses.close()
        self.assertEqual(len(query), 1, "Expected one radar entry")


if __name__ == "__main__":
    unittest.main()

import sys
import pytest
# Workaround from stackoverflow to allow importing from src
sys.path.append("..")

from src.confman import ConfManager

@pytest.fixture()
def confman(tmp_path):
    conf_file_path = tmp_path / "conf"
    yield ConfManager(conf_file_path)
    
class TestConfMan:
    def test_create(self, confman):
        assert confman is not None

    def test_base_schema_copied(self, confman):
        assert confman.BASE_SCHEMA["example"] == confman.get_value("example")

    def test_setting_value(self, confman):
        ex_val = True
        confman.set_value("test", ex_val)
        assert confman.get_value("test") == ex_val

    def test_persistence(self, tmp_path):
        # Manually
        conf_file_path = tmp_path / "conf"
        confman = ConfManager(conf_file_path)

        ex_val = 12
        confman.set_value("test", 12)

        del(confman)
        new_confman = ConfManager(conf_file_path)
        
        assert new_confman.get_value("test") == ex_val
        

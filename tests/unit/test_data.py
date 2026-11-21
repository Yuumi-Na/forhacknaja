import json
import shutil

import pytest

from mordin.data import DATA_DIR, DataFileError, load_data


@pytest.fixture
def data_dir(tmp_path):
    dest = tmp_path / "data"
    shutil.copytree(DATA_DIR, dest)
    return dest


def _edit(path, fn):
    obj = json.loads(path.read_text(encoding="utf-8"))
    fn(obj)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_loads_real_data_files():
    d = load_data()
    assert d.basic_formula["max_kg_per_rai"]["urea"] > 0
    assert d.prices["prices_per_kg"]["urea"] == 20.0
    assert d.limits["small_bag_kg"] == 5


def test_non_monotone_target_table_rejected(data_dir):
    def bump(o):
        o["bands"]["k"][2]["target_k2o_kg_per_rai"] = 99

    _edit(data_dir / "dld_rules" / "basic_formula.json", bump)
    with pytest.raises(DataFileError) as e:
        load_data(data_dir)
    assert "basic_formula.json" in e.value.path
    assert "monotone" in e.value.reason


def test_placeholder_with_empty_label_rejected(data_dir):
    _edit(data_dir / "limits.json", lambda o: o.update(label="  "))
    with pytest.raises(DataFileError) as e:
        load_data(data_dir)
    assert "limits.json" in e.value.path


def test_placeholder_with_missing_label_rejected(data_dir):
    _edit(data_dir / "dld_rules" / "basic_formula.json", lambda o: o.pop("label"))
    with pytest.raises(DataFileError):
        load_data(data_dir)


@pytest.mark.parametrize("name", ["urea", "dap", "mop"])
def test_missing_max_kg_rejected(data_dir, name):
    _edit(
        data_dir / "dld_rules" / "basic_formula.json",
        lambda o: o["max_kg_per_rai"].pop(name),
    )
    with pytest.raises(DataFileError) as e:
        load_data(data_dir)
    assert name in e.value.reason


def test_missing_file_names_the_file(data_dir):
    (data_dir / "fertilizer_prices.json").unlink()
    with pytest.raises(DataFileError) as e:
        load_data(data_dir)
    assert "fertilizer_prices.json" in str(e.value)

"""The site catalog is data, not Python configuration."""

from pathlib import Path


def test_site_catalog_is_loaded_from_yaml():
    from catix.wiki.sources import sites

    assert sites.CONFIG == Path(sites.__file__).with_name("sites.yaml")
    assert sites.CONFIG.exists()
    assert sites.SITES["university"].base == "https://innopolis.university/"
    assert sites.SITES["university"].aliases == ("university.innopolis.ru",)
    assert "inno-stand-up-club-timepad-ru" in sites.SITES
    assert "oez-innopolis.timepad.ru" in sites.BLOCKED
    assert "moodle.innopolis.university" in sites.BLOCKED

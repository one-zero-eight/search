# Run parsers and save results locally. This dump will be used for filling the mongo for tests.
import asyncio
import sys
from pathlib import Path

# add parent dir to sys.path
sys.path.append(str(Path(__file__).parents[1]))

from src.modules.parsers.routes import run_parse_route
from src.modules.sources_enum import InfoSources

for section in (InfoSources.hotel, InfoSources.eduwiki, InfoSources.campuslife, InfoSources.residents):
    asyncio.run(
        run_parse_route(section=section, indexing_is_needed=False, parsing_is_needed=True, saving_dump_is_needed=True)
    )

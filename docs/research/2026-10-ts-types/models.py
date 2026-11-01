import json, sys
from typing import Any, Literal, Annotated, Union
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import models_json_schema

STRICT = "strict" in sys.argv
class Base(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=STRICT)

class Ref(Base):
    id: str
    type: str

class Talent(Base):
    id: str
    type: Literal["talent"]
    name: str
    icon_path: str | None = None          # optional, may be null
    rarity: int = 0                        # has default
    stats: dict[str, float]                # tier 2 map
    unlocks: list[Ref] = []
    detail: dict[str, Any]                 # tier 3, open

class Pilot(Base):
    id: str
    type: Literal["pilot"]
    name: str
    talents: list[Ref]
    detail: dict[str, Any]

Obj = Annotated[Union[Talent, Pilot], Field(discriminator="type")]
class Envelope(Base):
    obj: Obj

mode = "serialization"
_, schema = models_json_schema([(m, mode) for m in (Talent, Pilot, Envelope)], title="WrfModels")
print(json.dumps(schema, indent=1))

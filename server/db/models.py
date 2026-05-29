from pydantic import BaseModel, Field
from typing import Optional

class GlobalSettingsUpdate(BaseModel):
    githubEnabled: bool = True
    githubToken: str = ""
    ozoneEnabled: bool = True
    ozoneFetchCron: str = ""
    concurrency: int = Field(64, ge=1, le=500)
    timeout: int = Field(2000, ge=200, le=10000)
    configDelay: int = Field(3, ge=0, le=60)
    scanCron: str = ""
    janitorCron: str = ""
    callbackToken: str = ""
    zoomeyeEnabled: bool = True
    zoomeyeFetchCron: str = ""
    daydaymapEnabled: bool = True
    daydaymapFetchCron: str = ""
    hunterEnabled: bool = True
    hunterApiKey: str = ""
    hunterFetchCron: str = ""
    githubUserResultFetchCron: str = ""
    githubUserResultQuery: str = "filename:result.txt path:output/ipv4"
    githubUserResultUrls: str = ""

class TemplateCreateOrUpdate(BaseModel):
    name: str
    region: str
    operator: str
    targetName: str
    targetAddress: str

class ConfigCreateOrUpdate(BaseModel):
    name: str
    templateId: int
    dataSource: str
    searchDepth: Optional[int] = Field(30, ge=1, le=30)
    enabled: Optional[bool] = True
